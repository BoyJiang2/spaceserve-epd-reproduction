#!/usr/bin/env bash
set -euo pipefail
export EXP_ROOT=${EXP_ROOT:?Set the dedicated H20 experiment directory}
source "$EXP_ROOT/scripts/env.sh"
PYTHON="$EXP_ROOT/envs/epd/bin/python"
PREFLIGHT=${1:?Path to the successful preflight directory}
case $(hostname) in
    qjh003) export VALIDATION_ONLY=0 ;;
    qjh005) export VALIDATION_ONLY=1 ;;
    *) echo "Unexpected H20 experiment host" >&2; exit 2 ;;
esac
[[ -f "$PREFLIGHT/PASSED" ]]
AUDIT_OPTIONS=()
if [[ "$VALIDATION_ONLY" == 1 ]]; then AUDIT_OPTIONS+=(--validation-only); fi
"$PYTHON" - "$PREFLIGHT/platform.json" <<'PY'
import json, pathlib, sys
record = json.loads(pathlib.Path(sys.argv[1]).read_text())
assert record['boot_id'] == pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()
PY
"$PYTHON" - "$EXP_ROOT/evidence" <<'PY'
import importlib.metadata, json, pathlib, sys
evidence = pathlib.Path(sys.argv[1])
assert importlib.metadata.version('nvidia-cublas-cu12') == '12.4.5.8'
embedding = json.loads((evidence / 'embedding-ipc.json').read_text())
assert embedding['source_validated'] and len(embedding['records']) == 3 and all(record['data_equal'] for record in embedding['records'])
blas = [json.loads(line) for line in (evidence / 'blas-after.jsonl').read_text().splitlines()]
assert blas[0]['cublas'] == '12.4.5.8' and sum(item.get('data_equal', False) for item in blas) == 4
PY
[[ ! -e "$EXP_ROOT/results/formal/epd-h20" && ! -e "$EXP_ROOT/results/formal/baseline-epd-h20" ]]
SERVERS=()
cleanup() {
    for PID in "${SERVERS[@]}"; do
        "$PYTHON" "$EXP_ROOT/scripts/stop_server.py" "$EXP_ROOT" "$PID" || true
    done
}
trap cleanup EXIT
start() {
    local ROLE=$1 DEVICES=$2 PORT=$3 LABEL=$4 READY=0
    [[ -z $(nvidia-smi --id="$DEVICES" --query-compute-apps=pid --format=csv,noheader) ]]
    bash "$EXP_ROOT/scripts/start_server.sh" "$ROLE" "$DEVICES" "$PORT" >"$EXP_ROOT/logs/$LABEL.log" 2>&1 &
    SERVER_PID=$!
    SERVERS+=("$SERVER_PID")
    echo "$SERVER_PID" >"$EXP_ROOT/results/server-$PORT.pid"
    echo "started $LABEL pid=$SERVER_PID devices=$DEVICES"
    for ((ATTEMPT=0; ATTEMPT<400; ATTEMPT++)); do
        kill -0 "$SERVER_PID" || return 1
        if [[ "$ROLE" == epd ]]; then ROUTE=openapi.json; else ROUTE=health; fi
        if curl -fsS --max-time 1 "http://127.0.0.1:$PORT/$ROUTE" >/dev/null 2>&1; then READY=1; break; fi
        sleep 1
    done
    [[ "$READY" == 1 ]]
}
stop_all() {
    cleanup
    SERVERS=()
}
correctness() {
    local PORT=$1 LABEL=$2
    shift 2
    "$PYTHON" "$EXP_ROOT/scripts/check_correctness.py" \
        --url "http://127.0.0.1:$PORT" --model "$EXP_ROOT/models/MiniCPM-V-2_6" \
        --dataset "$EXP_ROOT/dataset" --output "$EXP_ROOT/evidence/$LABEL.json" "$@"
}
start baseline-epd 0 18500 baseline-reference
correctness 18500 baseline-reference --reference http://127.0.0.1:18500
correctness 18500 baseline-reference-c8 --reference-file "$EXP_ROOT/evidence/baseline-reference.json" --concurrency8-only
stop_all
for EPOCH in 1 2; do
    start epd 0,1,2 18510 "epd-epoch$EPOCH"
    correctness 18510 "epd-epoch$EPOCH-c8" --reference-file "$EXP_ROOT/evidence/baseline-reference.json" --concurrency8-only
    correctness 18510 "epd-epoch$EPOCH" --reference-file "$EXP_ROOT/evidence/baseline-reference.json"
    if [[ "$EPOCH" == 2 ]]; then
        "$PYTHON" "$EXP_ROOT/scripts/check_rgb_cache.py" --urls http://127.0.0.1:18510 --dataset "$EXP_ROOT/dataset" --output "$EXP_ROOT/evidence/epd-rgb-before.json"
        "$PYTHON" "$EXP_ROOT/scripts/capture_h20_runtime.py" "$EXP_ROOT" --output "$EXP_ROOT/evidence/epd-runtime.json"
        bash "$EXP_ROOT/scripts/run_matrix.sh" epd-h20 0,1,2 "$SERVER_PID" http://127.0.0.1:18510
        "$PYTHON" "$EXP_ROOT/scripts/check_rgb_cache.py" --urls http://127.0.0.1:18510 --dataset "$EXP_ROOT/dataset" --output "$EXP_ROOT/evidence/epd-rgb-after.json"
        "$PYTHON" "$EXP_ROOT/scripts/audit_matrix.py" "$EXP_ROOT/results/formal/epd-h20" "${AUDIT_OPTIONS[@]}"
    fi
    stop_all
done
URLS=()
for GPU in 0 1 2; do
    PORT=$((18500 + GPU))
    start baseline-epd "$GPU" "$PORT" "baseline-replica$GPU"
    URLS+=("http://127.0.0.1:$PORT")
done
PID_LIST=$(IFS=,; echo "${SERVERS[*]}")
"$PYTHON" "$EXP_ROOT/scripts/check_rgb_cache.py" --urls "${URLS[@]}" --dataset "$EXP_ROOT/dataset" --output "$EXP_ROOT/evidence/baseline-rgb-before.json"
"$PYTHON" "$EXP_ROOT/scripts/capture_h20_runtime.py" "$EXP_ROOT" --output "$EXP_ROOT/evidence/baseline-runtime.json"
bash "$EXP_ROOT/scripts/run_matrix.sh" baseline-epd-h20 0,1,2 "$PID_LIST" "${URLS[@]}"
"$PYTHON" "$EXP_ROOT/scripts/check_rgb_cache.py" --urls "${URLS[@]}" --dataset "$EXP_ROOT/dataset" --output "$EXP_ROOT/evidence/baseline-rgb-after.json"
"$PYTHON" "$EXP_ROOT/scripts/audit_matrix.py" "$EXP_ROOT/results/formal/baseline-epd-h20" "${AUDIT_OPTIONS[@]}"
stop_all
bash "$EXP_ROOT/scripts/postflight_epd_h20.sh"
"$PYTHON" - "$PREFLIGHT/platform.json" <<'PY'
import json, pathlib, sys
assert json.loads(pathlib.Path(sys.argv[1]).read_text())['boot_id'] == pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()
PY
date -u +%FT%TZ >"$EXP_ROOT/results/$(hostname)-matrices-COMPLETED"
