#!/usr/bin/env bash
set -euo pipefail
p=/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023
[[ $(hostname) == qjh000 ]]
[[ ! -f "$p/evidence/7b-native-reference.json" ]]
[[ $("$p/envs/manage/bin/python" -c 'import json,sys; print(json.load(open(sys.argv[1]))["state"])' "$p/evidence/mps-owner.json") == stopped ]]
[[ -z $(nvidia-smi --id=0 --query-compute-apps=pid --format=csv,noheader) ]]
[[ ! -e "$p/results/preflight-cold-failed-mps-parser-185629" ]]
[[ -d "$p/results/preflight-cold" && ! -f "$p/results/preflight-cold/COMPLETED" ]]
mv -- "$p/results/preflight-cold" "$p/results/preflight-cold-failed-mps-parser-185629"
mv -- "$p/logs/model-preflight-cold-launch.log" "$p/logs/model-preflight-cold-failed-mps-parser-185629.log"
sha256sum -c "$p/evidence/service-sm-binaries.sha256"
find "$p/scripts" -maxdepth 1 -type f \( -name '*.py' -o -name '*.sh' \) -print0 | sort -z | xargs -0 sha256sum >"$p/evidence/model-approved-code.sha256"
sha256sum "$p/source/SpaceServe/vllm/engine/core.py" "$p/source/SpaceServe/vllm/worker/gpu_worker.py" >>"$p/evidence/model-approved-code.sha256"
printf '%s\n' 'Model hooks/runner G2 APPROVE_WITH_NITS; MPS idle delta G2 APPROVE /root/profile_runner_review;0BLOCKING;cold/restart only' >"$p/evidence/G2_MODEL_APPROVED"
nohup bash "$p/scripts/preflight_model.sh" cold >"$p/logs/model-preflight-cold-launch.log" 2>&1 </dev/null &
pid=$!
printf '%s\n' "$pid" >"$p/evidence/model-preflight-cold-retry.pid"
printf 'cold_retry_pid=%s\n' "$pid"
