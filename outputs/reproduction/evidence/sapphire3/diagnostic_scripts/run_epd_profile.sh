#!/usr/bin/env bash
set -euo pipefail
p=/mnt/data3/boyjiang-spaceserve-epd
export EXP_ROOT=$p EPD_REPRO_PROFILE_DIR=$p/results/epd-restart-profile
apps=$(nvidia-smi --id=0,1,2 --query-compute-apps=pid --format=csv,noheader)
[[ -z "$apps" ]]
"$p/envs/epd/bin/python" "$p/tmp/apply_epd_profile_probe.py" "$p"
bash "$p/scripts/start_server.sh" epd 0,1,2 18401 >"$p/logs/server-epd-profile-restart.log" 2>&1 &
server=$!
cleanup() {
    "$p/envs/epd/bin/python" "$p/scripts/stop_server.py" "$p" "$server" || true
    cp "$p/tmp/worker-before-profile.py" "$p/src/epdserve/epdserve/worker.py"
}
trap cleanup EXIT
ready=0
for ((attempt=0; attempt<240; attempt++)); do
    kill -0 "$server"
    if curl -fsS --max-time 1 http://127.0.0.1:18401/openapi.json >/dev/null 2>&1; then ready=1; break; fi
    sleep 1
done
[[ "$ready" == 1 ]]
source "$p/scripts/env.sh"
"$p/envs/epd/bin/python" "$p/scripts/benchmark.py" --urls http://127.0.0.1:18401 \
    --model "$p/models/MiniCPM-V-2_6" --dataset "$p/dataset" \
    --output "$p/results/epd-profile-request" --images 1 --concurrency 1 --tokens 8 \
    --warmup 0 --requests 1 --repetitions 1
