#!/usr/bin/env bash
set -euo pipefail
p=/mnt/data3/boyjiang-spaceserve-epd
export EXP_ROOT=$p
[[ -z $(nvidia-smi --id=0,1,2 --query-compute-apps=pid --format=csv,noheader) ]]
"$p/envs/epd/bin/python" "$p/tmp/add_rpc_diag.py" "$p"
bash "$p/scripts/start_server.sh" epd 0,1,2 18403 >"$p/logs/server-epd-rpc-diag.log" 2>&1 &
server=$!
cleanup() {
    "$p/envs/epd/bin/python" "$p/scripts/stop_server.py" "$p" "$server" || true
    cp "$p/tmp/api-before-rpc-diag.py" "$p/src/epdserve/epdserve/api_server.py"
}
trap cleanup EXIT
ready=0
for ((attempt=0; attempt<240; attempt++)); do
    kill -0 "$server"
    if curl -fsS --max-time 1 http://127.0.0.1:18403/openapi.json >/dev/null 2>&1; then ready=1; break; fi
    sleep 1
done
[[ "$ready" == 1 ]]
curl -fsS --max-time 30 http://127.0.0.1:18403/repro/worker-times >"$p/results/epd-rpc-before.json"
source "$p/scripts/env.sh"
"$p/envs/epd/bin/python" "$p/scripts/benchmark.py" --urls http://127.0.0.1:18403 \
    --model "$p/models/MiniCPM-V-2_6" --dataset "$p/dataset" --output "$p/results/epd-rpc-split-request" \
    --images 1 --concurrency 1 --tokens 128 --warmup 0 --requests 1 --repetitions 1
curl -fsS --max-time 30 http://127.0.0.1:18403/repro/worker-times >"$p/results/epd-rpc-after.json"
