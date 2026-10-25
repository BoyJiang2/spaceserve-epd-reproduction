#!/usr/bin/env bash
set -euo pipefail
export EXP_ROOT=/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023
[[ $(hostname) == qjh000 && -f "$EXP_ROOT/evidence/G2_FORMAL_APPROVED" && -f "$EXP_ROOT/evidence/G3_MODEL_APPROVED" ]]
if [[ ${REPRO_HOST_LOCK_HELD:-0} != 1 ]]; then
    exec /var/tmp/boyjiang-spaceserve-epd-qjh000-20261023/envs/manage/bin/python "$EXP_ROOT/scripts/gpu_exclusive.py" space bash "$0" "$@"
fi
export REPRO_USE_MPS=1 CUDA_MPS_ACTIVE_THREAD_PERCENTAGE=100
source "$EXP_ROOT/scripts/env.sh"
unset VLLM_TORCH_PROFILER_DIR REPRO_OBSERVE VLLM_LIBSMCTRL_PATH REPRO_SM_PROBE
export REPRO_RUN_ID="$EXP_ROOT:formal:$(date +%s%N):$$"
PY="$EXP_ROOT/envs/space/bin/python"
OUT="$EXP_ROOT/results/formal"
[[ ! -e "$OUT" && -f "$EXP_ROOT/evidence/environment-READY" ]]
cmp /proc/sys/kernel/random/boot_id "$EXP_ROOT/evidence/boot-id.txt"
sha256sum -c "$EXP_ROOT/evidence/formal-approved-code.sha256" >"$EXP_ROOT/evidence/formal-code-check.txt"
# Includes orphaned preparer/download/trace children after their parent has exited.
"$PY" "$EXP_ROOT/scripts/check_background.py" >"$EXP_ROOT/evidence/formal-background-check.txt"
mkdir -p "$OUT/used-scripts"
cp "$EXP_ROOT/scripts/"*.py "$EXP_ROOT/scripts/"*.sh "$OUT/used-scripts/"
API_PID=""; MONITOR=""; OWN_MPS=0
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
if [[ -f "$EXP_ROOT/evidence/SM_EFFECTIVE" ]]; then ROLES+=(space-mask); fi
mkdir -p "$OUT/points"
printf '%s\n' "${ROLES[@]}" >"$OUT/points/roles.txt"
for PHASE in points rest; do
    if [[ "$PHASE" == points ]]; then CASES=(1:1 4:8); else CASES=(1:4 1:8 4:1 4:4); fi
    for ROLE in "${ROLES[@]}"; do
        DEST="$OUT/$PHASE/$ROLE"
        mkdir -p "$DEST"
        export REPRO_SPACE_RUN_LABEL="formal-$PHASE-$ROLE"
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
        "$PY" "$EXP_ROOT/scripts/capture_runtime.py" "$DEST/runtime.json" --server-pids "$API_PID" --devices 0 --note 'Formal 7B single-H20 run; profiler disabled'
        bash "$EXP_ROOT/scripts/mps_control.sh" status >"$DEST/mps-clients-before.txt"
        "$PY" "$EXP_ROOT/scripts/capture_mps_clients.py" --api-pid "$API_PID" --output "$DEST/mps-identity.json"
        for CASE in "${CASES[@]}"; do
            IMAGES=${CASE%:*}; CONCURRENCY=${CASE#*:}
            CASE_DIR="$DEST/images$IMAGES-c$CONCURRENCY"
            mkdir -p "$CASE_DIR"
            "$PY" "$EXP_ROOT/scripts/check_rgb_cache.py" --dataset "$EXP_ROOT/dataset" --urls http://127.0.0.1:19770 --output "$CASE_DIR/rgb-before.json"
            "$PY" "$EXP_ROOT/scripts/capture_mps_clients.py" --api-pid "$API_PID" --output "$CASE_DIR/mps-before.json"
            "$PY" -u "$EXP_ROOT/scripts/monitor_gpu.py" --devices 0 --server-pids "$API_PID" >"$CASE_DIR/gpu-memory.jsonl" &
            MONITOR=$!
            "$PY" -u "$EXP_ROOT/scripts/benchmark.py" --urls http://127.0.0.1:19770 --model "$EXP_ROOT/models/Qwen2-VL-7B-Instruct" --dataset "$EXP_ROOT/dataset" \
                --output "$CASE_DIR/measurement" --images "$IMAGES" --concurrency "$CONCURRENCY" --tokens 128 --warmup 20 --requests 100 --repetitions 3 >"$CASE_DIR/benchmark.log" 2>&1
            kill -TERM "$MONITOR" || true; wait "$MONITOR" || true; MONITOR=""
            "$PY" "$EXP_ROOT/scripts/check_rgb_cache.py" --dataset "$EXP_ROOT/dataset" --urls http://127.0.0.1:19770 --output "$CASE_DIR/rgb-after.json"
            "$PY" "$EXP_ROOT/scripts/capture_mps_clients.py" --api-pid "$API_PID" --output "$CASE_DIR/mps-after.json"
            "$PY" "$EXP_ROOT/scripts/audit_formal_case.py" "$CASE_DIR" >"$CASE_DIR/technical-audit.log"
            date -u +%FT%TZ >"$CASE_DIR/COMPLETED"
        done
        bash "$EXP_ROOT/scripts/mps_control.sh" status >"$DEST/mps-clients-after.txt"
        stop_api
        cp -a "$EXP_ROOT/results/runtime-devices/$REPRO_SPACE_RUN_LABEL" "$DEST/device-records"
        date -u +%FT%TZ >"$DEST/COMPLETED"
    done
    if [[ "$PHASE" == points ]]; then
        find "$OUT/points" -type f -print0 | sort -z | xargs -0 sha256sum >"$OUT/points.sha256"
        sha256sum "$OUT/points.sha256" >"$OUT/points-manifest.sha256"
        date -u +%FT%TZ >"$OUT/POINTS_READY_FOR_G4"
        echo 'Low/high points for all accepted groups complete; waiting for independent G4_POINTS_APPROVED.'
        until [[ -f "$OUT/G4_POINTS_APPROVED" ]]; do
            [[ ! -f "$OUT/STOP_AFTER_POINTS" ]] || exit 1
            sleep 5
        done
        "$PY" "$EXP_ROOT/scripts/verify_points.py" "$OUT" >"$OUT/points-code-check.txt"
        sha256sum -c "$EXP_ROOT/evidence/formal-approved-code.sha256" >"$OUT/formal-code-check-after-points.txt"
    fi
done
cleanup
nvidia-smi --query-compute-apps=pid,gpu_uuid --format=csv >"$OUT/gpu-processes-after.csv"
cmp /proc/sys/kernel/random/boot_id "$EXP_ROOT/evidence/boot-id.txt"
date -u +%FT%TZ >"$OUT/COMPLETED"
