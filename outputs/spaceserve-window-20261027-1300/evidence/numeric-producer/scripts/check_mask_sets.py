"""Validate actual stream identities and reversible SM-set changes; no CUDA import."""
EXPECTED_UUID='GPU-79214c80-7778-37d9-282b-89228debbb69'


def validate(records, masked):
    labels={row['label']:row for row in records}
    required={'before-existing-mask','after-existing-mask','first-encoder-execution'}
    if masked:
        required|={'restored-to-zero-mask','reapplied-existing-mask'}
    if set(labels)!=required or len(labels)!=len(records):
        raise RuntimeError('missing or duplicate actual-stream SM records')
    identity={(row['pid'],row['stream'],row['visible_gpu_uuid']) for row in records}
    if len(identity)!=1 or next(iter(identity))[2]!=EXPECTED_UUID:
        raise RuntimeError('actual stream/PID/GPU identity differs')
    if any(row['mps_active_thread_percentage']!='100' or not row['mps_pipe'] or row['masked_group'] is not masked for row in records):
        raise RuntimeError('actual stream MPS/role identity differs')
    sets={label:set(row['sm_ids']) for label,row in labels.items()}
    if any(not value for value in sets.values()):
        raise RuntimeError('empty actual SM sample')
    before, after=sets['before-existing-mask'],sets['after-existing-mask']
    if masked:
        if not after<before or sets['restored-to-zero-mask']!=before or sets['reapplied-existing-mask']!=after:
            raise RuntimeError('mask is not a strict reversible reproducible SM subset')
    elif before!=after:
        raise RuntimeError('unmasked stream SM set changed')
    if sets['first-encoder-execution']!=after:
        raise RuntimeError('first execution does not use the verified stream SM set')
    return {'passed':True,'masked':masked,'before':sorted(before),'after':sorted(after),
            'scope':'actual encoder stream only; no decoder mutual exclusion or throughput fraction claim'}
