"""Five bounded CPU actions for the original Space environment. No model/GPU import."""
import base64
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
ACTIONS=('bootstrap','lock','install','framework','verify')
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


def controlled_environment(root):
    return {'PATH':'/usr/bin:/bin','HOME':'/nonexistent','LC_ALL':'C.UTF-8',
        'TMPDIR':str(root/'staging/env-build/tmp'),'XDG_CACHE_HOME':str(root/'assets/cache'),
        'UV_CACHE_DIR':str(root/'assets/cache/uv'),'UV_NO_CONFIG':'1','UV_PYTHON_DOWNLOADS':'never',
        'UV_HTTP_TIMEOUT':'30','UV_HTTP_RETRIES':'2','UV_CONCURRENT_DOWNLOADS':'4',
        'UV_CONCURRENT_INSTALLS':'1','UV_CONCURRENT_BUILDS':'1','UV_NO_PROGRESS':'1',
        'PYTHONDONTWRITEBYTECODE':'1','SETUPTOOLS_USE_DISTUTILS':'stdlib',
        'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_SYSTEM':'/dev/null','GIT_TERMINAL_PROMPT':'0'}


def install_arguments(uv,python,lock):
    return [str(uv),'--no-config','--verbose','pip','install','--python',str(python),
            '--no-deps','--require-hashes','--only-binary',':all:','--link-mode','copy',
            '--index-url','https://pypi.org/simple','-r',str(lock)]


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
    root=migration.PARENT/'spaceserve';assets=root/'assets';repo=root/'repo';evidence=root/'staging/env-build'
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
    if action=='bootstrap':
        if evidence.exists() or os.path.lexists(assets/'envs/space') or os.path.lexists(assets/'tools/uv'):
            raise ValueError('Existing bootstrap/partial; inspect without retry')
        evidence.mkdir(mode=0o700)
    else:
        previous=ACTIONS[ACTIONS.index(action)-1]
        prior=json.loads((evidence/(previous+'.terminal.json')).read_bytes())
        if (prior['action']!=previous or prior['state']!='SPACE_CPU_ACTION_SUCCEEDED'
                or prior['failure'] is not None or prior['runtime_commit']!=RUNTIME or prior['boot_id']!=BOOT
                or prior['host']!='qjh003' or prior['uid']!=2147 or prior['input_sha256s']!=INPUTS
                or migration.sha(evidence/(previous+'.log'))!=prior['log_sha256']):
            raise ValueError('Previous actual action has not succeeded with the same inputs')
    claim={'action':action,'tool_commit':data['tool_commit'],'runtime_commit':RUNTIME,'input_sha256s':INPUTS,
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
            if command(['git','-c','core.fsmonitor=false','-C',str(repo),'status','--porcelain','--untracked-files=all']).strip():
                raise ValueError('Frozen runtime is dirty')
            for name,raw in inputs.items():
                path=evidence/name
                if action=='bootstrap':
                    with path.open('xb') as target:target.write(raw)
                elif path.is_symlink() or migration.sha(path)!=INPUTS[name]:raise ValueError('Staged input changed')
            uv=assets/'tools/uv';python=assets/'envs/space/bin/python';lock=evidence/'requirements.lock'
            if action=='bootstrap':
                for path in (assets/'tools',assets/'envs',assets/'cache/uv',evidence/'tmp'):
                    migration.real_ancestry(path);path.mkdir(mode=0o700,parents=True,exist_ok=True)
                source=migration.PARENT/'spaceserve-epd-qjh003-20261023/envs/tools/bin/uv'
                migration.real_ancestry(source.parent)
                if source.is_symlink() or source.stat().st_uid!=2147 or source.stat().st_size!=37597160 or migration.sha(source)!=UV_SHA:
                    raise ValueError('Exact inspected native uv required')
                with source.open('rb') as reader,uv.open('xb') as writer:
                    while block:=reader.read(4*1024**2):check();writer.write(block)
                    writer.flush();os.fsync(writer.fileno())
                os.chmod(uv,0o755)
                if migration.sha(source)!=UV_SHA or migration.sha(uv)!=UV_SHA:raise ValueError('uv copy differs')
                command([str(uv),'--version'])
                helptext=command([str(uv),'venv','--help'])
                if b'--python' not in helptext or b'--no-config' not in helptext:raise ValueError('Required venv options unsupported')
                command([str(uv),'--no-config','venv','--python','/usr/bin/python3',str(python.parents[1])])
            else:
                if uv.is_symlink() or migration.sha(uv)!=UV_SHA:raise ValueError('Staged uv changed')
                if action=='lock':
                    if os.path.lexists(lock):raise ValueError('Existing lock output refused')
                    command([str(uv),'--no-config','--verbose','pip','compile',str(evidence/'space-freeze.txt'),
                        '--no-deps','--generate-hashes','--only-binary',':all:','--python','/usr/bin/python3',
                        '--index-url','https://pypi.org/simple','--output-file',str(lock)])
                    details['locked_packages']=len(verify_lock(lock.read_text(),expected));details['lock_sha256']=migration.sha(lock)
                elif action=='install':
                    prior=json.loads((evidence/'lock.terminal.json').read_bytes())
                    if lock.is_symlink() or migration.sha(lock)!=prior['details']['lock_sha256']:raise ValueError('Actual successful hash lock differs')
                    verify_lock(lock.read_text(),expected);command(install_arguments(uv,python,lock))
                elif action=='framework':
                    src=assets/'src';migration.real_ancestry(src);src.mkdir(mode=0o700,exist_ok=True)
                    for name,url,commit in UPSTREAM:
                        target=src/name
                        if os.path.lexists(target):raise ValueError('Existing framework source refused')
                        command(['git','-c','core.hooksPath=/dev/null','init',str(target)])
                        command(['git','-C',str(target),'remote','add','origin',url])
                        command(['git','-C',str(target),'fetch','--depth=1','origin',commit])
                        command(['git','-c','core.hooksPath=/dev/null','-C',str(target),'checkout','--detach',commit])
                        if command(['git','-C',str(target),'rev-parse','HEAD']).decode().strip()!=commit:raise ValueError('Official framework HEAD differs')
                    # System Python -S reads the new wheel metadata without executing installed .pth files.
                    prefix=('import importlib.metadata,pathlib,sys\n'
                        'site=pathlib.Path(sys.argv[1])/"envs/space/lib/python3.10/site-packages"\n'
                        'def metadata_only(name):\n'
                        ' return next(d for d in importlib.metadata.distributions(path=[str(site)]) if d.metadata["Name"].lower()==name.lower())\n'
                        'importlib.metadata.distribution=metadata_only\n')
                    for name in ('prepare_space.py','apply_space_compat.py'):
                        command(['/usr/bin/python3','-I','-S','-B','-c',prefix+inputs[name].decode(),str(assets)])
                    pins=json.loads((repo/'spaceserve/runtime/configs/asset-content-pins.json').read_bytes())
                    for row in (r for r in pins if 'link' in r):
                        path=assets/row['path'];expected_target=assets/row['target_member']
                        if not path.is_symlink() or path.resolve()!=expected_target.resolve():raise ValueError('Unexpected native extension link')
                        path.unlink();path.symlink_to(row['link'])
                    target=assets/'src/mysmctrl/libsmctrl.so'
                    if os.path.lexists(target):raise ValueError('Existing upstream library refused')
                    with (assets/'build/libsmctrl.so').open('rb') as reader,target.open('xb') as writer:shutil.copyfileobj(reader,writer)
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
