#!/usr/bin/env bash
set -euo pipefail
[[ ${REPRO_HOST_LOCK_HELD:-0} == 1 ]]
ulimit -c 0
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/env.sh"
ROLE=${1:?baseline-space, space, or space-mask}
[[ "$ROLE" == baseline-space || "$ROLE" == space || "$ROLE" == space-mask ]]
[[ ${REPRO_USE_MPS:-0} == 1 ]]
export CUDA_VISIBLE_DEVICES=${2:?GPU index or comma-separated indices}
if [[ ${REPRO_USE_MPS:-0} == 1 ]]; then
    export CUDA_VISIBLE_DEVICES=$(nvidia-smi --id="$2" --query-gpu=uuid --format=csv,noheader | paste -sd, -)
fi
PORT=${3:?Port}
export VLLM_USE_V1=0
unset PYTHONPATH VLLM_LIBSMCTRL_PATH
export REPRO_RGB_MANIFEST="$EXP_ROOT/dataset/manifest.json"
export REPRO_SYSTEM_ROLE="$ROLE" CUDA_MPS_ACTIVE_THREAD_PERCENTAGE=100
export PYTHONPATH="$SCRIPT_DIR"
if [[ "$ROLE" == epd || "$ROLE" == baseline-epd ]]; then
    export REPRO_RGB_MANIFEST="$EXP_ROOT/dataset/manifest.json"
fi
if [[ "$ROLE" == baseline-space || "$ROLE" == space || "$ROLE" == space-mask ]]; then
    PYTHON="$EXP_ROOT/envs/space/bin/python"
    MODEL="$EXP_ROOT/models/Qwen2-VL-7B-Instruct"
    export VLLM_USE_V1=1
    if [[ "$ROLE" == space || "$ROLE" == space-mask ]]; then
        [[ -f "$EXP_ROOT/src/SpaceServe/vllm/__init__.py" ]] || { echo "SpaceServe source is missing" >&2; exit 2; }
        export PYTHONPATH="$EXP_ROOT/src/SpaceServe:$SCRIPT_DIR"
        if [[ "$ROLE" == space-mask ]]; then
            [[ -f "$EXP_ROOT/evidence/SM_EFFECTIVE" || ( ${REPRO_SM_PROBE:-0} == 1 && -f "$EXP_ROOT/evidence/G2_MODEL_APPROVED" && -f "$EXP_ROOT/evidence/SM_NATIVE_APPROVED" ) ]]
            export VLLM_LIBSMCTRL_PATH="$EXP_ROOT/build/libsmctrl.so"
        fi
        cd "$EXP_ROOT/src/SpaceServe"
        "$PYTHON" -c 'import os, pathlib
from vllm.v1.smcontroller import libsmctrl_path
expected = str(pathlib.Path(os.environ["EXP_ROOT"]) / "build/libsmctrl.so") if os.environ["REPRO_SYSTEM_ROLE"] == "space-mask" else None
actual = str(pathlib.Path(libsmctrl_path).resolve()) if libsmctrl_path else None
if actual != expected:
    raise RuntimeError("role/libsmctrl discovery mismatch: " + repr((os.environ["REPRO_SYSTEM_ROLE"], actual, expected)))
print("REPRO_SM_ROLE_LIBRARY", os.environ["REPRO_SYSTEM_ROLE"], actual, flush=True)'
    else
        cd "$EXP_ROOT"
    fi
    exec "$PYTHON" "$SCRIPT_DIR/baseline_server.py" --model "$MODEL" \
        --dataset "$EXP_ROOT/dataset" --port "$PORT" --gpu-memory-utilization 0.65
elif [[ "$ROLE" == baseline-epd ]]; then
    cd "$EXP_ROOT"
    exec "$EXP_ROOT/envs/epd/bin/python" "$SCRIPT_DIR/baseline_server.py" \
        --model "$EXP_ROOT/models/MiniCPM-V-2_6" --dataset "$EXP_ROOT/dataset" \
        --port "$PORT" --gpu-memory-utilization 0.65
elif [[ "$ROLE" == epd ]]; then
    "$EXP_ROOT/envs/epd/bin/python" "$SCRIPT_DIR/check_iommu.py" --devices "$2" --require-compatible
    export CUDA_IPC_LIB_PATH="$EXP_ROOT/build/epd-cuda/libcuda_ipc_utils.so"
    SITE="$EXP_ROOT/envs/epd/lib/python3.10/site-packages"
    export LD_LIBRARY_PATH="$SITE/torch/lib:$SITE/nvidia/nccl/lib:${LD_LIBRARY_PATH:-}"
    export PYTHONPATH="$EXP_ROOT/src/epdserve:$SCRIPT_DIR"
    cd "$EXP_ROOT/src/epdserve"
    exec "$EXP_ROOT/envs/epd/bin/python" -u -m epdserve.api_server \
        --host 127.0.0.1 --port "$PORT" --model "$EXP_ROOT/models/MiniCPM-V-2_6" \
        --tokenizer "$EXP_ROOT/models/MiniCPM-V-2_6" \
        --encoding-data-parallel-size 1 --context-data-parallel-size 1 --decoding-data-parallel-size 1 \
        --intra-request-dp 0 --block-size 16 --max-num-blocks-per-req 256 \
        --gpu-memory-utilization 0.65 --swap-space 1 \
        --encoding-max-batch-size 1 --context-max-batch-size 1 --decoding-max-batch-size 8 \
        --context-max-tokens-per-batch 4096 --decoding-max-tokens-per-batch 4096 \
        --encoding-sched-policy fcfs --context-sched-policy fcfs --decoding-sched-policy fcfs \
        --limit-mm-per-prompt 4
else
    echo "unsupported role: $ROLE" >&2
    exit 2
fi
