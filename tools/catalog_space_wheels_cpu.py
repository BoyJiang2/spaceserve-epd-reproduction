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
FIRST_INDEX_SHA='7c9613a842a552a68582a6f5651610a03371d3d0a2905bd62565cf944d7114e7'


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


def remaining_rows(rows,old,terminal):
    prefix=[(item['name'],item['version']) for item in old]
    if (len(rows)!=154 or len(prefix)!=89 or prefix!=rows[:89] or terminal['complete'] is not False
            or terminal['completed_packages']!=89 or terminal['requests']!=154
            or terminal['failure']!={'type':'URLError','package':{'name':'opentelemetry-semantic-conventions','version':'0.66b1'},'http_status':None}
            or rows[89]!=('opentelemetry-semantic-conventions','0.66b1')):
        raise ValueError('Only the exact preserved first89 and remaining65 scope allowed')
    return rows[89:]


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
    parser=argparse.ArgumentParser();parser.add_argument('--commit',required=True)
    parser.add_argument('--remaining',action='store_true');args=parser.parse_args()
    if os.name!='nt' or not re.fullmatch('[0-9a-f]{40}',args.commit):raise ValueError('Designated local Windows CPU source required')
    def git(*argv):return subprocess.check_output(['git','-C',str(REPO),*argv],timeout=10)
    if git('rev-parse','HEAD').decode().strip()!=args.commit or git('status','--porcelain','--untracked-files=all').strip():
        raise ValueError('Use the clean published tool commit')
    before=FREEZE.read_bytes()
    if hashlib.sha256(before).hexdigest()!=FREEZE_SHA:raise ValueError('Original exact freeze required')
    rows=packages(before)
    if len(rows)!=154:raise ValueError('Exact 154 package metadata requests required')
    root=ROOT/'remaining' if args.remaining else ROOT;old=[]
    for path in (root,*root.parents):
        if path.is_symlink() or getattr(path,'is_junction',lambda:False)():raise ValueError('Linked catalog ancestry refused')
    if root.exists() or shutil.disk_usage(REPO).free<1024**3:raise ValueError('Existing catalog or insufficient space')
    if args.remaining:
        index_raw=FREEZE.with_name('catalog-first-index.json').read_bytes()
        if hashlib.sha256(index_raw).hexdigest()!=FIRST_INDEX_SHA:raise ValueError('Approved first-unit index differs')
        index=json.loads(index_raw)
        if len(index)!=270 or {p.name for p in ROOT.iterdir()}!={r['name'] for r in index}:raise ValueError('Original unit members differ')
        for row in index:
            path=ROOT/row['name']
            if path.is_symlink() or not path.is_file():raise ValueError('Linked or missing original evidence')
            raw=path.read_bytes()
            if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValueError('Original evidence changed')
        for name,digest in (('claim.json','37748f011507eff6d653c9fb6ce3933ada4bb3f910020de072e47e1471b83491'),
                            ('terminal.json','f66b9e808ead2860d6a5dcf5939de1da8e2155edb1e2a32b66edfd618fe67e80'),
                            ('catalog.json','04502e74384f6a9b05875806180a5ea25ba7d9a2a8ba763731f4f85264c0e809')):
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('G1 original digest differs')
        old=json.loads((ROOT/'catalog.json').read_bytes());terminal=json.loads((ROOT/'terminal.json').read_bytes())
        rows=remaining_rows(rows,old,terminal)
        for item in old:
            stem=item['name']+'-'+item['version'];raw=(ROOT/(stem+'.response.json')).read_bytes()
            receipt=json.loads((ROOT/(stem+'.receipt.json')).read_bytes())
            if (describe(raw,item['name'],item['version'])!=item or receipt['http_status']!=200
                    or receipt['bytes']!=len(raw) or receipt['sha256']!=hashlib.sha256(raw).hexdigest()):
                raise ValueError('Original successful response/receipt mismatch')
    root.mkdir(mode=0o700,parents=True)
    start=time.monotonic();deadline=start+120
    def check():
        left=deadline-time.monotonic()-5
        if left<=0:raise TimeoutError('Catalog work budget exhausted; reserve terminal time')
        return left
    claim={'commit':args.commit,'freeze_sha256':FREEZE_SHA,'requests':len(rows),'pid':os.getpid(),
           'scope':'remaining65' if args.remaining else 'initial154','first_unit_index_sha256':FIRST_INDEX_SHA if args.remaining else None,
           'started_ms':int(time.time()*1000),'max_work_seconds':120,'max_response_bytes':LIMIT,'GPU_calls':0,'server_operations':0}
    exclusive(root/'claim.json',claim);completed=[];failure=None;opener=urllib.request.build_opener(NoRedirect())
    current=None;status=None
    try:
        for name,version in rows:
            current={'name':name,'version':version};status=None;check()
            url='https://pypi.org/pypi/'+quote(name,safe='')+'/'+quote(version,safe='')+'/json'
            request=urllib.request.Request(url,headers={'User-Agent':'spaceserve-epd-reproduction-metadata'})
            try:response=opener.open(request,timeout=min(10,check()));status=response.status
            except urllib.error.HTTPError as error:response=error.fp;status=error.code
            exclusive(root/(name+'-'+version+'.headers.json'),{**current,'source_url':url,'http_status':status,
                'declared_content_length':response.headers.get('Content-Length'),'observed_ms':int(time.time()*1000)})
            received=bytearray()
            try:
                with response:raw=read_metadata(response,check,received)
            except BaseException:
                with (root/(name+'-'+version+'.response.partial')).open('xb') as stream:stream.write(received[:LIMIT])
                raise
            path=root/(name+'-'+version+'.response.json')
            with path.open('xb') as stream:stream.write(raw)
            exclusive(root/(name+'-'+version+'.receipt.json'),{**current,'source_url':url,'http_status':status,
                'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'observed_ms':int(time.time()*1000)})
            if status!=200:raise ValueError('PyPI exact version not available with HTTP200')
            completed.append(describe(raw,name,version));check()
            print(json.dumps({**current,'http_status':status,'metadata_sha256':hashlib.sha256(raw).hexdigest()}),flush=True)
        if FREEZE.read_bytes()!=before:raise ValueError('Original freeze changed')
    except BaseException as error:
        reason=getattr(error,'reason',None);errno=getattr(reason,'errno',None)
        failure={'type':type(error).__name__,'package':current,'http_status':status,
                 'reason_type':None if reason is None else type(reason).__name__,'errno':errno if type(errno) is int else None}
    finally:
        exclusive(root/'catalog.json',completed)
        exclusive(root/'combined-catalog.json',old+completed)
        exclusive(root/'terminal.json',{**claim,'ended_ms':int(time.time()*1000),'elapsed_seconds':time.monotonic()-start,
            'completed_packages':len(completed),'complete':failure is None and len(completed)==len(rows),'failure':failure,
            'combined_packages':len(old)+len(completed),'full_freeze_complete':failure is None and len(old)+len(completed)==154,
            'freeze_unchanged':FREEZE.read_bytes()==before,'artifact_bytes_downloaded':0,'environment_installed':False,
            'CPU_STAGED':False,'GPU_calls':0})
    if failure is not None:raise RuntimeError('Metadata catalog stopped; original responses preserved') from None


if __name__=='__main__':main()
