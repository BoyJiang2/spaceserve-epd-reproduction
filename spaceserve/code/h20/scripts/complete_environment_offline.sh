#!/usr/bin/env bash
set -euo pipefail
export EXP_ROOT=/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023
[[ $(hostname) == qjh000 && -f "$EXP_ROOT/evidence/G1_APPROVED" && ! -f "$EXP_ROOT/evidence/environment-READY" ]]
export TMPDIR="$EXP_ROOT/tmp" XDG_CACHE_HOME="$EXP_ROOT/cache"
export UV_CACHE_DIR="$EXP_ROOT/cache-sapphire/cache/uv" UV_PYTHON_DOWNLOADS=never
export HF_HOME="$EXP_ROOT/cache/huggingface" HF_MODULES_CACHE="$EXP_ROOT/cache/huggingface/modules"
export CUDA_CACHE_PATH="$EXP_ROOT/cache/cuda" TRITON_CACHE_DIR="$EXP_ROOT/cache/triton" PIP_CACHE_DIR="$EXP_ROOT/cache/pip"
export CUDA_HOME=/usr/local/cuda-12.8
"$EXP_ROOT/envs/manage/bin/python" "$EXP_ROOT/scripts/adopt_offline_environment.py" >"$EXP_ROOT/logs/adopt-offline.log" 2>&1
UV="$EXP_ROOT/envs/uv-sapphire"
PY="$EXP_ROOT/envs/space/bin/python"
"$UV" --version >"$EXP_ROOT/evidence/uv-offline-version.txt"
"$UV" pip install --offline --no-deps --python "$PY" --index-url https://pypi.tuna.tsinghua.edu.cn/simple -r "$EXP_ROOT/configs/space-freeze.txt" >"$EXP_ROOT/logs/install-offline.log" 2>&1
env -u PYTHONPATH "$PY" "$EXP_ROOT/scripts/prepare_space.py" "$EXP_ROOT" >"$EXP_ROOT/logs/prepare-space.log" 2>&1
"$PY" "$EXP_ROOT/scripts/apply_space_compat.py" "$EXP_ROOT" >"$EXP_ROOT/logs/compat-space.log" 2>&1
make -C "$EXP_ROOT/src/mysmctrl" libsmctrl.so >"$EXP_ROOT/logs/build-smctrl.log" 2>&1
mkdir -p "$EXP_ROOT/build"
cp "$EXP_ROOT/src/mysmctrl/libsmctrl.so" "$EXP_ROOT/build/libsmctrl.so"
"$UV" pip freeze --python "$PY" >"$EXP_ROOT/evidence/installed-freeze.txt"
"$UV" pip check --python "$PY" >"$EXP_ROOT/evidence/pip-check.txt" 2>&1
env -u PYTHONPATH "$PY" -c 'import torch, transformers, vllm; print(torch.__version__,torch.version.cuda,transformers.__version__,vllm.__version__)' >"$EXP_ROOT/evidence/dependency-import.txt" 2>&1
sha256sum "$EXP_ROOT/build/libsmctrl.so" >"$EXP_ROOT/evidence/libsmctrl.sha256"
date -u +%FT%TZ >"$EXP_ROOT/evidence/environment-READY"
