#!/usr/bin/env bash
set -euo pipefail
export EXP_ROOT=${EXP_ROOT:?Set the existing dedicated H20 experiment root}
source "$EXP_ROOT/scripts/env.sh"
PYTHON="$EXP_ROOT/envs/epd/bin/python"
case $(hostname) in qjh003|qjh005) ;; *) exit 2 ;; esac
"$PYTHON" - "$EXP_ROOT" <<'PY'
import importlib.metadata, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
assert json.loads((root / 'evidence/epd-runtime.json').read_text())['boot_id'] == pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert importlib.metadata.version('nvidia-cublas-cu12') == '12.4.5.8'
PY
OUT="$EXP_ROOT/results/cache-fix-single-c1-20261023"
[[ ! -e "$OUT" ]]
mkdir -p "$OUT/logs" "$OUT/epd-h20" "$OUT/baseline-epd-h20"
mkdir "$OUT/used-scripts"
find "$EXP_ROOT/scripts" -maxdepth 1 -type f -exec cp {} "$OUT/used-scripts/" \;
git -C "$EXP_ROOT/src/epdserve" diff -- epdserve/api_server.py epdserve/llm_async.py >"$OUT/epd-compat.patch"
cp /proc/sys/kernel/random/boot_id "$OUT/boot-id.txt"
export REPRO_MATRIX_ROOT="$OUT" LOW_LOAD_ONLY=1
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
    bash "$EXP_ROOT/scripts/start_server.sh" "$ROLE" "$DEVICES" "$PORT" >"$OUT/logs/$LABEL.log" 2>&1 &
    SERVER_PID=$!
    SERVERS+=("$SERVER_PID")
    for ((ATTEMPT=0; ATTEMPT<400; ATTEMPT++)); do
        kill -0 "$SERVER_PID" || return 1
        if curl -fsS --max-time 1 "http://127.0.0.1:$PORT/repro/rgb-cache" >/dev/null 2>&1; then READY=1; break; fi
        sleep 1
    done
    [[ "$READY" == 1 ]]
}
check_cache() {
    "$PYTHON" "$EXP_ROOT/scripts/check_rgb_cache.py" --dataset "$EXP_ROOT/dataset" \
        --output "$OUT/$ROLE/rgb-$1.json" --urls "${URLS[@]}"
}
for ROLE in epd-h20 baseline-epd-h20; do
    URLS=()
    if [[ "$ROLE" == epd-h20 ]]; then
        start epd 0,1,2 18510 epd
        URLS+=(http://127.0.0.1:18510)
    else
        for GPU in 0 1 2; do
            PORT=$((18500 + GPU))
            start baseline-epd "$GPU" "$PORT" "baseline-$GPU"
            URLS+=("http://127.0.0.1:$PORT")
        done
    fi
    check_cache before
    for CHECK in standard c8; do
        OPTIONS=()
        if [[ "$CHECK" == c8 ]]; then OPTIONS+=(--concurrency8-only); fi
        "$PYTHON" "$EXP_ROOT/scripts/check_correctness.py" --url "${URLS[0]}" \
            --model "$EXP_ROOT/models/MiniCPM-V-2_6" --dataset "$EXP_ROOT/dataset" \
            --reference-file "$EXP_ROOT/evidence/baseline-reference.json" \
            --output "$OUT/$ROLE/correctness-$CHECK.json" "${OPTIONS[@]}"
    done
    "$PYTHON" "$EXP_ROOT/scripts/capture_h20_runtime.py" "$EXP_ROOT" --output "$OUT/$ROLE/h20-runtime.json"
    PID_LIST=$(IFS=,; echo "${SERVERS[*]}")
    bash "$EXP_ROOT/scripts/run_matrix.sh" "$ROLE" 0,1,2 "$PID_LIST" "${URLS[@]}"
    check_cache after
    cleanup
    SERVERS=()
done
cmp /proc/sys/kernel/random/boot_id "$OUT/boot-id.txt"
[[ -z $(nvidia-smi --id=0,1,2 --query-compute-apps=pid --format=csv,noheader) ]]
nvidia-smi --id=0,1,2 --query-compute-apps=gpu_uuid,pid --format=csv >"$OUT/gpu-processes-after.csv"
date -u +%FT%TZ >"$OUT/COMPLETED"
