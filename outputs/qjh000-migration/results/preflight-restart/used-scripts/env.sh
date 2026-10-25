#!/usr/bin/env bash
export EXP_ROOT=${EXP_ROOT:?Set EXP_ROOT to the dedicated experiment directory}
export TMPDIR="$EXP_ROOT/tmp"
export XDG_CACHE_HOME="$EXP_ROOT/cache"
export HF_HOME="$EXP_ROOT/cache/huggingface"
export HF_MODULES_CACHE="$EXP_ROOT/cache/huggingface/modules"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export UV_CACHE_DIR="$EXP_ROOT/cache/uv"
export CUDA_CACHE_PATH="$EXP_ROOT/cache/cuda"
export TRITON_CACHE_DIR="$EXP_ROOT/cache/triton"
export NUMBA_CACHE_DIR="$EXP_ROOT/cache/numba"
# Ray's Unix sockets require a short pathname; the contents remain in EXP_ROOT.
RAY_SHORT_ROOT="$(dirname "$EXP_ROOT")/bj-space-qjh000-ray"
mkdir -p "$EXP_ROOT/tmp/ray"
if [[ ! -e "$RAY_SHORT_ROOT" && ! -L "$RAY_SHORT_ROOT" ]]; then
    ln -s "$EXP_ROOT/tmp/ray" "$RAY_SHORT_ROOT"
fi
[[ "$(readlink -f "$RAY_SHORT_ROOT")" == "$EXP_ROOT/tmp/ray" ]] || { echo "Ray path already belongs to another directory" >&2; exit 2; }
export RAY_TMPDIR="$RAY_SHORT_ROOT"
export CUDA_HOME=/usr/local/cuda-12.8
export OMP_NUM_THREADS=4
export TOKENIZERS_PARALLELISM=false
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export PYTHONFAULTHANDLER=1
if [[ ${REPRO_USE_MPS:-0} == 1 ]]; then
    export CUDA_MPS_PIPE_DIRECTORY="$EXP_ROOT/tmp/mps"
    export CUDA_MPS_LOG_DIRECTORY="$EXP_ROOT/logs/mps"
fi
mkdir -p "$TMPDIR" "$HF_HOME" "$HF_MODULES_CACHE" "$CUDA_CACHE_PATH" "$TRITON_CACHE_DIR" "$NUMBA_CACHE_DIR"
