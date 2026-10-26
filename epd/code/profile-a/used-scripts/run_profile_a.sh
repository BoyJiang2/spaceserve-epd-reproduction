#!/usr/bin/env bash
set -euo pipefail
export EXP_ROOT=${EXP_ROOT:?dedicated profiling root}
[[ "$EXP_ROOT" == /local/boyjiang/epd-profile-a-20261023 && $(hostname) == qjh003 ]]
source "$EXP_ROOT/scripts/env.sh"
PY="$EXP_ROOT/envs/epd/bin/python"
export REPRO_RUN_ID="$EXP_ROOT:$(date +%s%N):$$"
ACTION=${1:?pilot[-name] or formal}
[[ "$ACTION" =~ ^pilot(-[a-z0-9]+)*$ || "$ACTION" == formal ]]
[[ "$ACTION" != formal || -f "$EXP_ROOT/evidence/G3_APPROVED" ]]
OUT="$EXP_ROOT/results/$ACTION"
[[ ! -e "$OUT" ]]
mkdir -p "$OUT" "$OUT/used-scripts"
cp "$EXP_ROOT/scripts/"*.py "$EXP_ROOT/scripts/"*.sh "$OUT/used-scripts/"
cp "$EXP_ROOT/instrumentation.patch" "$OUT/"
cmp /proc/sys/kernel/random/boot_id "$EXP_ROOT/evidence/boot-id.txt"
[[ $("$PY" -c 'import importlib.metadata; print(importlib.metadata.version("nvidia-cublas-cu12"))') == 12.4.5.8 ]]
SERVERS=()
LAUNCHERS=()
MONITOR=""
cleanup() {
    if [[ -n "$MONITOR" ]]; then
        kill -TERM "$MONITOR" 2>/dev/null || true
        wait "$MONITOR" || true
        MONITOR=""
    fi
    for PID in "${SERVERS[@]}"; do
        "$PY" "$EXP_ROOT/scripts/stop_server.py" "$EXP_ROOT" "$PID" || echo "recorded API stop failed: $PID" >&2
    done
    for PID in "${LAUNCHERS[@]}"; do
        if kill -0 "$PID" 2>/dev/null; then
            # After stopping API workers, allow Nsight to finish writing its report.
            for ((WAIT=0; WAIT<120; WAIT++)); do
                kill -0 "$PID" 2>/dev/null || break
                sleep 1
            done
            if kill -0 "$PID" 2>/dev/null; then
                "$PY" "$EXP_ROOT/scripts/stop_server.py" "$EXP_ROOT" "$PID" || echo "launcher stop failed: $PID" >&2
            fi
        fi
        wait "$PID" || true
    done
    "$PY" "$EXP_ROOT/scripts/cleanup_owned.py" "$EXP_ROOT"
    SERVERS=()
    LAUNCHERS=()
}
trap cleanup EXIT
start() {
    local ROLE=$1 DEVICES=$2 PORT=$3 LABEL=$4 READY=0
    [[ -z $(nvidia-smi --id="$DEVICES" --query-compute-apps=pid --format=csv,noheader) ]]
    if [[ "$MODE" == on ]]; then
        setsid env NSYS_NVTX_PROFILER_REGISTER_ONLY=0 nsys profile --trace=cuda,nvtx \
            --sample=none --cpuctxsw=none --capture-range=nvtx --nvtx-capture=repro_capture \
            --capture-range-end=stop --wait=primary --output="$DEST/traces/$LABEL" \
            bash "$EXP_ROOT/scripts/start_server.sh" "$ROLE" "$DEVICES" "$PORT" >"$DEST/logs/$LABEL.log" 2>&1 &
    else
        setsid bash "$EXP_ROOT/scripts/start_server.sh" "$ROLE" "$DEVICES" "$PORT" >"$DEST/logs/$LABEL.log" 2>&1 &
    fi
    local LAUNCH=$!
    LAUNCHERS+=("$LAUNCH")
    for ((ATTEMPT=0; ATTEMPT<500; ATTEMPT++)); do
        kill -0 "$LAUNCH" || return 1
        if curl -fsS --max-time 1 "http://127.0.0.1:$PORT/repro/rgb-cache" >/dev/null 2>&1; then READY=1; break; fi
        sleep 1
    done
    [[ "$READY" == 1 ]]
    local SERVER
    SERVER=$("$PY" "$EXP_ROOT/scripts/control.py" status "http://127.0.0.1:$PORT" | "$PY" -c 'import json,sys; print(json.load(sys.stdin)[0]["pid"])')
    SERVERS+=("$SERVER")
}
for MODE in off on; do
    [[ "$ACTION" == formal || "$MODE" == on ]] || continue
    if [[ "$MODE" == on ]]; then export REPRO_OBSERVE=1; else unset REPRO_OBSERVE; fi
    for ROLE in epd baseline-epd; do
        for CASE in 1:1 4:8; do
            [[ "$ACTION" == formal || "$CASE" == 4:8 ]] || continue
            IMAGES=${CASE%:*}
            CONCURRENCY=${CASE#*:}
            DEST="$OUT/$MODE-$ROLE-images$IMAGES-c$CONCURRENCY"
            mkdir -p "$DEST/logs" "$DEST/traces"
            URLS=()
            if [[ "$ROLE" == epd ]]; then
                start epd 0,1,2 19510 epd
                URLS+=(http://127.0.0.1:19510)
            else
                for GPU in 0 1 2; do
                    PORT=$((19500+GPU))
                    start baseline-epd "$GPU" "$PORT" "baseline-$GPU"
                    URLS+=("http://127.0.0.1:$PORT")
                done
            fi
            "$PY" "$EXP_ROOT/scripts/check_rgb_cache.py" --dataset "$EXP_ROOT/dataset" --urls "${URLS[@]}" --output "$DEST/rgb-before.json"
            "$PY" "$EXP_ROOT/scripts/capture_h20_runtime.py" "$EXP_ROOT" --output "$DEST/runtime.json"
            if [[ "$ACTION" != formal ]]; then
                "$PY" "$EXP_ROOT/scripts/control.py" start "${URLS[@]}" >"$DEST/capture-start.json"
            fi
            INDEX=0
            for URL in "${URLS[@]}"; do
                for CHECK in standard c8; do
                    OPTIONS=()
                    if [[ "$CHECK" == c8 ]]; then OPTIONS+=(--concurrency8-only); fi
                    "$PY" "$EXP_ROOT/scripts/check_correctness.py" --url "$URL" --model "$EXP_ROOT/models/MiniCPM-V-2_6" \
                        --dataset "$EXP_ROOT/dataset" --reference-file "$EXP_ROOT/evidence/baseline-reference.json" \
                        --output "$DEST/correctness-$INDEX-$CHECK.json" "${OPTIONS[@]}" >"$DEST/logs/correctness-$INDEX-$CHECK.log" 2>&1
                done
                INDEX=$((INDEX+1))
            done
            if [[ "$ACTION" != formal ]]; then
                "$PY" "$EXP_ROOT/scripts/control.py" stop "${URLS[@]}" >"$DEST/capture-stop.json"
            else
                PID_LIST=$(IFS=,; echo "${SERVERS[*]}")
                "$PY" -u "$EXP_ROOT/scripts/monitor_gpu.py" --devices 0,1,2 --server-pids "$PID_LIST" >"$DEST/gpu-memory.jsonl" &
                MONITOR=$!
                OPTIONS=()
                if [[ "$MODE" == on ]]; then OPTIONS+=(--observe); fi
                "$PY" -u "$EXP_ROOT/scripts/benchmark.py" --urls "${URLS[@]}" --model "$EXP_ROOT/models/MiniCPM-V-2_6" \
                    --dataset "$EXP_ROOT/dataset" --output "$DEST/measurement" --images "$IMAGES" --concurrency "$CONCURRENCY" \
                    --tokens 128 --warmup 20 --requests 100 --repetitions 3 "${OPTIONS[@]}" >"$DEST/logs/benchmark.log" 2>&1
                kill -TERM "$MONITOR" || true
                wait "$MONITOR" || true
                MONITOR=""
            fi
            "$PY" "$EXP_ROOT/scripts/check_rgb_cache.py" --dataset "$EXP_ROOT/dataset" --urls "${URLS[@]}" --output "$DEST/rgb-after.json"
            cleanup
            [[ -z $(nvidia-smi --id=0,1,2 --query-compute-apps=pid --format=csv,noheader) ]]
            if [[ "$MODE" == on ]]; then
                COUNT=$(find "$DEST/traces" -maxdepth 1 -name '*.nsys-rep' | wc -l)
                [[ "$COUNT" == "${#URLS[@]}" ]]
                for TRACE in "$DEST/traces/"*.nsys-rep; do
                    nsys export --type sqlite --output="${TRACE%.nsys-rep}.sqlite" "$TRACE" >"${TRACE%.nsys-rep}.export.log" 2>&1
                done
            fi
            date -u +%FT%TZ >"$DEST/COMPLETED"
        done
    done
done
cmp /proc/sys/kernel/random/boot_id "$EXP_ROOT/evidence/boot-id.txt"
nvidia-smi --query-compute-apps=pid,gpu_uuid --format=csv >"$OUT/gpu-processes-after.csv"
date -u +%FT%TZ >"$OUT/COMPLETED"
