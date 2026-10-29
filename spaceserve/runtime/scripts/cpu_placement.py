"""Explicit shared logical-CPU budget; no CUDA context or model imports."""
import os
from pathlib import Path
import re
import subprocess


ENVIRONMENT = ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS')


def cpu_list(value):
    result = set()
    for part in value.strip().split(','):
        ends = part.split('-')
        if len(ends) not in (1, 2) or any(not x.isdecimal() for x in ends):
            raise ValueError('Invalid Linux CPU list')
        start, end = int(ends[0]), int(ends[-1])
        if start > end or end > 65535:
            raise ValueError('Invalid Linux CPU range')
        members = set(range(start, end + 1))
        if result & members:
            raise ValueError('Duplicate logical CPU')
        result.update(members)
    return result


def expected(config):
    names = ('workload_cpu_affinity', 'workload_numa_node')
    if not any(name in config for name in names):
        return None
    cpus, node = (config.get(name) for name in names)
    if (not isinstance(cpus, list) or not cpus
            or any(type(cpu) is not int or cpu < 0 or cpu > 65535 for cpu in cpus)
            or cpus != sorted(set(cpus)) or type(node) is not int or not 0 <= node <= 65535):
        raise ValueError('Explicit sorted logical CPU list and NUMA node required')
    return set(cpus)


def apply(config, action):
    cpus = expected(config)
    if cpus is None or action not in ('numeric', 'model', 'formal'):
        return False
    node = config['workload_numa_node']
    node_cpus = cpu_list(Path(f'/sys/devices/system/node/node{node}/cpulist').read_text())
    online = cpu_list(Path('/sys/devices/system/cpu/online').read_text())
    if cpus != node_cpus or not cpus <= online:
        raise ValueError('CPU profile differs from the current complete online NUMA node')
    uuids = config.get('gpu_uuids')
    if not isinstance(uuids, list) or len(uuids) != 1:
        raise ValueError('One approved GPU UUID required for CPU placement')
    rows = subprocess.check_output(['nvidia-smi', '--query-gpu=uuid,pci.bus_id',
                                    '--format=csv,noheader,nounits'], text=True, timeout=15)
    matches = [row.split(',') for row in rows.splitlines() if row.split(',')[0].strip() == uuids[0]]
    if len(matches) != 1 or len(matches[0]) != 2:
        raise ValueError('GPU UUID/PCI identity missing or ambiguous')
    pci = matches[0][1].strip().lower()
    # nvidia-smi prints an eight-digit domain; Linux sysfs uses four digits.
    parts = pci.split(':')
    if not re.fullmatch(r'00000000:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]', pci):
        raise ValueError('Unexpected GPU PCI domain')
    pci = '0000:' + ':'.join(parts[1:])
    if int(Path(f'/sys/bus/pci/devices/{pci}/numa_node').read_text()) != node:
        raise ValueError('GPU is not on the approved CPU NUMA node')
    os.sched_setaffinity(0, cpus)
    if set(os.sched_getaffinity(0)) != cpus:
        raise RuntimeError('OS did not apply the exact CPU profile')
    return True


def snapshot(pid=None):
    pid = os.getpid() if pid is None else pid
    root = Path('/proc') / str(pid)
    before = (root / 'stat').read_text()
    fields = before[before.rfind(')') + 2:].split()
    threads = {str(path.name): sorted(os.sched_getaffinity(int(path.name)))
               for path in sorted((root / 'task').iterdir())}
    environment = dict(item.split('=', 1) for item in (root / 'environ').read_bytes().decode().split('\0')
                       if '=' in item)
    record = {'pid': pid, 'start_ticks': int(fields[19]), 'uid': root.stat().st_uid,
              'nice': int(fields[16]), 'main_affinity': sorted(os.sched_getaffinity(pid)),
              'thread_affinity': threads, 'thread_count': len(threads),
              'environment': {key: environment.get(key) for key in ENVIRONMENT}}
    after = (root / 'stat').read_text()
    if after[after.rfind(')') + 2:].split()[19] != fields[19]:
        raise RuntimeError('Process identity changed during CPU snapshot')
    return record


def validate(record, config):
    cpus = expected(config)
    if cpus is None:
        return
    if (not isinstance(record, dict) or record.get('main_affinity') != sorted(cpus)
            or not record.get('thread_affinity')
            or record.get('thread_count') != len(record['thread_affinity'])
            or any(not mask or not set(mask) <= cpus for mask in record['thread_affinity'].values())):
        raise RuntimeError('Actual main/thread CPU placement differs from shared CPU budget')
