#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ROLE=${1:?space or epd}
export EXP_ROOT=${2:?Dedicated experiment directory}
mkdir -p "$EXP_ROOT"/{src,envs,models,cache,tmp,logs,results,build,scripts,evidence}
export TMPDIR="$EXP_ROOT/tmp" UV_CACHE_DIR="$EXP_ROOT/cache/uv"
INDEX=https://pypi.tuna.tsinghua.edu.cn/simple
if [[ ! -x "$EXP_ROOT/envs/$ROLE/bin/python" ]]; then
    REQUIRED_GIB=20
    [[ "$ROLE" != epd ]] || REQUIRED_GIB=35
    AVAILABLE=$(df --output=avail -B1 "$EXP_ROOT" | tail -1)
    ((AVAILABLE >= REQUIRED_GIB * 1024 * 1024 * 1024)) || { echo "Insufficient data-disk space" >&2; exit 2; }
fi

checkout() {
    local REPO=$1 DESTINATION=$2 COMMIT=$3
    if [[ ! -d "$DESTINATION/.git" ]]; then
        git init "$DESTINATION"
        git -C "$DESTINATION" remote add origin "https://github.com/$REPO.git"
        git -C "$DESTINATION" -c http.version=HTTP/1.1 fetch --depth 1 origin "$COMMIT"
        git -C "$DESTINATION" checkout --detach "$COMMIT"
    fi
    [[ "$(git -C "$DESTINATION" rev-parse HEAD)" == "$COMMIT" ]] || { echo "Unexpected source revision" >&2; exit 2; }
}

if [[ "$ROLE" == space ]]; then
    checkout gofreelee/SpaceServe "$EXP_ROOT/src/SpaceServe" 66de079af4234b27f7f82ff91d238ef1351324ba
    checkout gofreelee/mysmctrl "$EXP_ROOT/src/mysmctrl" 6ff57356968a3f04158b9273aa881ee6bdf04229
    uv venv --allow-existing --python /usr/bin/python3 "$EXP_ROOT/envs/space"
    uv pip install --python "$EXP_ROOT/envs/space/bin/python" --index-url "$INDEX" -r "$SCRIPT_DIR/../configs/space-freeze.txt"
    "$EXP_ROOT/envs/space/bin/python" "$SCRIPT_DIR/prepare_space.py" "$EXP_ROOT"
    "$EXP_ROOT/envs/space/bin/python" "$SCRIPT_DIR/apply_space_compat.py" "$EXP_ROOT"
    make -C "$EXP_ROOT/src/mysmctrl" libsmctrl.so
    cp "$EXP_ROOT/src/mysmctrl/libsmctrl.so" "$EXP_ROOT/build/libsmctrl.so"
    python3 "$SCRIPT_DIR/download_model.py" Qwen/Qwen2-VL-2B-Instruct "$EXP_ROOT/models/Qwen2-VL-2B-Instruct" \
        --manifest "$SCRIPT_DIR/../configs/qwen-model-manifest.json"
elif [[ "$ROLE" == epd ]]; then
    checkout vbdi/epdserve "$EXP_ROOT/src/epdserve" 9b111f710dfb4724072b603d626a1e4dad93ef1f
    uv venv --allow-existing --python /usr/bin/python3 "$EXP_ROOT/envs/epd"
    uv pip install --python "$EXP_ROOT/envs/epd/bin/python" --index-url "$INDEX" -r "$SCRIPT_DIR/../configs/epd-freeze.txt"
    case $(hostname) in
        qjh003|qjh005)
            # Fix the documented Hopper cuBLASLt SIGFPE without changing PyTorch/vLLM.
            uv pip install --python "$EXP_ROOT/envs/epd/bin/python" --index-url "$INDEX" --no-deps nvidia-cublas-cu12==12.4.5.8 ;;
    esac
    "$EXP_ROOT/envs/epd/bin/python" "$SCRIPT_DIR/apply_epd_compat.py" "$EXP_ROOT"
    bash "$SCRIPT_DIR/build_epd_cuda.sh"
    python3 "$SCRIPT_DIR/download_model.py" OpenBMB/MiniCPM-V-2_6 "$EXP_ROOT/models/MiniCPM-V-2_6" \
        --manifest "$SCRIPT_DIR/../configs/minicpm-model-manifest.json"
else
    exit 2
fi
if [[ "$(realpath "$SCRIPT_DIR")" != "$(realpath "$EXP_ROOT/scripts")" ]]; then
    find "$SCRIPT_DIR" -maxdepth 1 -type f -exec cp {} "$EXP_ROOT/scripts/" \;
fi
if [[ -f "$SCRIPT_DIR/../data/dataset.tar.gz" ]]; then
    tar -xzf "$SCRIPT_DIR/../data/dataset.tar.gz" -C "$EXP_ROOT"
fi
