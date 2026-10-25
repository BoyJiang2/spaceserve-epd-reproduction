#!/usr/bin/env bash
set -euo pipefail
export EXP_ROOT=/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023
[[ $(hostname) == qjh000 && -f "$EXP_ROOT/evidence/G2_MODEL_APPROVED" ]]
if [[ ${REPRO_HOST_LOCK_HELD:-0} != 1 ]]; then
    exec /var/tmp/boyjiang-spaceserve-epd-qjh000-20261023/envs/manage/bin/python "$EXP_ROOT/scripts/gpu_exclusive.py" space bash "$0" "$@"
fi
TRIAL=${1:?cold or restart}
[[ "$TRIAL" == cold || "$TRIAL" == restart ]]
export REPRO_USE_MPS=1 CUDA_MPS_ACTIVE_THREAD_PERCENTAGE=100
export REPRO_SM_PROBE=1
source "$EXP_ROOT/scripts/env.sh"
export REPRO_RUN_ID="$EXP_ROOT:preflight:$TRIAL:$(date +%s%N):$$"
PY="$EXP_ROOT/envs/space/bin/python"
OUT="$EXP_ROOT/results/preflight-$TRIAL"
[[ ! -e "$OUT" && -f "$EXP_ROOT/evidence/environment-READY" ]]
mkdir -p "$OUT/used-scripts"
cp "$EXP_ROOT/scripts/"*.py "$EXP_ROOT/scripts/"*.sh "$OUT/used-scripts/"
API_PID=""
MONITOR=""
OWN_MPS=0
stop_api() {
    if [[ -n "$MONITOR" ]]; then kill -TERM "$MONITOR" 2>/dev/null || true; wait "$MONITOR" || true; MONITOR=""; fi
    if [[ -n "$API_PID" ]]; then "$PY" "$EXP_ROOT/scripts/stop_server.py" "$EXP_ROOT" "$API_PID" || echo "API stop failed: $API_PID" >&2; API_PID=""; fi
    "$PY" "$EXP_ROOT/scripts/cleanup_owned.py" "$EXP_ROOT"
}
cleanup() {
    local FAILED=0
    stop_api || FAILED=1
    if [[ "$OWN_MPS" == 1 ]]; then
        if bash "$EXP_ROOT/scripts/mps_control.sh" stop; then OWN_MPS=0; else FAILED=1; fi
    fi
    return "$FAILED"
}
trap cleanup EXIT
trap 'exit 143' TERM INT
"$EXP_ROOT/envs/manage/bin/python" "$EXP_ROOT/scripts/prune_stopped_mps.py"
env -u REPRO_RUN_ID bash "$EXP_ROOT/scripts/mps_control.sh" start 0 >"$OUT/mps-start.json"
OWN_MPS=1
ROLES=(baseline-space space)
if [[ -f "$EXP_ROOT/evidence/SM_NATIVE_APPROVED" ]]; then ROLES+=(space-mask); fi
for ROLE in "${ROLES[@]}"; do
    DEST="$OUT/$ROLE"
    mkdir -p "$DEST/traces"
    export REPRO_SPACE_RUN_LABEL="preflight-$TRIAL-$ROLE"
    export VLLM_TORCH_PROFILER_DIR="$DEST/traces"
    "$PY" "$EXP_ROOT/scripts/capture_mps_clients.py" --output "$DEST/mps-idle.json"
    setsid bash "$EXP_ROOT/scripts/start_server.sh" "$ROLE" 0 19770 >"$DEST/server.log" 2>&1 &
    API_PID=$!
    READY=0
    for ((ATTEMPT=0; ATTEMPT<500; ATTEMPT++)); do
        kill -0 "$API_PID" || exit 1
        if curl -fsS --max-time 1 http://127.0.0.1:19770/health >/dev/null 2>&1; then READY=1; break; fi
        sleep 1
    done
    [[ "$READY" == 1 ]]
    "$PY" "$EXP_ROOT/scripts/check_rgb_cache.py" --dataset "$EXP_ROOT/dataset" --urls http://127.0.0.1:19770 --output "$DEST/rgb-before.json"
    REFERENCE="$EXP_ROOT/evidence/7b-native-reference.json"
    if [[ "$TRIAL:$ROLE" == cold:baseline-space ]]; then OPTIONS=(--reference http://127.0.0.1:19770); else OPTIONS=(--reference-file "$REFERENCE"); fi
    "$PY" "$EXP_ROOT/scripts/check_correctness.py" --url http://127.0.0.1:19770 --model "$EXP_ROOT/models/Qwen2-VL-7B-Instruct" --dataset "$EXP_ROOT/dataset" "${OPTIONS[@]}" --output "$DEST/correctness-standard.json" >"$DEST/correctness-standard.log" 2>&1
    if [[ "$TRIAL:$ROLE" == cold:baseline-space ]]; then [[ ! -e "$REFERENCE" ]]; cp "$DEST/correctness-standard.json" "$REFERENCE"; fi
    "$PY" "$EXP_ROOT/scripts/check_correctness.py" --url http://127.0.0.1:19770 --model "$EXP_ROOT/models/Qwen2-VL-7B-Instruct" --dataset "$EXP_ROOT/dataset" --reference-file "$REFERENCE" --concurrency8-only --output "$DEST/correctness-c8.json" >"$DEST/correctness-c8.log" 2>&1
    "$PY" "$EXP_ROOT/scripts/capture_runtime.py" "$DEST/runtime.json" --server-pids "$API_PID" --devices 0 --note "Captured before diagnostic profiling; fresh 7B service"
    bash "$EXP_ROOT/scripts/mps_control.sh" status >"$DEST/mps-clients-before.txt"
    "$PY" "$EXP_ROOT/scripts/capture_mps_clients.py" --api-pid "$API_PID" --output "$DEST/mps-identity-before.json"
    "$PY" -u "$EXP_ROOT/scripts/monitor_gpu.py" --devices 0 --server-pids "$API_PID" >"$DEST/gpu-memory.jsonl" &
    MONITOR=$!
    curl -fsS --max-time 60 -X POST http://127.0.0.1:19770/profile/start >"$DEST/profile-start.json"
    "$PY" "$EXP_ROOT/scripts/benchmark.py" --urls http://127.0.0.1:19770 --model "$EXP_ROOT/models/Qwen2-VL-7B-Instruct" --dataset "$EXP_ROOT/dataset" --output "$DEST/profile-requests" --images 4 --concurrency 8 --tokens 128 --warmup 20 --requests 16 --repetitions 1 >"$DEST/profile-requests.log" 2>&1
    curl -fsS --max-time 300 -X POST http://127.0.0.1:19770/profile/stop >"$DEST/profile-stop.json"
    WORKERS=2
    if [[ "$ROLE" == baseline-space ]]; then WORKERS=1; fi
    "$PY" "$EXP_ROOT/scripts/wait_for_traces.py" --directory "$DEST/traces" \
        --device-records "$EXP_ROOT/results/runtime-devices/$REPRO_SPACE_RUN_LABEL" \
        --workers "$WORKERS" --output "$DEST/profile-export-complete.json"
    bash "$EXP_ROOT/scripts/mps_control.sh" status >"$DEST/mps-clients-after.txt"
    "$PY" "$EXP_ROOT/scripts/capture_mps_clients.py" --api-pid "$API_PID" --output "$DEST/mps-identity-after.json"
    "$PY" "$EXP_ROOT/scripts/check_rgb_cache.py" --dataset "$EXP_ROOT/dataset" --urls http://127.0.0.1:19770 --output "$DEST/rgb-after.json"
    stop_api
    if [[ "$ROLE" == space || "$ROLE" == space-mask ]]; then
        "$PY" "$EXP_ROOT/scripts/analyze_trace.py" "$DEST/traces" --server-log "$DEST/server.log" --output "$DEST/overlap.json"
    fi
    date -u +%FT%TZ >"$DEST/COMPLETED"
done
cleanup
nvidia-smi --id=0 --query-compute-apps=pid,gpu_uuid --format=csv >"$OUT/processes-after.csv"
date -u +%FT%TZ >"$OUT/COMPLETED"
