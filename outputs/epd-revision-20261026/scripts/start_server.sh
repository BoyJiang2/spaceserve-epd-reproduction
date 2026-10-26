#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/env.sh"
ROLE=${1:?epd or baseline-epd}
DEVICES=${2:?GPU indices}
PORT=${3:?port}
export CUDA_VISIBLE_DEVICES="$DEVICES" VLLM_USE_V1=0
export REPRO_RGB_MANIFEST="$EXP_ROOT/dataset/manifest.json"
PY="$EXP_ROOT/envs/epd/bin/python"
MODEL="$EXP_ROOT/models/MiniCPM-V-2_6"
unset PYTHONPATH
if [[ "$ROLE" == epd ]]; then
    "$PY" -B "$SCRIPT_DIR/check_iommu.py" --devices "$DEVICES" --require-compatible
    export PYTHONPATH="$EXP_ROOT/src/epdserve:$SCRIPT_DIR"
    cd "$EXP_ROOT/src/epdserve"
    exec "$PY" -B -u -m epdserve.api_server --host 127.0.0.1 --port "$PORT" \
        --model "$MODEL" --tokenizer "$MODEL" \
        --encoding-data-parallel-size 1 --context-data-parallel-size 1 --decoding-data-parallel-size 1 \
        --intra-request-dp 0 --block-size 16 --max-num-blocks-per-req 256 \
        --gpu-memory-utilization 0.65 --swap-space 1 \
        --encoding-max-batch-size 1 --context-max-batch-size 1 --decoding-max-batch-size 8 \
        --context-max-tokens-per-batch 4096 --decoding-max-tokens-per-batch 4096 \
        --encoding-sched-policy fcfs --context-sched-policy fcfs --decoding-sched-policy fcfs \
        --limit-mm-per-prompt 8
elif [[ "$ROLE" == baseline-epd ]]; then
    cd "$EXP_ROOT"
    exec "$PY" -B -u "$SCRIPT_DIR/baseline_server.py" --model "$MODEL" \
        --dataset "$EXP_ROOT/dataset" --port "$PORT" --gpu-memory-utilization 0.65
else
    echo 'unsupported role' >&2
    exit 2
fi
