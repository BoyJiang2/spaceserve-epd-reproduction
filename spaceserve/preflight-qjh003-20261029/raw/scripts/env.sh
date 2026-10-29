#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
: "${SPACESERVE_CONFIG:?explicit project/run configuration required}"
: "${REPRO_PHASE:?explicit numeric/model/formal phase required}"
# Checks precede directories, device queries or CUDA imports.
SPACE_EXPORTS=$(python3 -I -B "$SCRIPT_DIR/runtime_config.py" --shell "$REPRO_PHASE")
eval "$SPACE_EXPORTS"
export TMPDIR="$EXP_ROOT/tmp" XDG_CACHE_HOME="$PROJECT_ROOT/cache"
export HF_HOME="$PROJECT_ROOT/cache/huggingface" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export HF_MODULES_CACHE="$HF_HOME/modules"
export CUDA_CACHE_PATH="$PROJECT_ROOT/cache/cuda" TRITON_CACHE_DIR="$PROJECT_ROOT/cache/triton"
export NUMBA_CACHE_DIR="$PROJECT_ROOT/cache/numba" UV_CACHE_DIR="$PROJECT_ROOT/cache/uv"
mkdir -p "$TMPDIR" "$RAY_TMPDIR" "$HF_MODULES_CACHE" "$CUDA_CACHE_PATH" "$TRITON_CACHE_DIR" "$NUMBA_CACHE_DIR" "$EXP_ROOT/logs/mps"
export OMP_NUM_THREADS=4 TOKENIZERS_PARALLELISM=false
export VLLM_WORKER_MULTIPROC_METHOD=spawn PYTHONFAULTHANDLER=1 PYTHONDONTWRITEBYTECODE=1
if [[ ${REPRO_USE_MPS:-0} == 1 ]]; then
    export CUDA_MPS_PIPE_DIRECTORY="$EXP_ROOT/tmp/mps" CUDA_MPS_LOG_DIRECTORY="$EXP_ROOT/logs/mps"
    export CUDA_MPS_ACTIVE_THREAD_PERCENTAGE=100
fi
