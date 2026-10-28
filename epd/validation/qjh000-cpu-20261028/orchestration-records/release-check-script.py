import json, os, subprocess, sys, time
from pathlib import Path
root = "/var/tmp/boyjiang-epd-cpu-qjh000-20261028/epd/code/fair-pd-candidate-20261028-v13"
rows = []
for item in sys.argv[1:]:
    pid, ticks = map(int, item.split(":"))
    stat = Path(f"/proc/{pid}/stat")
    state = "absent"
    if stat.exists():
        raw = stat.read_text(); same = int(raw[raw.rfind(")")+2:].split()[19]) == ticks
        state = "same_identity_ALIVE" if same else "pid_reused_by_other_process"
    rows.append({"pid": pid, "start_ticks": ticks, "state": state})
owned_in_root = []
for entry in Path("/proc").iterdir():
    if entry.name.isdigit() and int(entry.name) != os.getpid():
        try:
            if entry.stat().st_uid == os.getuid() and os.readlink(entry / "cwd").startswith(root):
                owned_in_root.append(int(entry.name))
        except OSError:
            pass
git = lambda *a: subprocess.check_output(["git", "-C", root, *a], text=True).strip()
print(json.dumps({"observed_ms": int(time.time()*1000), "identities": rows, "own_processes_with_cwd_in_root": owned_in_root,
                  "head": git("rev-parse", "HEAD"), "tracked_clean": git("status", "--porcelain", "--untracked-files=no") == "",
                  "signals_sent": 0, "gpu_queried": False}, indent=2))
