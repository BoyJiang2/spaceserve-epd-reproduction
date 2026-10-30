"""Exact renewed CPU lane only; grants neither GPU work nor runtime Gates."""
BOOKING=dict(id='bk-20261030T0311-c71b1c22',node='qjh003',resource_id='h20/qjh003',
    kind='cpu',user='boyjiang',start_ms=1793329200000,end_ms=1793347200000)


def validate(proof,now_ms,seconds):
    if type(now_ms) is not int or type(seconds) is not int or not 0<seconds<=360:
        raise ValueError('Exact clock and bounded CPU unit required')
    observed=proof.get('observed_ms')
    if (proof.get('origin')!='gputime_read_only_api' or proof.get('read_only') is not True
            or type(observed) is not int or not 0<=now_ms-observed<=300000):
        raise ValueError('Fresh actual read-only CPU booking snapshot required')
    resource=[r for r in proof['resources'] if r.get('id')=='h20/qjh003']
    tickets=[r for r in proof['bookings'] if r.get('id')==BOOKING['id']]
    finish=now_ms+seconds*1000
    if (len(resource)!=1 or resource[0].get('node')!='qjh003' or resource[0].get('active') is not True
            or len(tickets)!=1 or tickets[0]!=BOOKING
            or now_ms<BOOKING['start_ms'] or finish+120000>BOOKING['end_ms']):
        raise ValueError('Exact renewed11-16 CPU lane and full cleanup reserve required')
    for row in proof['bookings']:
        if row.get('resource_id')!='h20/qjh003' or row.get('kind')=='gpu':continue
        if row.get('kind') not in (None,'cpu'):raise ValueError('Unknown CPU resource lane')
        if type(row.get('start_ms')) is not int or type(row.get('end_ms')) is not int:
            raise ValueError('Unknown CPU booking interval')
        if row['start_ms']<finish+120000 and row['end_ms']>now_ms and row.get('user')!='boyjiang':
            raise ValueError('Foreign CPU/whole-node reservation conflicts')
    return dict(work_seconds=seconds,booking_end_ms=BOOKING['end_ms'],cleanup_reserve_seconds=120,
        CPU_booking_id=BOOKING['id'],GPU_approved=False,runtime_Gates_granted=False)
