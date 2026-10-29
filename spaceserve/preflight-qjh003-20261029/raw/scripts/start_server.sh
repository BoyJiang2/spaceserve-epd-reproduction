#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/env.sh"
[[ ${REPRO_HOST_LOCK_HELD:-0} == 1 && ${REPRO_USE_MPS:-0} == 1 ]]
ROLE=${1:?role}; GPU=${2:?GPU}; PORT=${3:?port}
[[ "$ROLE" == baseline-space || "$ROLE" == space || "$ROLE" == space-mask ]]
[[ "$GPU" == "$SPACE_GPU_INDEX" && "$PORT" == 19770 ]]
[[ -f "$EXP_ROOT/evidence/G2_MODEL_CODE_APPROVED.json" ]]
export CUDA_VISIBLE_DEVICES=$(nvidia-smi --id="$SPACE_GPU_INDEX" --query-gpu=uuid --format=csv,noheader)
[[ "$CUDA_VISIBLE_DEVICES" == "$SPACE_GPU_UUID" ]]
export REPRO_RGB_MANIFEST="$SPACE_DATASET/manifest.json" REPRO_SYSTEM_ROLE="$ROLE" VLLM_USE_V1=1
unset PYTHONPATH VLLM_LIBSMCTRL_PATH
export PYTHONPATH="$SCRIPT_DIR"
"$SPACE_PYTHON" -B -c 'from model_guard import model_code; model_code()'
if [[ "$ROLE" != baseline-space ]]; then
    export PYTHONPATH="$SPACE_SOURCE:$SCRIPT_DIR"
    if [[ "$ROLE" == space-mask ]]; then
        export VLLM_LIBSMCTRL_PATH="$SPACE_SMCTRL"
    fi
    cd "$EXP_ROOT"
    "$SPACE_PYTHON" -B -c 'import os,pathlib
from vllm.v1.smcontroller import libsmctrl_path
expected=str(pathlib.Path(os.environ["SPACE_SMCTRL"]).resolve()) if os.environ["REPRO_SYSTEM_ROLE"]=="space-mask" else None
actual=str(pathlib.Path(libsmctrl_path).resolve()) if libsmctrl_path else None
if actual!=expected: raise RuntimeError("role/library mismatch")
print("ROLE_LIBRARY",os.environ["REPRO_SYSTEM_ROLE"],actual,flush=True)'
else
    cd "$EXP_ROOT"
fi
exec "$SPACE_PYTHON" -B "$SCRIPT_DIR/baseline_server.py" \
    --model "$SPACE_MODEL" --dataset "$SPACE_DATASET" \
    --port "$PORT" --gpu-memory-utilization 0.65
