#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export REPRO_USE_MPS=1
source "$SCRIPT_DIR/env.sh"
ACTION=${1:?start, status, or stop}
if [[ "$ACTION" == start ]]; then
    DEVICES=${2:?Comma-separated physical GPU indices}
    export CUDA_VISIBLE_DEVICES=$(nvidia-smi --id="$DEVICES" --query-gpu=uuid --format=csv,noheader | paste -sd, -)
    mkdir -p "$CUDA_MPS_PIPE_DIRECTORY" "$CUDA_MPS_LOG_DIRECTORY"
    chmod 700 "$CUDA_MPS_PIPE_DIRECTORY" "$CUDA_MPS_LOG_DIRECTORY"
    echo "$CUDA_VISIBLE_DEVICES" >"$EXP_ROOT/results/mps-gpu-uuids.txt"
    nvidia-cuda-mps-control -d
elif [[ "$ACTION" == status ]]; then
    echo get_server_list | nvidia-cuda-mps-control
    echo ps | nvidia-cuda-mps-control
elif [[ "$ACTION" == stop ]]; then
    echo quit | nvidia-cuda-mps-control
else
    exit 2
fi
