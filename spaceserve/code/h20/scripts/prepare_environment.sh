#!/usr/bin/env bash
set -euo pipefail
export EXP_ROOT=/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023
[[ $(hostname) == qjh000 && -f "$EXP_ROOT/evidence/G1_APPROVED" && ! -f "$EXP_ROOT/evidence/environment-READY" ]]
export TMPDIR="$EXP_ROOT/tmp" XDG_CACHE_HOME="$EXP_ROOT/cache" UV_CACHE_DIR="$EXP_ROOT/cache/uv"
export HF_HOME="$EXP_ROOT/cache/huggingface" HF_MODULES_CACHE="$EXP_ROOT/cache/huggingface/modules"
export CUDA_CACHE_PATH="$EXP_ROOT/cache/cuda" TRITON_CACHE_DIR="$EXP_ROOT/cache/triton"
export PIP_CACHE_DIR="$EXP_ROOT/cache/pip" UV_PYTHON_DOWNLOADS=never UV_HTTP_TIMEOUT=180 UV_HTTP_RETRIES=3
export CUDA_HOME=/usr/local/cuda-12.8
[[ $(df --output=avail -B1 "$EXP_ROOT" | tail -1) -gt $((180*1024*1024*1024)) ]]
python3 "$EXP_ROOT/scripts/fetch_assets.py" >"$EXP_ROOT/logs/fetch-assets.log" 2>&1
[[ $(sha256sum "$EXP_ROOT/configs/space-freeze.txt" | cut -d' ' -f1) == 12cc7ae16e15cb32a58d197b10c139df7d715a8c3eeb4246b77eebe5d4814b0f ]]
[[ $(git -C "$EXP_ROOT/src/SpaceServe" rev-parse HEAD) == 66de079af4234b27f7f82ff91d238ef1351324ba ]]
[[ $(git -C "$EXP_ROOT/src/mysmctrl" rev-parse HEAD) == 6ff57356968a3f04158b9273aa881ee6bdf04229 ]]
"$EXP_ROOT/envs/uv" --version >"$EXP_ROOT/evidence/uv-version.txt"
"$EXP_ROOT/envs/uv" venv --allow-existing --python /usr/bin/python3 "$EXP_ROOT/envs/space"
"$EXP_ROOT/envs/uv" pip install --python "$EXP_ROOT/envs/space/bin/python" --index-url https://pypi.tuna.tsinghua.edu.cn/simple -r "$EXP_ROOT/configs/space-freeze.txt" >"$EXP_ROOT/logs/install-environment.log" 2>&1
PY="$EXP_ROOT/envs/space/bin/python"
env -u PYTHONPATH "$PY" "$EXP_ROOT/scripts/prepare_space.py" "$EXP_ROOT" >"$EXP_ROOT/logs/prepare-space.log" 2>&1
"$PY" "$EXP_ROOT/scripts/apply_space_compat.py" "$EXP_ROOT" >"$EXP_ROOT/logs/compat-space.log" 2>&1
make -C "$EXP_ROOT/src/mysmctrl" libsmctrl.so >"$EXP_ROOT/logs/build-smctrl.log" 2>&1
mkdir -p "$EXP_ROOT/build"
cp "$EXP_ROOT/src/mysmctrl/libsmctrl.so" "$EXP_ROOT/build/libsmctrl.so"
"$EXP_ROOT/envs/uv" pip freeze --python "$PY" >"$EXP_ROOT/evidence/installed-freeze.txt"
"$EXP_ROOT/envs/uv" pip check --python "$PY" >"$EXP_ROOT/evidence/pip-check.txt" 2>&1
env -u PYTHONPATH "$PY" -c 'import torch, transformers, vllm; print(torch.__version__,torch.version.cuda,transformers.__version__,vllm.__version__)' >"$EXP_ROOT/evidence/dependency-import.txt" 2>&1
sha256sum "$EXP_ROOT/build/libsmctrl.so" >"$EXP_ROOT/evidence/libsmctrl.sha256"
date -u +%FT%TZ >"$EXP_ROOT/evidence/environment-READY"
