"""Inspect fixed EPD startup assets before any separately approved relocation."""
import hashlib,json,os,socket,sys,time
from pathlib import Path
ROOT=Path('/local/boyjiang/epd')
BOOT='65f52a67-afe4-4919-8646-4694255b48ee'

def main():
    data=json.load(sys.stdin);now=int(time.time()*1000);started=time.monotonic()
    if data.get('phase')!='inspect':raise ValueError('Only read-only inspection implemented')
    if socket.gethostname()!='qjh003' or os.getuid()!=2147 or os.sched_getaffinity(0)!={50} or os.getpriority(os.PRIO_PROCESS,0)!=10:raise ValueError('Executor differs')
    if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=BOOT:raise ValueError('Boot differs')
    proof=data['booking'];expected=dict(id='bk-20261029T0057-e2efd603',node='qjh003',resource_id='h20/qjh003',kind='cpu',user='boyjiang',start_ms=1793235600000,end_ms=1793239200000)
    tickets=[b for b in proof['bookings'] if b.get('id')==expected['id']];resources=[r for r in proof['resources'] if r.get('id')=='h20/qjh003']
    if (proof.get('origin')!='gputime_read_only_api' or proof.get('read_only') is not True or type(proof.get('observed_ms')) is not int or not 0<=now-proof['observed_ms']<=300000 or len(tickets)!=1 or tickets[0]!=expected or len(resources)!=1 or resources[0].get('active') is not True or now<expected['start_ms'] or now+210000>expected['end_ms']):raise ValueError('Fresh exact owned CPU slot/full60+30 before09:58 required')
    def check():
        if time.monotonic()-started>=60 or int(time.time()*1000)+120000>=expected['end_ms']:raise TimeoutError('Inspection deadline')
    def real(path):
        for item in (path,*path.parents):
            if item.is_symlink():raise ValueError('Managed symlink refused')
            if item.exists() and item.is_relative_to('/local/boyjiang') and item.stat().st_uid!=2147:raise ValueError('Foreign managed owner')
    def read(path,text=False):
        check();real(path)
        if not path.is_file() or path.stat().st_size>65536:raise ValueError('Expected small owned regular startup file')
        raw=path.read_bytes();row=dict(path=path.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        if text:row['text']=raw.decode('utf8')
        return row
    real(ROOT);env=ROOT/'assets/envs/epd';site=env/'lib/python3.10/site-packages';real(site);binpath=env/'bin';real(binpath)
    files=[read(env/'pyvenv.cfg',True)]
    for path in sorted(site.glob('*.pth')):files.append(read(path,True))
    for name in ('sitecustomize.py','usercustomize.py'):
        path=site/name;real(path)
        if path.exists():files.append(read(path,True))
    for path in sorted(binpath.iterdir()):
        check()
        if path.is_symlink():continue
        real(path)
        if path.is_file():
            with path.open('rb') as stream:first=stream.readline(1024)
            if path.name.startswith('activate'):files.append(read(path,True))
            elif first.startswith(b'#!'):files.append(read(path,False)|dict(first_line=first.decode('utf8').strip()))
    links=[]
    for name in ('python','python3','python3.10'):
        path=binpath/name;real(path.parent)
        if path.is_symlink():links.append(dict(path=path.relative_to(ROOT).as_posix(),link=os.readlink(path),resolved=str(path.resolve(strict=True))))
        elif path.exists():links.append(read(path,False))
    check();print(json.dumps(dict(phase='inspect',scope='CPU static only; no imports from relocated environment, no GPU or writes',host=socket.gethostname(),uid=os.getuid(),boot=BOOT,observed_ms=now,files=files,python_links=links,elapsed_seconds=time.monotonic()-started)),flush=True)

if __name__=='__main__':main()
