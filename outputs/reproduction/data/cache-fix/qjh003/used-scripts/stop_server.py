"""Stop only the process tree of a recorded experiment server PID."""
import os
import pathlib
import sys
import psutil


root = pathlib.Path(sys.argv[1]).resolve()
process = psutil.Process(int(sys.argv[2]))
assert str(root) + "/" in " ".join(process.cmdline()), "PID does not belong to this experiment"
assert process.uids().real == os.getuid(), "PID belongs to another user"
children = process.children(recursive=True)
targets = children + [process]
print("stopping", [(item.pid, item.name()) for item in targets], flush=True)
for item in targets:
    try:
        item.terminate()
    except psutil.NoSuchProcess:
        pass
_, alive = psutil.wait_procs(targets, timeout=8)
for item in alive:
    try:
        item.kill()
    except psutil.NoSuchProcess:
        pass
psutil.wait_procs(alive, timeout=5)
