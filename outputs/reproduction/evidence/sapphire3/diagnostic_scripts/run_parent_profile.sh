#!/usr/bin/env bash
set -euo pipefail
p=/mnt/data3/boyjiang-spaceserve-epd
export EXP_ROOT=$p
[[ -z $(nvidia-smi --id=0,1,2,3 --query-compute-apps=pid --format=csv,noheader) ]]
"$p/envs/epd/bin/python" "$p/tmp/profile_epd_parent.py" "$p"
bash "$p/scripts/start_server_parent_profile.sh" epd 0,1,2 18402 >"$p/logs/server-epd-parent-profile.log" 2>&1 &
epd_server=$!
bash "$p/scripts/start_server.sh" baseline-epd 3 18103 >"$p/logs/server-baseline-restart-control.log" 2>&1 &
baseline_server=$!
echo "$epd_server" >"$p/results/server-parent-profile.pid"
echo "$baseline_server" >"$p/results/server-restart-control.pid"
cleanup() {
    for server in "$epd_server" "$baseline_server"; do
        "$p/envs/epd/bin/python" "$p/scripts/stop_server.py" "$p" "$server" || true
    done
}
trap cleanup EXIT
for url in http://127.0.0.1:18402/openapi.json http://127.0.0.1:18103/health; do
    ready=0
    for ((attempt=0; attempt<240; attempt++)); do
        kill -0 "$epd_server"; kill -0 "$baseline_server"
        if curl -fsS --max-time 1 "$url" >/dev/null 2>&1; then ready=1; break; fi
        sleep 1
    done
    [[ "$ready" == 1 ]]
done
source "$p/scripts/env.sh"
"$p/envs/epd/bin/python" "$p/scripts/benchmark.py" --urls http://127.0.0.1:18103 \
    --model "$p/models/MiniCPM-V-2_6" --dataset "$p/dataset" --output "$p/results/epd-restart-baseline-control" \
    --images 1 --concurrency 1 --tokens 128 --warmup 2 --requests 2 --repetitions 1
"$p/envs/epd/bin/python" "$p/scripts/benchmark.py" --urls http://127.0.0.1:18402 \
    --model "$p/models/MiniCPM-V-2_6" --dataset "$p/dataset" --output "$p/results/epd-parent-profile-request" \
    --images 1 --concurrency 1 --tokens 128 --warmup 0 --requests 1 --repetitions 1
kill -INT "$epd_server"
for ((attempt=0; attempt<30; attempt++)); do
    [[ ! -s "$p/results/epd-parent-profile.pstats" ]] || break
    sleep 1
done
test -s "$p/results/epd-parent-profile.pstats"
