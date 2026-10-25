#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/env.sh"
ROLE=${1:?Role label}
DEVICES=${2:?Comma-separated physical GPU indices}
SERVER_PIDS=${3:?Comma-separated server PIDs}
shift 3
URLS=("$@")
[[ ${#URLS[@]} -gt 0 ]] || exit 2
if [[ "$ROLE" == *epd* ]]; then
    PYTHON="$EXP_ROOT/envs/epd/bin/python"
    MODEL="$EXP_ROOT/models/MiniCPM-V-2_6"
else
    PYTHON="$EXP_ROOT/envs/space/bin/python"
    MODEL="$EXP_ROOT/models/Qwen2-VL-2B-Instruct"
fi
DESTINATION="${REPRO_MATRIX_ROOT:-$EXP_ROOT/results/formal}/$ROLE"
mkdir -p "$DESTINATION"
[[ ! -e "$DESTINATION/gpu-memory.jsonl" ]] || { echo "Existing run; choose a new role label" >&2; exit 2; }
"$PYTHON" - "$EXP_ROOT" "$DESTINATION" "$DEVICES" "$SERVER_PIDS" <<'PY'
import datetime, hashlib, importlib.metadata, json, pathlib, subprocess, sys
import psutil
root, destination = map(pathlib.Path, sys.argv[1:3])
keys = ["CUDA_VISIBLE_DEVICES", "CUDA_MPS_PIPE_DIRECTORY", "VLLM_USE_V1", "PYTHONPATH", "VLLM_LIBSMCTRL_PATH", "REPRO_RGB_MANIFEST"]
servers = []
for pid in map(int, sys.argv[4].split(",")):
    process = psutil.Process(pid)
    environment = process.environ()
    servers.append({"pid": pid, "command": process.cmdline(), "environment": {key: environment.get(key) for key in keys}})
config = {"started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "devices": sys.argv[3],
          "servers": servers, "packages": {name: importlib.metadata.version(name) for name in ["vllm", "torch", "transformers"]},
          "gpu_memory_sampling_interval_s": 0.1}
(destination / "runtime-config.json").write_text(json.dumps(config, indent=2))
PY
"$PYTHON" -u "$SCRIPT_DIR/monitor_gpu.py" --devices "$DEVICES" --server-pids "$SERVER_PIDS" >"$DESTINATION/gpu-memory.jsonl" &
MONITOR_PID=$!
trap 'kill -TERM "$MONITOR_PID" 2>/dev/null || true; wait "$MONITOR_PID" 2>/dev/null || true' EXIT
for IMAGES in 1 4; do
    for CONCURRENCY in 1 4 8; do
        if [[ ${LOW_LOAD_ONLY:-0} == 1 ]]; then
            [[ "$IMAGES:$CONCURRENCY" == 1:1 ]] || continue
        fi
        if [[ ${VALIDATION_ONLY:-0} == 1 ]]; then
            [[ "$IMAGES:$CONCURRENCY" == 1:1 || "$IMAGES:$CONCURRENCY" == 4:8 ]] || continue
        fi
        "$PYTHON" -u "$SCRIPT_DIR/benchmark.py" --urls "${URLS[@]}" --model "$MODEL" \
            --dataset "$EXP_ROOT/dataset" --output "$DESTINATION/images${IMAGES}-c${CONCURRENCY}" \
            --images "$IMAGES" --concurrency "$CONCURRENCY" --tokens 128 --warmup 20 --requests 100 --repetitions 3
    done
done
date -u +%FT%TZ >"$DESTINATION/COMPLETED"
