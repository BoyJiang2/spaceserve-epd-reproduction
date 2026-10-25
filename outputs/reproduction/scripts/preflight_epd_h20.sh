#!/usr/bin/env bash
set -euo pipefail
export EXP_ROOT=${EXP_ROOT:?Set the dedicated qjh003 experiment directory}
source "$EXP_ROOT/scripts/env.sh"
PYTHON="$EXP_ROOT/envs/epd/bin/python"
DESTINATION="$EXP_ROOT/evidence/preflight-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir "$DESTINATION"
"$PYTHON" "$EXP_ROOT/scripts/check_iommu.py" --devices 0,1,2 \
    --output "$DESTINATION/platform.json" --require-compatible
"$PYTHON" "$EXP_ROOT/scripts/capture_environment.py" "$EXP_ROOT"
cp "$EXP_ROOT/results/environment.json" "$DESTINATION/environment.json"
SITE="$EXP_ROOT/envs/epd/lib/python3.10/site-packages"
export LD_LIBRARY_PATH="$SITE/torch/lib:$SITE/nvidia/nccl/lib:${LD_LIBRARY_PATH:-}"
"$PYTHON" "$EXP_ROOT/scripts/probe_h20_blas.py" --device 0 >"$DESTINATION/blas-after.jsonl"
"$PYTHON" "$EXP_ROOT/scripts/probe_epd_embedding_ipc.py" \
    --library "$EXP_ROOT/build/epd-cuda/libcuda_ipc_utils.so" --output "$DESTINATION/embedding-ipc.json"
cp "$DESTINATION/blas-after.jsonl" "$DESTINATION/embedding-ipc.json" "$EXP_ROOT/evidence/"
for PAIR in 0,1 1,0 0,2 2,0 1,2 2,1; do
    CUDA_VISIBLE_DEVICES="$PAIR" "$PYTHON" "$EXP_ROOT/scripts/probe_cuda_peer_runtime.py" \
        --bytes 16777216 --output "$DESTINATION/cuda-peer-$PAIR.json"
    for BLOCKS in 2048 24728; do
        "$PYTHON" "$EXP_ROOT/scripts/probe_epd_kv_ipc.py" \
            --source "${PAIR%,*}" --destination "${PAIR#*,}" \
            --library "$EXP_ROOT/build/epd-cuda/libcuda_ipc_utils.so" \
            --cache-blocks "$BLOCKS" --transfer-blocks 18 --repetitions 3 \
            --output "$DESTINATION/kv-$PAIR-blocks$BLOCKS.json"
    done
done
date -u +%FT%TZ >"$DESTINATION/PASSED"
echo "$DESTINATION"
