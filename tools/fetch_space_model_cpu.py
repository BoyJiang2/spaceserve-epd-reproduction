"""One bounded local CPU-only fetch of pinned public Qwen files; no remote host/model execution."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import time

REPO=Path(__file__).resolve().parents[1]
ROOT=REPO.parents[1]/'assets/spaceserve'
PREFIX='models/Qwen2-VL-7B-Instruct/'
END=1793191800  # Beijing 2026-10-28 20:50, ahead of the 21:00 code migration.


def sha(path,deadline=None):
    h=hashlib.sha256()
    with path.open('rb') as source:
        while block:=source.read(8*1024**2):
            if deadline is not None and time.monotonic()>=deadline:raise TimeoutError('Local download/hash budget expired')
            h.update(block)
    return h.hexdigest()


def source_files(manifest,pins):
    if manifest['repo']!='Qwen/Qwen2-VL-7B-Instruct' or manifest['endpoint']!='https://modelscope.cn':
        raise ValueError('Only the recorded public ModelScope Qwen7B source is allowed')
    expected={item['path'][len(PREFIX):]:item for item in pins if item['path'].startswith(PREFIX)
              and item['path']!=PREFIX+'download_manifest.json'}
    rows=manifest['files'];names=[row['name'] for row in rows]
    if len(rows)!=15 or len(set(names))!=15 or set(names)!=set(expected):raise ValueError('Exact 15 frozen model files required')
    for row in rows:
        name=row['name'];part=PurePosixPath(name)
        if (part.is_absolute() or '..' in part.parts or '\\' in name or part.as_posix()!=name
                or len(part.parts)!=1 or not re.fullmatch('[0-9a-f]{40}',row['source']['Revision'])
                or (row['bytes'],row['sha256'])!=(expected[name]['bytes'],expected[name]['sha256'])):
            raise ValueError('Unsafe name, unpinned revision or model bytes/SHA mismatch')
    return rows


def safe_paths(root):
    for path in (root,*root.parents):
        if path.is_symlink() or getattr(path,'is_junction',lambda:False)():raise ValueError('Linked local asset ancestry refused')


def fetch(row,destination,logs,deadline,curl):
    safe_paths(destination)
    target=destination/row['name'];partial=target.with_name(target.name+'.partial')
    if target.is_symlink() or partial.is_symlink() or partial.exists():raise ValueError('Linked/partial file: preserve and review before any retry')
    if target.exists():
        if target.stat().st_size!=row['bytes'] or sha(target,deadline-5)!=row['sha256']:raise ValueError('Existing model file differs')
        return {'name':row['name'],'bytes':row['bytes'],'sha256':row['sha256'],'state':'existing_verified_no_download'}
    left=math.floor(deadline-time.monotonic())-5  # Reserve terminal/log and process cleanup time.
    if left<2:raise TimeoutError('No remaining local download budget')
    url='https://modelscope.cn/models/Qwen/Qwen2-VL-7B-Instruct/resolve/'+row['source']['Revision']+'/'+row['name']
    argv=[curl,'--disable','--fail','--location','--proto','=https','--proto-redir','=https',
          '--max-redirs','3','--silent','--show-error','--connect-timeout','15','--max-time',str(left-1),
          '--retry','0','--max-filesize',str(row['bytes']),'--output',str(partial),url]
    started=time.time();code=None;failure=None
    with (logs/(row['name']+'.stdout.log')).open('xb') as stdout,(logs/(row['name']+'.stderr.log')).open('xb') as stderr:
        try:
            result=subprocess.run(argv,stdout=stdout,stderr=stderr,timeout=left,check=False)
            code=result.returncode
            if code!=0:raise RuntimeError('Pinned file curl failed with exit '+str(code))
            if partial.stat().st_size!=row['bytes'] or sha(partial,deadline-5)!=row['sha256']:
                raise ValueError('Actual downloaded bytes/SHA differs; preserve partial')
            if target.exists():raise ValueError('Final path appeared during download; do not overwrite')
            partial.rename(target)
        except BaseException as error:failure=repr(error);raise
        finally:
            with (logs/(row['name']+'.command.json')).open('x') as record:
                json.dump({'argv':argv,'started_epoch':started,'finished_epoch':time.time(),
                    'exit_code':code,'failure':failure,'auto_retries':0},record,indent=2)
    return {'name':row['name'],'bytes':row['bytes'],'sha256':row['sha256'],'state':'downloaded_and_verified'}


def main():
    if os.name!='nt':raise RuntimeError('This preparation uses the reviewed local Windows curl.exe only')
    parser=argparse.ArgumentParser();parser.add_argument('--commit',required=True);args=parser.parse_args()
    if not re.fullmatch('[0-9a-f]{40}',args.commit):raise ValueError('Exact published tool commit required')
    def git(*args):return subprocess.check_output(['git','-C',str(REPO),*args],timeout=30)
    if git('rev-parse','HEAD').decode().strip()!=args.commit or git('status','--porcelain','--untracked-files=all').strip():
        raise ValueError('Use the clean designated published source')
    manifest=REPO/'spaceserve/configs/h20/qwen7b-model-manifest.json'
    pins=REPO/'spaceserve/runtime/configs/asset-content-pins.json'
    rows=source_files(json.loads(manifest.read_bytes()),json.loads(pins.read_bytes()))
    safe_paths(ROOT)
    if ROOT.exists() and (ROOT/'preparation').exists():raise ValueError('Existing once-only local download: inspect; do not repeat')
    free=shutil.disk_usage(REPO).free
    if free<sum(row['bytes'] for row in rows)+8*1024**3:raise ValueError('Insufficient local data disk budget')
    remaining=min(1800,END-time.time())
    if remaining<60:raise TimeoutError('No safe local preparation interval before 20:50')
    deadline=time.monotonic()+remaining
    curl=shutil.which('curl.exe')
    if not curl:raise RuntimeError('Reviewed Windows curl.exe required')
    ROOT.mkdir(parents=True,exist_ok=True);logs=ROOT/'preparation';logs.mkdir()
    destination=ROOT/PREFIX;safe_paths(destination);destination.mkdir(parents=True,exist_ok=True)
    state={'commit':args.commit,'source_manifest_sha256':sha(manifest),'asset_pins_sha256':sha(pins),
           'tool_sha256':sha(Path(__file__)),'started_epoch':time.time(),'deadline_seconds':remaining,
           'free_bytes_at_start':free,'files':[],'GPU_requests':0,'remote_host_operations':0,
           'download_manifest_pin_recovered':False,'complete_assets_ready':False}
    failure=None
    try:
        for row in rows:
            item=fetch(row,destination,logs,deadline,curl);state['files'].append(item)
            print(json.dumps(item),flush=True)
    except BaseException as error:failure=repr(error);raise
    finally:
        state.update(failure=failure,finished_epoch=time.time(),all_15_model_files_verified=len(state['files'])==15)
        with (logs/'terminal.json').open('x') as terminal:json.dump(state,terminal,indent=2)


if __name__=='__main__':main()
