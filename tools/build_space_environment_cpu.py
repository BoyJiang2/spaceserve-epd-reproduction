"""Bounded dependency batches and framework actions for the original Space environment. No model/GPU import."""
import base64
import configparser
import io
import stat
import tarfile
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import sys
import time

import migrate_code_cpu as migration

BOOT='65f52a67-afe4-4919-8646-4694255b48ee'
RUNTIME='a3f03b9dd5956db92add454f9b3afd5663f84609'
ACTIONS=('restore-hooks','verify')
MIRROR_TOOL='ac30bfb7255a49738ca1450c92799b803c983208'
SOURCE_TRANSFER_TOOL='97a08edc8136909192a6b821cf832a313d108a91'
SOURCE_ARCHIVES_SHA='7f2c0ef2769f1f3dfdbb8c8a5d4d5e833a5655e5f625e983353e6262f5080a43'
PARTIAL_GIT_SHA='68719988769a6fe6f6f7f57ba9d0ff3d07f32032ae61c7712b701e08ec5b9922'
LOCK_TOOL='999d479ff855dd25d9eb50ee073a6421209ff7d9'
INPUTS={'space-freeze.txt':'12cc7ae16e15cb32a58d197b10c139df7d715a8c3eeb4246b77eebe5d4814b0f',
        'prepare_space.py':'3775d95a2e1ed4deefb49c6db1d2efe8480e46aba553d349804347751eab721c',
        'apply_space_compat.py':'8718c981961ca4812e16b0bce2dcd36639c4bdf0e923ba178b9761a4a75fd2ed'}
UV_SHA='8a70db72685b7138121bfcda71fa1a00cb709ed9f1fdc4ecf1dd871e8e167e52'
UPSTREAM=(('SpaceServe','https://github.com/gofreelee/SpaceServe.git','66de079af4234b27f7f82ff91d238ef1351324ba'),
          ('mysmctrl','https://github.com/gofreelee/mysmctrl.git','6ff57356968a3f04158b9273aa881ee6bdf04229'))


def versions(text):
    result={}
    for line in text.splitlines():
        if not line.strip():continue
        match=re.fullmatch(r'([A-Za-z0-9._-]+)==([A-Za-z0-9.!+_-]+)',line)
        if not match:raise ValueError('Exact versions required')
        name=re.sub('[-_.]+','-',match[1]).lower()
        if name in result:raise ValueError('Duplicate package')
        result[name]=match[2]
    return result


def verify_lock(text,expected):
    found={};current=None
    for raw in text.splitlines():
        line=raw.strip().removesuffix('\\').strip()
        if not line or line.startswith('#'):continue
        match=re.fullmatch(r'([A-Za-z0-9._-]+)==([A-Za-z0-9.!+_-]+)',line)
        if match:
            current=re.sub('[-_.]+','-',match[1]).lower()
            if current in found:raise ValueError('Duplicate lock requirement')
            found[current]={'version':match[2],'hashes':[]}
        elif re.fullmatch(r'--hash=sha256:[0-9a-f]{64}',line) and current:
            found[current]['hashes'].append(line[14:])
        else:raise ValueError('Unexpected lock entry; no unpinned URLs/markers')
    if {name:row['version'] for name,row in found.items()}!=expected or not all(row['hashes'] for row in found.values()):
        raise ValueError('Full original versions and hashes required')
    return found


def dependency_parts(raw):
    expected=versions(raw.decode())
    if len(expected)!=154:raise ValueError('Exact154 packages required')
    lines=raw.decode().splitlines(keepends=True)
    if len(lines)!=154 or any(not line.strip() for line in lines):raise ValueError('Exact154 original lines required')
    return [b''.join(line.encode() for line in lines[start:start+16]) for start in range(0,154,16)]


def git_configuration(url):
    return ('[core]\n\trepositoryformatversion = 0\n\tbare = false\n\tfilemode = true\n'
        '\tsymlinks = true\n\tignorecase = false\n[remote "origin"]\n\turl = '+url+'\n').encode()


