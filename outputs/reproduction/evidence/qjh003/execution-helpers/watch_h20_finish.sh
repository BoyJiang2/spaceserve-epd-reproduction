#!/usr/bin/env bash
set -euo pipefail
export EXP_ROOT=${1:?Experiment root}
WORKFLOW_PID=${2:?Verified live workflow PID}
while [[ -r /proc/$WORKFLOW_PID/stat ]] && [[ $(cut -d ' ' -f 3 /proc/$WORKFLOW_PID/stat) != Z ]]; do
    if [[ -f "$EXP_ROOT/results/formal/baseline-epd-h20/runtime-config.json" && ! -f "$EXP_ROOT/evidence/baseline-runtime.json" ]]; then
        "$EXP_ROOT/envs/epd/bin/python" "$EXP_ROOT/scripts/capture_h20_runtime.py" "$EXP_ROOT" --output "$EXP_ROOT/evidence/baseline-runtime.json"
    fi
    sleep 5
done
[[ -f "$EXP_ROOT/evidence/baseline-runtime.json" && -f "$EXP_ROOT/results/$(hostname)-matrices-COMPLETED" ]]
bash "$EXP_ROOT/scripts/postflight_epd_h20.sh"
date -u +%FT%TZ >"$EXP_ROOT/results/postflight-COMPLETED"
