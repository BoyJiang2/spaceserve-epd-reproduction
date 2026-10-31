"""Direct human CPU permission, subject to fresh booking clearance; no GPU grant."""
START_MS=1793412000000  # 2026-10-31 10:00 Asia/Shanghai
END_MS=1793426400000    # Self-imposed 2026-10-31 14:00 stop; not a booking


def acquire_cpu50():
    import fcntl
    import os
    from pathlib import Path
    import stat
    parent=Path('/local/boyjiang')
    if parent.is_symlink() or not parent.is_dir() or parent.stat().st_uid!=os.getuid():
        raise ValueError('Own real CPU control directory required')
    fd=os.open(parent/'epd-space-cpu50-20261030.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
    try:
        info=os.fstat(fd)
        if (info.st_uid!=os.getuid() or info.st_nlink!=1 or not stat.S_ISREG(info.st_mode)
                or stat.S_IMODE(info.st_mode)&0o077):
            raise ValueError('Unsafe shared CPU control lock')
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return fd  # Keep until controller exit; every new Space CPU controller must use this lock.
    except BaseException:
        os.close(fd);raise


def normalize_snapshot(data,now_ms):
    if (not isinstance(data,dict) or type(now_ms) is not int or any(
            not isinstance(data.get(name),list) or any(not isinstance(row,dict) for row in data[name])
            for name in ('resources','bookings'))):
        raise ValueError('Raw API must contain complete resource and booking lists')
    for row in data['resources']:
        if (not isinstance(row.get('id'),str) or not row['id']
                or not isinstance(row.get('node'),str) or type(row.get('active')) is not bool):
            raise ValueError('Malformed raw resource')
    for row in data['bookings']:
        if (not isinstance(row.get('resource_id'),str) or not row['resource_id']
                or row.get('kind') not in (None,'cpu','gpu')
                or not isinstance(row.get('user'),str) or not row['user']
                or type(row.get('start_ms')) is not int or type(row.get('end_ms')) is not int
                or row['start_ms']>=row['end_ms']):
            raise ValueError('Malformed raw booking')
    return dict(origin='gputime_read_only_api',read_only=True,observed_ms=now_ms,
        resources=[{k:r.get(k) for k in ('id','node','active','gpu_count')}
                   for r in data['resources'] if r['id']=='h20/qjh003'],
        bookings=[{k:r.get(k) for k in ('id','node','resource_id','kind','user','start_ms','end_ms')}
                  for r in data['bookings'] if r['resource_id']=='h20/qjh003'])


def snapshot():
    import importlib.util
    import json
    from pathlib import Path
    import subprocess
    import time
    path=Path('C:/Users/23520/.codex/skills/gputime-booking-agent/scripts/gputime_agent.py')
    spec=importlib.util.spec_from_file_location('owned_booking_client',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    class Args:token_file=str(module.default_token_file())
    config='url = "https://gputime.approaching-ai.com/api/agent/snapshot"\nheader = '+json.dumps('Authorization: Bearer '+module.load_token(Args()))+'\nheader = "Accept: application/json"\n'
    result=subprocess.run(['curl.exe','--disable','--silent','--show-error','--fail','--connect-timeout','10','--max-time','25','--config','-'],input=config.encode(),capture_output=True,timeout=30)
    if result.returncode:raise RuntimeError('Booking read failed; sensitive response omitted; no dispatch')
    return normalize_snapshot(json.loads(result.stdout),int(time.time()*1000))


def validate(proof,now_ms,seconds):
    if (not isinstance(proof,dict) or any(
            not isinstance(proof.get(name),list) or any(not isinstance(row,dict) for row in proof[name])
            for name in ('resources','bookings'))):
        raise ValueError('Complete resource and booking lists required')
    if any(not isinstance(row.get(key),str) or not row[key]
           for name,key in (('resources','id'),('bookings','resource_id')) for row in proof[name]):
        raise ValueError('Every resource and booking must identify its resource')
    if type(now_ms) is not int or type(seconds) is not int or not 0<seconds<=300:
        raise ValueError('Exact clock and bounded CPU unit required')
    observed=proof.get('observed_ms')
    if (proof.get('origin')!='gputime_read_only_api' or proof.get('read_only') is not True
            or type(observed) is not int or observed<START_MS
            or not 0<=now_ms-observed<=300000):
        raise ValueError('Fresh actual read-only snapshot for today required')
    finish=now_ms+seconds*1000+30000
    if now_ms<START_MS or finish>END_MS:
        raise ValueError('Complete EPD CPU unit and cleanup must finish before14')
    resources=[r for r in proof['resources'] if r.get('id')=='h20/qjh003']
    if (len(resources)!=1 or resources[0].get('node')!='qjh003'
            or resources[0].get('active') is not True):
        raise ValueError('Active qjh003 resource required')
    for row in proof['bookings']:
        if row.get('resource_id')!='h20/qjh003':continue
        if row.get('kind')=='gpu':continue
        if row.get('kind') not in (None,'cpu'):
            raise ValueError('Unknown CPU resource lane')
        if (type(row.get('start_ms')) is not int or type(row.get('end_ms')) is not int
                or row['start_ms']>=row['end_ms'] or not row.get('user')):
            raise ValueError('Unknown CPU booking interval or owner')
        if row['start_ms']<finish and row['end_ms']>now_ms and row['user']!='boyjiang':
            raise ValueError('Foreign CPU/whole-node reservation conflicts')
    return dict(work_seconds=seconds,authorization_end_ms=END_MS,cleanup_reserve_seconds=30,
        authorization_kind='explicit-human-direct-CPU-use-subject-to-fresh-clearance',
        cpu_booking_claimed=False,CPU_booking_id=None,GPU_approved=False,runtime_Gates_granted=False)