def validate_git_archive(path,row):
    raw=Path(path).read_bytes()
    if len(raw)!=row['archive_bytes'] or hashlib.sha256(raw).hexdigest()!=row['archive_sha256']:
        raise ValueError('Git metadata archive bytes differ')
    expected={r['path']:r for r in row['members']}
    if len(expected)!=len(row['members']):raise ValueError('Duplicate expected metadata')
    allowed=r'(?:config|HEAD|FETCH_HEAD|shallow|refs/heads/pinned|objects/[0-9a-f]{2}/[0-9a-f]{38}|objects/pack/pack-[0-9a-f]{40}\.(?:idx|pack|rev))'
    if not all(re.fullmatch(allowed,name) for name in expected):raise ValueError('Unexpected Git metadata path')
    if not {'config','HEAD','FETCH_HEAD','shallow','refs/heads/pinned'}<=set(expected):raise ValueError('Incomplete shallow Git metadata')
    contents={};end=0
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as archive:
        for member in archive.getmembers():
            if (not member.isfile() or member.name not in expected or member.name in contents
                    or member.linkname or member.mode!=0o600 or member.pax_headers):
                raise ValueError('Unexpected archive member/type/mode')
            value=archive.extractfile(member).read();record=expected[member.name]
            if len(value)!=record['bytes'] or hashlib.sha256(value).hexdigest()!=record['sha256']:
                raise ValueError('Git metadata member differs')
            contents[member.name]=value;end=max(end,member.offset_data+(member.size+511)//512*512)
    if set(contents)!=set(expected) or len(raw)-end<1024 or any(raw[end:]) or len(raw)%512:
        raise ValueError('Incomplete archive or unexpected trailing data')
    config=configparser.RawConfigParser();config.read_string(contents['config'].decode())
    if config.sections()!=['core'] or dict(config['core'])!={'repositoryformatversion':'0','filemode':'false','bare':'true','symlinks':'false','ignorecase':'true'}:
        raise ValueError('Imported config is not the original empty-template bare config')
    if (contents['shallow']!=(row['commit']+'\n').encode()
            or contents['refs/heads/pinned']!=(row['commit']+'\n').encode()
            or contents['HEAD']!=b'ref: refs/heads/master\n'):
        raise ValueError('Exact shallow boundary/refs required')
    return contents


def partial_git_inventory(path):
    rows=[]
    for entry in sorted(path.rglob('*')):
        info=entry.lstat()
        if info.st_uid!=2147 or entry.is_symlink() or entry.name.endswith('.lock') or not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            raise ValueError('Unknown partial Git state; refuse mutation')
        rows.append({'path':entry.relative_to(path).as_posix(),'uid':info.st_uid,'mode':info.st_mode,
            'bytes':info.st_size,'sha256':migration.sha(entry) if entry.is_file() else None,'link':None})
    return rows


def controlled_environment(root):
    return {'PATH':'/usr/bin:/bin','HOME':'/nonexistent','LC_ALL':'C.UTF-8',
        'TMPDIR':str(root/'staging/env-build-hooks/tmp'),'XDG_CACHE_HOME':str(root/'assets/cache'),
        'UV_CACHE_DIR':str(root/'assets/cache/uv'),'UV_NO_CONFIG':'1','UV_PYTHON_DOWNLOADS':'never',
        'UV_HTTP_TIMEOUT':'30','UV_HTTP_RETRIES':'2','UV_CONCURRENT_DOWNLOADS':'4',
        'UV_CONCURRENT_INSTALLS':'1','UV_CONCURRENT_BUILDS':'1','UV_NO_PROGRESS':'1',
        'PYTHONDONTWRITEBYTECODE':'1','SETUPTOOLS_USE_DISTUTILS':'stdlib',
        'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_SYSTEM':'/dev/null','GIT_TERMINAL_PROMPT':'0',
        'GIT_LFS_SKIP_SMUDGE':'1','GIT_ATTR_NOSYSTEM':'1'}


def install_arguments(uv,python,lock):
    return [str(uv),'--no-config','--verbose','pip','install','--python',str(python),
            '--no-deps','--require-hashes','--only-binary',':all:','--link-mode','copy',
            '--index-url','https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple','-r',str(lock)]


def run(data):
    start=time.monotonic();deadline=start+240;proof=data['booking'];action=data['action']
    if action not in ACTIONS or data['runtime_commit']!=RUNTIME or not re.fullmatch('[0-9a-f]{40}',data['tool_commit']):
        raise ValueError('Exact action/commits required')
    def check():
        now=int(time.time()*1000);migration.booking(proof,now)
        left=min(deadline-time.monotonic(),(proof['observed_ms']+300000-now)/1000)
        if left<=1:raise TimeoutError('Action/proof work budget exhausted')
        return left
    check();migration.validate_executor()
    if (sys.version_info[:3]!=(3,10,12) or Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=BOOT):
        raise ValueError('Exact system Python/boot required')
    root=migration.PARENT/'spaceserve';assets=root/'assets';repo=root/'repo';evidence=root/'staging/env-build-hooks';source_previous=root/'staging/env-build-source-io';locks_root=root/'staging/env-build-batched';mirror=root/'staging/env-build-mirror'
    for path in (assets,repo/'.git',evidence):migration.real_ancestry(path)
    if (repo/'.git/HEAD').is_symlink() or (repo/'.git/HEAD').read_text().strip()!=RUNTIME:
        raise ValueError('Frozen runtime differs')
    if shutil.disk_usage(root).free<120*1024**3:raise ValueError('120GiB real free space required')
    if set(data['inputs'])!=set(INPUTS):raise ValueError('Exact three committed recipe inputs required')
    inputs={}
    for name,digest in INPUTS.items():
        raw=base64.b64decode(data['inputs'][name],validate=True)
        if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Recipe/freeze bytes differ')
        inputs[name]=raw
    expected=versions(inputs['space-freeze.txt'].decode())
    if len(expected)!=154:raise ValueError('Exact154 packages required')
    parts=dependency_parts(inputs['space-freeze.txt'])
    first=action==ACTIONS[0]
    if first:
        if evidence.exists():raise ValueError('Existing batch preparation/partial; inspect without retry')
        prior_root=source_previous;previous='framework'
    else:
        prior_root=evidence;previous=ACTIONS[ACTIONS.index(action)-1]
    def prior_success(folder,name):
        prior=json.loads((folder/(name+'.terminal.json')).read_bytes())
        if (prior['action']!=name or prior['state']!='SPACE_CPU_ACTION_SUCCEEDED'
                or prior['failure'] is not None or prior['runtime_commit']!=RUNTIME or prior['boot_id']!=BOOT
                or prior['host']!='qjh003' or prior['uid']!=2147 or prior['input_sha256s']!=INPUTS
                or migration.sha(folder/(name+'.log'))!=prior['log_sha256']):
            raise ValueError('Previous actual action has not succeeded with the same inputs')
        expected_tool=data['tool_commit'] if folder==evidence else (SOURCE_TRANSFER_TOOL if folder==source_previous else MIRROR_TOOL if folder==mirror else LOCK_TOOL)
        if prior['tool_commit']!=expected_tool:raise ValueError('Actual action tool commit changed')
        return prior
    prior_success(prior_root,previous)
    if first:
        failed=json.loads((source_previous/'verify.terminal.json').read_bytes())
        if (failed['action']!='verify' or failed['state']!='FAILED_PARTIAL_PRESERVED'
                or failed['failure']!="ValueError('Original protected bytes/links differ; do not rewrite pins')"
                or failed['tool_commit']!=SOURCE_TRANSFER_TOOL or failed['runtime_commit']!=RUNTIME
                or failed['boot_id']!=BOOT or failed['host']!='qjh003' or failed['uid']!=2147
                or failed['input_sha256s']!=INPUTS
                or migration.sha(source_previous/'verify.log')!=failed['log_sha256']):
            raise ValueError('Exact known failed framework evidence required')
        evidence.mkdir(mode=0o700)
    claim={'action':action,'tool_commit':data['tool_commit'],'runtime_commit':RUNTIME,'input_sha256s':INPUTS,
           'source_archive_manifest_sha256':SOURCE_ARCHIVES_SHA,
           'host':socket.gethostname(),'uid':os.getuid(),'boot_id':BOOT,'booking':proof,
           'pid':os.getpid(),'start_ticks':Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19],
           'affinity':sorted(os.sched_getaffinity(0)),'nice':os.getpriority(os.PRIO_PROCESS,0),'started_ms':int(time.time()*1000)}
    def save(name,value):migration.real_ancestry(evidence);migration.exclusive_json(evidence/name,value)
    save(action+'.claim.json',claim);log=evidence/(action+'.log');failure=None;details={}
    handlers={number:signal.getsignal(number) for number in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM)}
    def interrupted(number,frame):raise TimeoutError('CPU environment action interrupted')
    for number in handlers:signal.signal(number,interrupted)
    signal.alarm(max(1,int(deadline-time.monotonic())))
    try:
        env=controlled_environment(root);os.environ.clear();os.environ.update(env);os.chdir(root)
        with log.open('xb') as stream:
            def command(argv):
                left=check()
                return migration.command_output(argv,stream,max(0.1,left-1),start+360)
            if command(['git','-c','core.fsmonitor=false','-c','core.excludesFile=/dev/null','-C',str(repo),'status','--porcelain','--untracked-files=all']).strip():
                raise ValueError('Frozen runtime is dirty')
            for name,raw in inputs.items():
                path=evidence/name
                if first:
                    with path.open('xb') as target:target.write(raw)
                elif path.is_symlink() or migration.sha(path)!=INPUTS[name]:raise ValueError('Staged input changed')
            uv=assets/'tools/uv';python=assets/'envs/space/bin/python'
            if uv.is_symlink() or migration.sha(uv)!=UV_SHA:raise ValueError('Staged uv changed')
            migration.real_ancestry(python.parent)
            if not python.is_file() or python.resolve()!=Path('/usr/bin/python3').resolve():
                raise ValueError('Actual successful bootstrap system interpreter required')
            if first:
                site=assets/'envs/space/lib/python3.10/site-packages'
                installed={re.sub('[-_.]+','-',d.metadata['Name']).lower():d.version
                           for d in importlib.metadata.distributions(path=[str(site)])}
                if installed!=expected:raise ValueError('Actual154 installed versions changed')
                (evidence/'tmp').mkdir(mode=0o700)
                save('failed-framework-reference.json',{'terminal_sha256':migration.sha(source_previous/'verify.terminal.json'),
                    'log_sha256':migration.sha(source_previous/'verify.log'),'actual_installed_versions':installed})
            lock_receipts={}
            for number,raw in enumerate(parts,1):
                path=locks_root/f'part-{number:02}.txt';lock=locks_root/f'part-{number:02}.lock'
                if path.is_symlink() or path.read_bytes()!=raw:raise ValueError('Original fixed batch changed')
                prior=prior_success(locks_root,f'lock-{number:02}')
                if lock.is_symlink() or migration.sha(lock)!=prior['details']['lock_sha256']:
                    raise ValueError('Actual original successful batch lock differs')
                verify_lock(lock.read_text(),versions(raw.decode()));lock_receipts[number]=prior['details']['lock_sha256']
            if first:save('original-lock-references.json',lock_receipts)
            archive_raw=base64.b64decode(data['source_archives_base64'],validate=True)
            if hashlib.sha256(archive_raw).hexdigest()!=SOURCE_ARCHIVES_SHA:raise ValueError('Approved source archive manifest differs')
            archives=json.loads(archive_raw)
            if [(row['name'],row['url'],row['commit']) for row in archives]!=list(UPSTREAM):raise ValueError('Official source identities differ')
            if action=='restore-hooks':
                before={
                    'envs/space/lib/python3.10/site-packages/vllm/v1/worker/gpu_worker.py':'41232620036691ced8c0f06982c87a2fff7d7b24fa7e159ab1ba7a1834b63b96',
                    'src/SpaceServe/vllm/v1/worker/gpu_worker.py':'975d48631b1298966b5f64db479038c3070e3673c632d5a5e4802f546870f569',
                    'src/SpaceServe/vllm/v1/engine/core.py':'6737019b2f74dbbc349fd852287f48dd774c56d2eb575db3d42e6f97667fd456'}
                pins={r['path']:r for r in json.loads((repo/'spaceserve/runtime/configs/asset-content-pins.json').read_bytes())}
                for number,(name,digest) in enumerate(before.items()):
                    path=assets/name;migration.real_ancestry(path.parent)
                    if path.is_symlink() or path.stat().st_uid!=2147 or migration.sha(path)!=digest:raise ValueError('Exact pre-hook file required')
                    with (evidence/f'hook-{number}.before.py').open('xb') as writer:writer.write(path.read_bytes())
                recipes={'install_device_record.py':'29f8e6d5a5894a14de6f83dd613cb76bcee22593fef24d15f6115ce8a20ab5b4',
                         'install_service_probe.py':'871730504cc3247291143236f601b7bd5ae6b6996439c3a5d473dd7c82998e04'}
                prefix=('import importlib.metadata,pathlib,sys\n'
                    'site=pathlib.Path(sys.argv[1])/"envs/space/lib/python3.10/site-packages"\n'
                    'def metadata_only(name):\n'
                    ' return next(d for d in importlib.metadata.distributions(path=[str(site)]) if d.metadata["Name"].lower()==name.lower())\n'
                    'importlib.metadata.distribution=metadata_only\n')
                guard=b"'/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023'"
                for name,digest in recipes.items():
                    raw=command(['git','-C',str(repo),'show',RUNTIME+':spaceserve/code/h20/used-scripts/'+name])
                    if hashlib.sha256(raw).hexdigest()!=digest or raw.count(guard)!=1:raise ValueError('Original hook recipe differs')
                    adapted=raw.replace(guard,repr(str(assets)).encode(),1)
                    command(['/usr/bin/python3','-I','-S','-B','-c',prefix+adapted.decode(),str(assets)])
                for number,name in enumerate(before):
                    if migration.sha(assets/name)!=pins[name]['sha256']:raise ValueError('Restored hook must equal original pin')
                    with (evidence/f'hook-{number}.after.py').open('xb') as writer:writer.write((assets/name).read_bytes())
                save('hook-restoration.json',{'before_sha256s':before,'after_sha256s':{n:pins[n]['sha256'] for n in before},
                    'recipe_source_commit':RUNTIME,'recipe_sha256s':recipes,'root_only_adaptation':str(assets)})
            elif action=='verify':
                site=assets/'envs/space/lib/python3.10/site-packages'
                actual={re.sub('[-_.]+','-',d.metadata['Name']).lower():d.version for d in importlib.metadata.distributions(path=[str(site)])}
                if actual!=expected:raise ValueError('Actual154 package versions differ')
                command([str(uv),'--no-config','pip','check','--python',str(python)])
                spec=importlib.util.spec_from_file_location('space_asset_inventory',repo/'spaceserve/runtime/scripts/stage_cpu.py')
                inventory=importlib.util.module_from_spec(spec);spec.loader.exec_module(inventory)
                rows=inventory.inventory(assets);pins=json.loads((repo/'spaceserve/runtime/configs/asset-content-pins.json').read_bytes())
                protected=('models/','dataset/','src/SpaceServe/','src/mysmctrl/','build/','envs/space/lib/python3.10/site-packages/vllm/')
                if {r['path']:r for r in rows if r['path'].startswith(protected)}!={r['path']:r for r in pins}:
                    raise ValueError('Original protected bytes/links differ; do not rewrite pins')
                with (assets/'manifest.json').open('x') as target:json.dump(rows,target,indent=2)
                details.update(packages=len(actual),protected_entries=len(pins),asset_files=len(rows),
                    asset_manifest_sha256=migration.sha(assets/'manifest.json'),state='ASSETS_MATERIALIZED_only')
            check()
    except BaseException as error:failure=repr(error)
    finally:
        signal.alarm(0)
        for number in handlers:signal.signal(number,signal.SIG_IGN)
        try:
            save(action+'.terminal.json',{**claim,'ended_ms':int(time.time()*1000),'elapsed_seconds':time.monotonic()-start,
                'failure':failure,'state':'SPACE_CPU_ACTION_SUCCEEDED' if failure is None else 'FAILED_PARTIAL_PRESERVED',
                'details':details,'log_sha256':migration.sha(log) if log.is_file() else None,
                'CPU_STAGED':False,'actual_CPU_suite_passed':False,'GPU_requests':0})
        finally:
            for number,handler in handlers.items():signal.signal(number,handler)
    if failure is not None:raise RuntimeError('CPU environment action failed; preserve partial state')
    return {'action':action,'state':'SPACE_CPU_ACTION_SUCCEEDED','details':details,'GPU_requests':0}


if __name__=='__main__':
    payload=sys.stdin.buffer.read(100001)
    if len(payload)>100000:raise ValueError('CPU recipe payload budget exceeded')
    print(json.dumps(run(json.loads(payload))))
