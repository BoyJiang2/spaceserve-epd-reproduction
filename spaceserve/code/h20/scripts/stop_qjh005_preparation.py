"""Retire only the recorded qjh005 preparation jobs after verified migration."""
import json
import os
from pathlib import Path
import sys
import psutil

root = Path('/local/boyjiang/spaceserve-h20-7b-20261023')
if os.uname().nodename != 'qjh005':
    raise RuntimeError('wrong source host')
proof = json.loads(Path(sys.argv[1]).read_text())
if proof.get('host') != 'qjh000' or proof.get('fp16_matmul_passed') is not True or proof.get('boot_id') != 'a9617eaa-1638-45fc-8997-a62b528e8f30' or proof.get('packages') != {'torch': '2.5.1', 'vllm': '0.7.2', 'transformers': '4.49.0'}:
    raise RuntimeError('new environment usability proof missing')
if (root / 'evidence/G2_MODEL_APPROVED').exists():
    raise RuntimeError('old GPU launch gate was not suspended')
expected = {
    1512045: ['bash', str(root / 'scripts/start_when_ready.sh'), '1164664'],
    1164664: ['bash', str(root / 'scripts/prepare_environment.sh')],
    1629479: ['python3', '-m', 'http.server', '18670', '--bind', '172.31.35.34', '--directory', '/local/boyjiang/qjh000-migration-export-20261023'],
}
records, targets = [], {}
for pid, command in expected.items():
    try:
        process = psutil.Process(pid)
        if process.status() == psutil.STATUS_ZOMBIE:
            records.append({'pid': pid, 'state': 'already zombie'})
            continue
        if process.uids().real != os.getuid() or process.cmdline() != command:
            raise RuntimeError('recorded preparation PID identity changed: ' + str(pid))
        for item in [process, *process.children(recursive=True)]:
            if item.uids().real != os.getuid() or not (item.pid == pid or str(root) in ' '.join(item.cmdline()) or item.environ().get('EXP_ROOT') == str(root)):
                raise RuntimeError('unexpected descendant; leave all jobs intact')
            targets[item.pid] = item
    except psutil.NoSuchProcess:
        records.append({'pid': pid, 'state': 'already exited'})
for process in targets.values():
    records.append({'pid': process.pid, 'created': process.create_time(), 'command': process.cmdline()})
result = {'source_host': 'qjh005', 'new_host_runtime_proof': proof, 'identified_jobs': records, 'termination': 'TERM only; no system changes or data deletion'}
destination = root / 'evidence/qjh000-migration-stop.json'
if destination.exists():
    raise RuntimeError('preserve previous stop evidence')
destination.write_text(json.dumps(result, indent=2))
for process in targets.values():
    try:
        process.terminate()
    except psutil.NoSuchProcess:
        pass
_, alive = psutil.wait_procs(list(targets.values()), timeout=20)
remaining = [item.pid for item in alive if item.is_running() and item.status() != psutil.STATUS_ZOMBIE]
result['remaining_identified_jobs'] = remaining
destination.write_text(json.dumps(result, indent=2))
print(json.dumps(result), flush=True)
if remaining:
    raise RuntimeError('identified jobs still live; no stronger signal sent')
