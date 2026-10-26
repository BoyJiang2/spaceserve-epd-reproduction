#!/usr/bin/env bash
set -euo pipefail
export EXP_ROOT=/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023
[[ $(hostname) == qjh000 && -f "$EXP_ROOT/evidence/G2_SM_APPROVED" && -f "$EXP_ROOT/evidence/environment-READY" ]]
if [[ ${REPRO_HOST_LOCK_HELD:-0} != 1 ]]; then
    exec "$EXP_ROOT/envs/manage/bin/python" "$EXP_ROOT/scripts/gpu_exclusive.py" space bash "$0"
fi
export REPRO_USE_MPS=0
unset CUDA_MPS_PIPE_DIRECTORY CUDA_MPS_LOG_DIRECTORY CUDA_MPS_ACTIVE_THREAD_PERCENTAGE PYTHONPATH
source "$EXP_ROOT/scripts/env.sh"
[[ -z $(ps -eo comm | grep '^nvidia-cuda-mps' || true) ]]
export CUDA_VISIBLE_DEVICES=$(nvidia-smi --id=0 --query-gpu=uuid --format=csv,noheader)
[[ ! -e "$EXP_ROOT/evidence/runtime-probe.json" ]]
"$EXP_ROOT/envs/space/bin/python" "$EXP_ROOT/scripts/probe_runtime.py" >"$EXP_ROOT/logs/runtime-probe.log" 2>&1
