"""One local exact-version PyPI metadata catalog; no artifact download or installation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from urllib.parse import quote,urlsplit

REPO=Path(__file__).resolve().parents[1]
ROOT=REPO.parents[1]/'assets/spaceserve/preparation/environment-catalog'
FREEZE=REPO/'spaceserve/migration/asset-recovery/environment/space-freeze.txt'
FREEZE_SHA='12cc7ae16e15cb32a58d197b10c139df7d715a8c3eeb4246b77eebe5d4814b0f'
LIMIT=2*1024**2


def normalize(name):return re.sub('[-_.]+','-',name).lower()


def packages(raw):
    rows=[]
    for line in raw.decode('utf8').splitlines():
        if not line.strip():continue
        match=re.fullmatch(r'([A-Za-z0-9][A-Za-z0-9._-]*)==([A-Za-z0-9][A-Za-z0-9.!+_-]*)',line)
        if not match:raise ValueError('Exact name==version lines only')
        rows.append((normalize(match[1]),match[2]))
    if len({name for name,version in rows})!=len(rows):raise ValueError('Duplicate normalized package')
    return rows


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('PyPI metadata redirects refused')


def describe(raw,name,version):
    data=json.loads(raw)
    if normalize(data['info']['name'])!=name or data['info']['version']!=version:raise ValueError('PyPI identity/version differs')
    artifacts=[]
    for row in data['urls']:
        url=urlsplit(row['url']);digest=row['digests']['sha256']
        if (url.scheme!='https' or url.hostname!='files.pythonhosted.org' or url.username is not None
                or url.password is not None or url.query or url.fragment or not re.fullmatch('[0-9a-f]{64}',digest)
                or type(row['size']) is not int or row['size']<0):raise ValueError('Unapproved artifact metadata')
        value={key:row.get(key) for key in ('filename','packagetype','url','size','requires_python','yanked','python_version')}
        value['sha256']=digest
        if row['filename'].endswith('.whl'):
            tags=row['filename'][:-4].rsplit('-',3)
            if len(tags)!=4:raise ValueError('Malformed wheel tag')
            value['wheel_tags']=dict(zip(('python','abi','platform'),tags[1:]))
        artifacts.append(value)
    return {'name':name,'version':version,'metadata_sha256':hashlib.sha256(raw).hexdigest(),'artifacts':artifacts}


def read_metadata(response,check,received=None):
    check();length=response.headers.get('Content-Length')
    if length is not None and not 0<=int(length)<=LIMIT:raise ValueError('Declared metadata response exceeds bounds')
    raw=bytearray() if received is None else received
    while True:
        left=check()
        if response.fp is not None:response.fp.raw._sock.settimeout(min(10,left))
        block=response.read(min(65536,LIMIT+1-len(raw)));check()
        if not block:break
        raw.extend(block)
        if len(raw)>LIMIT:raise ValueError('Actual metadata response exceeds 2MiB')
    return bytes(raw)


def exclusive(path,value):
    with path.open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--commit',required=True);args=parser.parse_args()
    if os.name!='nt' or not re.fullmatch('[0-9a-f]{40}',args.commit):raise ValueError('Designated local Windows CPU source required')
    def git(*argv):return subprocess.check_output(['git','-C',str(REPO),*argv],timeout=10)
    if git('rev-parse','HEAD').decode().strip()!=args.commit or git('status','--porcelain','--untracked-files=all').strip():
        raise ValueError('Use the clean published tool commit')
    before=FREEZE.read_bytes()
    if hashlib.sha256(before).hexdigest()!=FREEZE_SHA:raise ValueError('Original exact freeze required')
    rows=packages(before)
    if len(rows)!=154:raise ValueError('Exact 154 package metadata requests required')
    for path in (ROOT,*ROOT.parents):
        if path.is_symlink() or getattr(path,'is_junction',lambda:False)():raise ValueError('Linked catalog ancestry refused')
    if ROOT.exists() or shutil.disk_usage(REPO).free<1024**3:raise ValueError('Existing catalog or insufficient space')
    ROOT.mkdir(mode=0o700,parents=True)
    start=time.monotonic();deadline=start+120
    def check():
        left=deadline-time.monotonic()-5
        if left<=0:raise TimeoutError('Catalog work budget exhausted; reserve terminal time')
        return left
    claim={'commit':args.commit,'freeze_sha256':FREEZE_SHA,'requests':len(rows),'pid':os.getpid(),
           'started_ms':int(time.time()*1000),'max_work_seconds':120,'max_response_bytes':LIMIT,'GPU_calls':0,'server_operations':0}
    exclusive(ROOT/'claim.json',claim);completed=[];failure=None;opener=urllib.request.build_opener(NoRedirect())
    current=None;status=None
    try:
        for name,version in rows:
            current={'name':name,'version':version};status=None;check()
            url='https://pypi.org/pypi/'+quote(name,safe='')+'/'+quote(version,safe='')+'/json'
            request=urllib.request.Request(url,headers={'User-Agent':'spaceserve-epd-reproduction-metadata'})
            try:response=opener.open(request,timeout=min(10,check()));status=response.status
            except urllib.error.HTTPError as error:response=error.fp;status=error.code
            exclusive(ROOT/(name+'-'+version+'.headers.json'),{**current,'source_url':url,'http_status':status,
                'declared_content_length':response.headers.get('Content-Length'),'observed_ms':int(time.time()*1000)})
            received=bytearray()
            try:
                with response:raw=read_metadata(response,check,received)
            except BaseException:
                with (ROOT/(name+'-'+version+'.response.partial')).open('xb') as stream:stream.write(received[:LIMIT])
                raise
            path=ROOT/(name+'-'+version+'.response.json')
            with path.open('xb') as stream:stream.write(raw)
            exclusive(ROOT/(name+'-'+version+'.receipt.json'),{**current,'source_url':url,'http_status':status,
                'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'observed_ms':int(time.time()*1000)})
            if status!=200:raise ValueError('PyPI exact version not available with HTTP200')
            completed.append(describe(raw,name,version));check()
            print(json.dumps({**current,'http_status':status,'metadata_sha256':hashlib.sha256(raw).hexdigest()}),flush=True)
        if FREEZE.read_bytes()!=before:raise ValueError('Original freeze changed')
    except BaseException as error:failure={'type':type(error).__name__,'package':current,'http_status':status}
    finally:
        exclusive(ROOT/'catalog.json',completed)
        exclusive(ROOT/'terminal.json',{**claim,'ended_ms':int(time.time()*1000),'elapsed_seconds':time.monotonic()-start,
            'completed_packages':len(completed),'complete':failure is None and len(completed)==154,'failure':failure,
            'freeze_unchanged':FREEZE.read_bytes()==before,'artifact_bytes_downloaded':0,'environment_installed':False,
            'CPU_STAGED':False,'GPU_calls':0})
    if failure is not None:raise RuntimeError('Metadata catalog stopped; original responses preserved') from None


if __name__=='__main__':main()
