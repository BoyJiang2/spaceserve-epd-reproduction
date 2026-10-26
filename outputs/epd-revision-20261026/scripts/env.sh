#!/usr/bin/env bash
set -euo pipefail
export EXP_ROOT=${EXP_ROOT:?dedicated experiment root}
[[ "$EXP_ROOT" == /var/tmp/boyjiang-epd-revision-20261026 && $(hostname) == qjh000 ]]
[[ -f "$EXP_ROOT/CPU_STAGED.json" ]]
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$EXP_ROOT/tmp"
export XDG_CACHE_HOME="$EXP_ROOT/cache"
export HF_HOME="$EXP_ROOT/cache/huggingface"
export HF_MODULES_CACHE="$HF_HOME/modules"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export CUDA_CACHE_PATH="$EXP_ROOT/cache/cuda"
export TRITON_CACHE_DIR="$EXP_ROOT/cache/triton"
export NUMBA_CACHE_DIR="$EXP_ROOT/cache/numba"
export OMP_NUM_THREADS=4 TOKENIZERS_PARALLELISM=false
export VLLM_WORKER_MULTIPROC_METHOD=spawn PYTHONFAULTHANDLER=1
export CUDA_HOME=/usr/local/cuda
mkdir -p "$TMPDIR/ray" "$CUDA_CACHE_PATH" "$TRITON_CACHE_DIR" "$NUMBA_CACHE_DIR"
RAY_SHORT=/var/tmp/boyjiang-er26-ray
if [[ ! -e "$RAY_SHORT" && ! -L "$RAY_SHORT" ]]; then ln -s "$TMPDIR/ray" "$RAY_SHORT"; fi
[[ $(readlink -f "$RAY_SHORT") == "$TMPDIR/ray" ]]
export RAY_TMPDIR="$RAY_SHORT"
unset CUDA_MPS_PIPE_DIRECTORY CUDA_MPS_LOG_DIRECTORY CUDA_MPS_ACTIVE_THREAD_PERCENTAGE VLLM_LIBSMCTRL_PATH
unset PYTHONOPTIMIZE
SITE="$EXP_ROOT/envs/epd/lib/python3.10/site-packages"
export LD_LIBRARY_PATH="$SITE/torch/lib:$SITE/nvidia/nccl/lib:${LD_LIBRARY_PATH:-}"
export CUDA_IPC_LIB_PATH="$EXP_ROOT/build/epd-cuda/libcuda_ipc_utils.so"
