#!/usr/bin/env bash
set -euo pipefail
[[ ${1:-} != start || ${REPRO_HOST_LOCK_HELD:-0} == 1 ]]
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export REPRO_USE_MPS=1 CUDA_MPS_ACTIVE_THREAD_PERCENTAGE=100
source "$SCRIPT_DIR/env.sh"
exec /var/tmp/boyjiang-spaceserve-epd-qjh000-20261023/envs/manage/bin/python "$SCRIPT_DIR/mps_owner.py" "$@"
