#!/usr/bin/env bash
set -euo pipefail
export EXP_ROOT=${EXP_ROOT:?Set the dedicated experiment directory}
source "$EXP_ROOT/scripts/env.sh"
[[ -z $(nvidia-smi --id=0,1,2 --query-compute-apps=pid --format=csv,noheader) ]]
# CUDA 12.4 Update 1 fixes Hopper SIGFPE in cuBLASLt algorithm selection.
"$EXP_ROOT/envs/tools/bin/uv" pip install --python "$EXP_ROOT/envs/epd/bin/python" \
    --index-url https://pypi.tuna.tsinghua.edu.cn/simple --no-deps nvidia-cublas-cu12==12.4.5.8
"$EXP_ROOT/envs/tools/bin/uv" pip freeze --python "$EXP_ROOT/envs/epd/bin/python" >"$EXP_ROOT/evidence/epd-h20-freeze.txt"
"$EXP_ROOT/envs/epd/bin/python" "$EXP_ROOT/scripts/probe_h20_blas.py" --device 0 \
    >"$EXP_ROOT/evidence/blas-after.jsonl"
