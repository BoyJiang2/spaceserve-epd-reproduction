#!/usr/bin/env bash
export EXP_ROOT=/var/tmp/boyjiang-spaceserve-window-20261027-1300
export TMPDIR="$EXP_ROOT/tmp" XDG_CACHE_HOME="$EXP_ROOT/cache"
export HF_HOME="$EXP_ROOT/cache/huggingface" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export HF_MODULES_CACHE="$HF_HOME/modules"
export CUDA_CACHE_PATH="$EXP_ROOT/cache/cuda" TRITON_CACHE_DIR="$EXP_ROOT/cache/triton"
export NUMBA_CACHE_DIR="$EXP_ROOT/cache/numba" UV_CACHE_DIR="$EXP_ROOT/cache/uv"
export RAY_TMPDIR=/var/tmp/bj-space1300-qjh000-ray
mkdir -p "$TMPDIR/ray" "$HF_MODULES_CACHE" "$CUDA_CACHE_PATH" "$TRITON_CACHE_DIR" "$NUMBA_CACHE_DIR" "$EXP_ROOT/logs/mps"
if [[ ! -e "$RAY_TMPDIR" && ! -L "$RAY_TMPDIR" ]]; then ln -s "$TMPDIR/ray" "$RAY_TMPDIR"; fi
[[ $(readlink -f "$RAY_TMPDIR") == "$TMPDIR/ray" ]] || exit 2
export CUDA_HOME=/usr/local/cuda-12.8 OMP_NUM_THREADS=4 TOKENIZERS_PARALLELISM=false
export VLLM_WORKER_MULTIPROC_METHOD=spawn PYTHONFAULTHANDLER=1 PYTHONDONTWRITEBYTECODE=1
if [[ ${REPRO_USE_MPS:-0} == 1 ]]; then
    export CUDA_MPS_PIPE_DIRECTORY="$EXP_ROOT/tmp/mps" CUDA_MPS_LOG_DIRECTORY="$EXP_ROOT/logs/mps"
    export CUDA_MPS_ACTIVE_THREAD_PERCENTAGE=100
fi
