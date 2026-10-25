#!/usr/bin/env bash
set -euo pipefail
p=/mnt/data3/boyjiang-spaceserve-epd
export EXP_ROOT=$p
while [[ -r /proc/2779115/stat ]] && [[ $(cut -d ' ' -f 3 /proc/2779115/stat) != Z ]]; do sleep 2; done
[[ -z $(nvidia-smi --id=2 --query-compute-apps=pid --format=csv,noheader) ]]
bash "$p/scripts/start_server.sh" baseline-epd 2 18102 >"$p/logs/server-baseline-gpu2-control.log" 2>&1 &
server=$!
trap '"$p/envs/epd/bin/python" "$p/scripts/stop_server.py" "$p" "$server"' EXIT
ready=0
for ((attempt=0; attempt<180; attempt++)); do
    kill -0 "$server"
    if curl -fsS --max-time 1 http://127.0.0.1:18102/health >/dev/null 2>&1; then ready=1; break; fi
    sleep 1
done
[[ "$ready" == 1 ]]
source "$p/scripts/env.sh"
"$p/envs/epd/bin/python" "$p/scripts/benchmark.py" --urls http://127.0.0.1:18102 \
    --model "$p/models/MiniCPM-V-2_6" --dataset "$p/dataset" --output "$p/results/epd-gpu2-baseline-control" \
    --images 1 --concurrency 1 --tokens 128 --warmup 1 --requests 2 --repetitions 1
