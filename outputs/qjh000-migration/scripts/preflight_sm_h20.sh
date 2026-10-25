#!/usr/bin/env bash
set -euo pipefail
export EXP_ROOT=/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023
[[ $(hostname) == qjh000 && -f "$EXP_ROOT/evidence/G2_SM_APPROVED" ]]
if [[ ${REPRO_HOST_LOCK_HELD:-0} != 1 ]]; then
    exec "$EXP_ROOT/envs/manage/bin/python" "$EXP_ROOT/scripts/gpu_exclusive.py" space bash "$0" "$@"
fi
export REPRO_USE_MPS=0
unset CUDA_MPS_PIPE_DIRECTORY CUDA_MPS_LOG_DIRECTORY CUDA_MPS_ACTIVE_THREAD_PERCENTAGE
source "$EXP_ROOT/scripts/env.sh"
OUT="$EXP_ROOT/results/sm-feasibility"
[[ ! -e "$OUT" ]]
[[ -z $(nvidia-smi --id=0 --query-compute-apps=pid --format=csv,noheader) ]]
[[ ! -e "$EXP_ROOT/tmp/mps/control" ]]
mkdir -p "$OUT"
export CUDA_VISIBLE_DEVICES=$(nvidia-smi --id=0 --query-gpu=uuid --format=csv,noheader)
nvidia-smi --id=0 --query-gpu=index,name,uuid,memory.used,driver_version --format=csv >"$OUT/device.csv"
ps -eo pid,user,comm | grep nvidia-cuda-mps >"$OUT/mps-before.txt" || true
[[ ! -s "$OUT/mps-before.txt" ]] || { echo 'Existing MPS processes: stop this probe without touching them' >&2; exit 2; }
mkdir "$OUT/library"
REVISION=$(git -C "$EXP_ROOT/src/mysmctrl" rev-parse HEAD)
[[ "$REVISION" == 6ff57356968a3f04158b9273aa881ee6bdf04229 ]]
git -C "$EXP_ROOT/src/mysmctrl" archive "$REVISION" libsmctrl.c libsmctrl.h Makefile | tar -x -C "$OUT/library"
make -C "$OUT/library" libsmctrl.so >"$OUT/build-library.log" 2>&1
/usr/local/cuda-12.8/bin/nvcc -gencode arch=compute_90,code=sm_90 "$EXP_ROOT/scripts/probe_sm_mask.cu" -o "$OUT/probe_sm_mask" -ldl >"$OUT/build-probe.log" 2>&1
sha256sum "$OUT/library/libsmctrl.so" "$OUT/probe_sm_mask" >"$OUT/binaries.sha256"
echo "$REVISION" >"$OUT/library-revision.txt"
OWN_MPS=0
cleanup() {
    if [[ "$OWN_MPS" == 1 ]]; then
        bash "$EXP_ROOT/scripts/mps_control.sh" status >"$OUT/mps-before-stop.txt" 2>&1 || true
        bash "$EXP_ROOT/scripts/mps_control.sh" stop >"$OUT/mps-stop.txt" 2>&1
        OWN_MPS=0
    fi
}
trap cleanup EXIT
trap 'exit 143' TERM INT
for MODE in no-mps private-mps; do
    if [[ "$MODE" == private-mps ]]; then
        export REPRO_USE_MPS=1 CUDA_MPS_ACTIVE_THREAD_PERCENTAGE=100
        source "$EXP_ROOT/scripts/env.sh"
        for ((ATTEMPT=0; ATTEMPT<15; ATTEMPT++)); do
            [[ -n $(nvidia-smi --id=0 --query-compute-apps=pid --format=csv,noheader) ]] || break
            sleep 1
        done
        [[ -z $(nvidia-smi --id=0 --query-compute-apps=pid --format=csv,noheader) ]]
        bash "$EXP_ROOT/scripts/mps_control.sh" start 0 >"$OUT/mps-start.txt" 2>&1
        OWN_MPS=1
    fi
    for REPEAT in 1 2 3; do
        if "$OUT/probe_sm_mask" "$OUT/library/libsmctrl.so" >"$OUT/$MODE-$REPEAT.jsonl" 2>"$OUT/$MODE-$REPEAT.stderr"; then
            RC=0
        else
            RC=$?
        fi
        echo "$RC" >"$OUT/$MODE-$REPEAT.exit-code"
    done
done
cleanup
nvidia-smi --id=0 --query-compute-apps=pid,gpu_uuid --format=csv >"$OUT/processes-after.csv"
date -u +%FT%TZ >"$OUT/COMPLETED"
# This is feasibility evidence. A passing mask still requires service-stream
# probes under the actual service MPS session before the third group is accepted.
