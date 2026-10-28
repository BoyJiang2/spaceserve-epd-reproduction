"""Read-only host probe; runs on qjh000 via `ssh qjh000 python3 -I -S - <source_root>`.

Reads only /proc metadata (boot id, own affinity, other processes' Cpus_allowed_list) and the
owned root; never reads environ/cmdline of other processes and never signals anything.
"""
import json
import os
import socket
import sys
import time
from pathlib import Path

PF_KTHREAD = 0x00200000  # per-CPU kernel threads (cpuhp/N, ksoftirqd/N, kworker/N:*) are pinned by design

source_root = Path(sys.argv[1])
own_uid = os.getuid()
pinned_to_50 = []
for entry in Path("/proc").iterdir():
    if not entry.name.isdigit() or int(entry.name) == os.getpid():
        continue
    try:
        status = (entry / "status").read_text()
        stat = (entry / "stat").read_text()
    except OSError:
        continue
    if int(stat[stat.rfind(")") + 2:].split()[6]) & PF_KTHREAD:
        continue
    for line in status.splitlines():
        if line.startswith("Cpus_allowed_list:") and line.split(":", 1)[1].strip() == "50":
            pinned_to_50.append(int(entry.name))
runtime = source_root / "runtime"
active = []
if runtime.exists():
    active = sorted(str(p.relative_to(source_root)) for p in runtime.rglob("CPU-unit-claim.json"))
owned_in_root = []
for entry in Path("/proc").iterdir():
    if not entry.name.isdigit() or int(entry.name) == os.getpid():
        continue
    try:
        if entry.stat().st_uid != own_uid:
            continue
        if Path(os.readlink(entry / "cwd")).is_relative_to(source_root):
            owned_in_root.append(int(entry.name))
    except OSError:
        continue
probe = {
    "origin": "actual_read_only_host_probe",
    "observed_ms": int(time.time() * 1000),
    "host": socket.gethostname(),
    "uid": own_uid,
    "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
    "source_root": str(source_root),
    "available_affinity": [50] if 50 in os.sched_getaffinity(0) else [],
    "cpu50_conflicting_pids": sorted(pinned_to_50),
    "root_active_units": active + ["pid:%d" % pid for pid in sorted(owned_in_root)],
    "source_uid": source_root.stat().st_uid,
    "definitions": {
        "cpu50_conflicting_pids": "user-space processes (PF_KTHREAD clear) whose Cpus_allowed_list is exactly 50 (core reserved by someone else)",
        "root_active_units": "existing CPU-unit-claim.json under SOURCE_ROOT/runtime, plus own processes whose cwd is inside SOURCE_ROOT",
    },
}
print(json.dumps(probe))
