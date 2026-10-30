"""Exact 04–10 window admission only; never a runtime Gate or GPU launcher."""
START = 1793376000000
END = 1793415600000
RESOURCE = 'h20/qjh003'
CPU = None  # Direct human CPU authorization; no CPU booking claim.
GPU = 'bk-20261030T0301-bd62e6dd'
BUDGETS = {'prepare':240, 'cpu':240, 'numeric':900, 'model':1800, 'formal':12060}


def human_confirmation(configuration,now_ms):
    return dict(origin='direct-human-reservation-confirmation-20261031',read_only=True,
        human_confirmed=True,authorization_reference='user-confirmed-qjh003-20261031-API-network-failure',
        observed_ms=now_ms,resources=[dict(id=RESOURCE,node='qjh003',active=True,gpu_count=8)],
        bookings=[dict(configuration['booking'],resource_id=RESOURCE,node='qjh003',kind='gpu',user='boyjiang')])


def validate(snapshot, now_ms, phase, configuration):
    if phase not in BUDGETS or type(now_ms) is not int:
        raise ValueError('Unknown phase or clock')
    if (configuration.get('run_id') != 'space-20261031-0000'
            or configuration.get('host') != 'qjh003' or configuration.get('uid') != 2147
            or configuration.get('gpu_devices') != [2]
            or configuration.get('gpu_uuids') != ['GPU-c005197e-747d-2dc8-b77b-b123b41efd75']
            or configuration.get('booking') != dict(id=GPU,start_ms=START,end_ms=END)
            or configuration.get('workload_cpu_affinity') != list(range(90))
            or configuration.get('workload_numa_node') != 0 or configuration.get('mask_off') != 56
            or 'temporary_gpu_use' in configuration):
        raise ValueError('Frozen window parameters differ')
    observed = snapshot.get('observed_ms')
    human=(snapshot.get('origin')=='direct-human-reservation-confirmation-20261031'
           and snapshot.get('human_confirmed') is True
           and snapshot.get('authorization_reference')=='user-confirmed-qjh003-20261031-API-network-failure')
    if (snapshot.get('origin') != 'gputime_read_only_api' and not human):
        raise ValueError('Actual API or explicit current human authorization required')
    if (snapshot.get('read_only') is not True
            or type(observed) is not int or not START <= observed <= now_ms
            or now_ms-observed > 300000):
        raise ValueError('Actual fresh after-start snapshot required')
    resources = [row for row in snapshot['resources'] if row.get('id') == RESOURCE]
    if (len(resources) != 1 or resources[0].get('node') != 'qjh003'
            or resources[0].get('active') is not True or resources[0].get('gpu_count') != 8):
        raise ValueError('Actual active resource differs')
    budget = BUDGETS[phase]
    finish = now_ms+(budget+120)*1000
    if not START <= now_ms or finish > END:
        raise ValueError('Complete work and cleanup budget unavailable')
    for kind, ticket, end in [('gpu',GPU,END)]:
        rows = [row for row in snapshot['bookings'] if row.get('id') == ticket]
        expected = dict(id=ticket, resource_id=RESOURCE, node='qjh003', kind=kind,
                        user='boyjiang', start_ms=START, end_ms=end)
        if len(rows) != 1 or any(rows[0].get(k) != v for k,v in expected.items()):
            raise ValueError('Exact current owned lane required')
    for row in snapshot['bookings']:
        if (row.get('resource_id') == RESOURCE and row.get('user') != 'boyjiang'
                and row.get('kind') in (None,'cpu','gpu')
                and row['start_ms'] < finish and row['end_ms'] > now_ms):
            raise ValueError('Foreign booking intersects actual unit')
    return dict(work_seconds=budget, cleanup_seconds=120, booking_end_ms=END,
                source_or_runtime_Gates_granted=False)
