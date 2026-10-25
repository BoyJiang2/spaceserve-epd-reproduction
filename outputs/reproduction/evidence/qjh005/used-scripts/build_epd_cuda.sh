#!/usr/bin/env bash
set -euo pipefail
EXP_ROOT=${EXP_ROOT:?Set EXP_ROOT to the dedicated experiment directory}
export TMPDIR="$EXP_ROOT/tmp"
export UV_CACHE_DIR="$EXP_ROOT/cache/uv"
export XDG_CACHE_HOME="$EXP_ROOT/cache"
export HF_HOME="$EXP_ROOT/cache/huggingface"
export CUDA_HOME=/usr/local/cuda
export CONDA_PREFIX="$EXP_ROOT/envs/epd"
SITE="$CONDA_PREFIX/lib/python3.10/site-packages"
export LD_LIBRARY_PATH="$SITE/torch/lib:$SITE/nvidia/nccl/lib:${LD_LIBRARY_PATH:-}"
mkdir -p "$EXP_ROOT/build/epd-cuda"
ln -sfn "$SITE/nvidia/nccl/lib/libnccl.so.2" "$EXP_ROOT/build/epd-cuda/libnccl.so"
export LIBRARY_PATH="$EXP_ROOT/build/epd-cuda:$SITE/nvidia/nccl/lib:${LIBRARY_PATH:-}"
"$CONDA_PREFIX/bin/cmake" -S "$EXP_ROOT/src/epdserve/csrc" -B "$EXP_ROOT/build/epd-cuda" \
    -DCMAKE_CXX_FLAGS="-I/usr/include/python3.10 -I$SITE/nvidia/nccl/include" \
    -DCMAKE_BUILD_RPATH="$SITE/torch/lib;$SITE/nvidia/nccl/lib"
"$CONDA_PREFIX/bin/cmake" --build "$EXP_ROOT/build/epd-cuda" -j 4
export CUDA_IPC_LIB_PATH="$EXP_ROOT/build/epd-cuda/libcuda_ipc_utils.so"
cd "$EXP_ROOT/src/epdserve"
"$CONDA_PREFIX/bin/python" -c 'import torch; import epdserve; print("EPD CUDA extension and Python package imported")'
