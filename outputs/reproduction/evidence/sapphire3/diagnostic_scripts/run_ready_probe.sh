#!/usr/bin/env bash
set -euo pipefail
p=/mnt/data3/boyjiang-spaceserve-epd
export EXP_ROOT=$p
"$p/envs/epd/bin/python" "$p/tmp/apply_epd_ready_probe.py" "$p"
server=0
cleanup() {
    if [[ "$server" != 0 ]]; then "$p/envs/epd/bin/python" "$p/scripts/stop_server.py" "$p" "$server" || true; fi
    cp "$p/tmp/api-before-ready-probe.py" "$p/src/epdserve/epdserve/api_server.py"
}
trap cleanup EXIT
source "$p/scripts/env.sh"
for epoch in 1 2; do
    [[ -z $(nvidia-smi --id=0,1,2 --query-compute-apps=pid --format=csv,noheader) ]]
    bash "$p/scripts/start_server.sh" epd 0,1,2 18404 >"$p/logs/server-epd-ready-epoch$epoch.log" 2>&1 &
    server=$!
    ready=0
    for ((attempt=0; attempt<240; attempt++)); do
        kill -0 "$server"
        if curl -fsS --max-time 1 http://127.0.0.1:18404/openapi.json >/dev/null 2>&1; then ready=1; break; fi
        sleep 1
    done
    [[ "$ready" == 1 ]]
    "$p/envs/epd/bin/python" "$p/scripts/check_correctness.py" \
        --url http://127.0.0.1:18404 --reference-file "$p/results/epd-correctness-fixed.json" \
        --model "$p/models/MiniCPM-V-2_6" --dataset "$p/dataset" \
        --output "$p/results/epd-ready-epoch$epoch-c8.json" --concurrency8-only
    "$p/envs/epd/bin/python" "$p/scripts/benchmark.py" --urls http://127.0.0.1:18404 \
        --model "$p/models/MiniCPM-V-2_6" --dataset "$p/dataset" --output "$p/results/epd-ready-epoch$epoch-c1" \
        --images 1 --concurrency 1 --tokens 128 --warmup 2 --requests 3 --repetitions 1
    "$p/envs/epd/bin/python" "$p/scripts/stop_server.py" "$p" "$server"
    server=0
done
date -u +%FT%TZ >"$p/results/epd-ready-probe-COMPLETED"
