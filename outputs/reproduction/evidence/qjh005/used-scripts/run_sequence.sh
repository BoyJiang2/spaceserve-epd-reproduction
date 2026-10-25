#!/usr/bin/env bash
# Continue an already-running matrix with the remaining same-GPU comparisons.
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/env.sh"
TRACK=${1:?epd-followup, space-followup, or l20-followup}
WAIT_PID=${2:?Existing matrix PID}
CURRENT_SERVERS=${3:?Comma-separated current server PIDs}

while [[ -r /proc/$WAIT_PID/stat ]]; do
    STATE=$(cut -d ' ' -f 3 /proc/$WAIT_PID/stat)
    [[ "$STATE" != Z ]] || break
    sleep 10
done

if [[ "$TRACK" == epd-followup ]]; then
    PYTHON="$EXP_ROOT/envs/epd/bin/python"
    PREVIOUS=epd-l20
else
    PYTHON="$EXP_ROOT/envs/space/bin/python"
    if [[ "$TRACK" == space-followup ]]; then PREVIOUS=baseline-space-4090-mps; else PREVIOUS=baseline-space-l20-mps; fi
    export REPRO_USE_MPS=1
fi
[[ -f "$EXP_ROOT/results/formal/$PREVIOUS/COMPLETED" ]] || { echo "Previous matrix did not complete" >&2; exit 1; }
IFS=, read -ra SERVERS <<<"$CURRENT_SERVERS"
for PID in "${SERVERS[@]}"; do "$PYTHON" "$SCRIPT_DIR/stop_server.py" "$EXP_ROOT" "$PID"; done

start() {
    local ROLE=$1 GPU=$2 PORT=$3
    env EXP_ROOT="$EXP_ROOT" REPRO_USE_MPS="${REPRO_USE_MPS:-0}" \
        bash "$SCRIPT_DIR/start_server.sh" "$ROLE" "$GPU" "$PORT" >"$EXP_ROOT/logs/sequence-$ROLE-$PORT.log" 2>&1 &
    STARTED_PID=$!
    echo "started $ROLE gpu=$GPU port=$PORT pid=$STARTED_PID"
    echo "$STARTED_PID" >"$EXP_ROOT/results/server-$PORT.pid"
    local READY=0
    for ((ATTEMPT=0; ATTEMPT<180; ATTEMPT++)); do
        kill -0 "$STARTED_PID" 2>/dev/null || { echo "server exited during startup" >&2; return 1; }
        if curl -fsS --max-time 1 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then READY=1; break; fi
        sleep 1
    done
    [[ "$READY" == 1 ]] || { echo "server readiness timed out" >&2; return 1; }
}

if [[ "$TRACK" == epd-followup ]]; then
    PIDS=()
    URLS=()
    for GPU in 0 1 2; do
        PORT=$((18100 + GPU))
        start baseline-epd "$GPU" "$PORT"
        PIDS+=("$STARTED_PID")
        URLS+=("http://127.0.0.1:$PORT")
    done
    PID_LIST=$(IFS=,; echo "${PIDS[*]}")
    bash "$SCRIPT_DIR/run_matrix.sh" baseline-epd-l20 0,1,2 "$PID_LIST" "${URLS[@]}"
    for PID in "${PIDS[@]}"; do "$PYTHON" "$SCRIPT_DIR/stop_server.py" "$EXP_ROOT" "$PID"; done
elif [[ "$TRACK" == space-followup ]]; then
    start space 3 17778
    bash "$SCRIPT_DIR/run_matrix.sh" space-4090-mps 3 "$STARTED_PID" http://127.0.0.1:17778
    "$PYTHON" "$SCRIPT_DIR/stop_server.py" "$EXP_ROOT" "$STARTED_PID"
elif [[ "$TRACK" == l20-followup ]]; then
    for ROLE in space space-mask; do
        start "$ROLE" 6 17778
        VALIDATION_ONLY=1 bash "$SCRIPT_DIR/run_matrix.sh" "$ROLE-l20-mps" 6 "$STARTED_PID" http://127.0.0.1:17778
        "$PYTHON" "$SCRIPT_DIR/stop_server.py" "$EXP_ROOT" "$STARTED_PID"
    done
else
    exit 2
fi
date -u +%FT%TZ >"$EXP_ROOT/results/$TRACK-COMPLETED"
