#!/usr/bin/env bash
set -euo pipefail
export EXP_ROOT=${EXP_ROOT:?Set the dedicated H20 experiment directory}
source "$EXP_ROOT/scripts/env.sh"
PYTHON="$EXP_ROOT/envs/epd/bin/python"
BLOCKS=$("$PYTHON" - "$EXP_ROOT/logs/epd-epoch2.log" <<'PY'
import pathlib, re, sys
sizes = set(map(int, re.findall(r'Num GPU Blocks: (\d+)', pathlib.Path(sys.argv[1]).read_text())))
assert len(sizes) == 1, sizes
print(sizes.pop())
PY
)
SITE="$EXP_ROOT/envs/epd/lib/python3.10/site-packages"
export LD_LIBRARY_PATH="$SITE/torch/lib:$SITE/nvidia/nccl/lib:${LD_LIBRARY_PATH:-}"
"$PYTHON" "$EXP_ROOT/scripts/probe_epd_kv_ipc.py" --source 1 --destination 2 \
    --library "$EXP_ROOT/build/epd-cuda/libcuda_ipc_utils.so" --cache-blocks "$BLOCKS" \
    --transfer-blocks 18 --repetitions 3 --output "$EXP_ROOT/evidence/kv-actual-cache.json"
