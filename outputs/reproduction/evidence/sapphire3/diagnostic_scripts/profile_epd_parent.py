"""Create a CPU-profile launch variant without editing the official implementation."""
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
source = (root / "scripts/start_server.sh").read_text()
old = 'exec "$EXP_ROOT/envs/epd/bin/python" -u -m epdserve.api_server'
new = 'exec "$EXP_ROOT/envs/epd/bin/python" -m cProfile -o "$EXP_ROOT/results/epd-parent-profile.pstats" -m epdserve.api_server'
assert source.count(old) == 1
(root / "scripts/start_server_parent_profile.sh").write_text(source.replace(old, new))
