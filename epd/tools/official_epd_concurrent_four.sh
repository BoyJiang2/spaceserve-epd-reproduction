#!/usr/bin/env bash
# One diagnostic request, after independent runtime approval and fresh booking checks.
set -euo pipefail
: "${BOOK_START_EPOCH:?}" "${BOOK_END_EPOCH:?}" "${UNIT_START_EPOCH:?}"
: "${GPU_IDS:?}" "${PORT:?}" "${RUN:?}" "${HELPER:?}"
: "${CLIENT:?}"
: "${FINALIZER:?}"
START=$UNIT_START_EPOCH
now=$(date +%s)
test "$now" -ge "$BOOK_START_EPOCH" && test "$now" -ge "$START"
test "$((now - START))" -le 5 && test "$((BOOK_END_EPOCH - START))" -ge 900
ROOT=/local/boyjiang/epdserve-official
PY=/local/boyjiang/epd/assets/envs/epd/bin/python
CPU_PY=/usr/bin/python3
MODEL="$ROOT/assets/models/MiniCPM-V-2_6"
LOAD_END=$((START + 600)); WORK_END=$((START + 720))
test "$(id -u)" = 2147
case "$RUN" in /local/boyjiang/epd/runs/*) ;; *) exit 1 ;; esac
test -d "$RUN" && test ! -e "$RUN/identity.json"
test "$(sha256sum "$HELPER" | cut -d' ' -f1)" = eee078afa9aebdd7d0838331d2e85d298a769bfae5322c2432fb73e40efe1ee3
test "$(sha256sum "$CLIENT" | cut -d' ' -f1)" = a5460cc1787c41daa06a17c8a0b52c20440888b46b96d59a27b39976d0009cdb
test "$(sha256sum "$FINALIZER" | cut -d' ' -f1)" = 5b646e564e6bebc13a876305b38d30e49033f01a0d4fe47c9c947746f137f5cd
command -v ss; command -v timeout
test "$(git --no-optional-locks -c core.fsmonitor=false -C "$ROOT" rev-parse HEAD)" = 06fbcb6f3f3b931950077077c9a040e9c238deee
test -z "$(git --no-optional-locks -c core.fsmonitor=false -C "$ROOT" status --porcelain=v1 --untracked-files=all)"
STATE="$RUN/identity.json"
"$CPU_PY" -I -S -B - "$STATE" "$ROOT" "$GPU_IDS" "$PORT" <<'PY'
import json, os, pathlib, socket, sys, time, uuid
path, root, gpu_ids, port = sys.argv[1:]
assert len(gpu_ids.split(',')) == len(set(gpu_ids.split(','))) == 3
assert all(value.isdigit() for value in gpu_ids.split(','))
assert 1024 <= int(port) <= 65535
with socket.socket() as probe:
    probe.bind(('127.0.0.1', int(port)))
state = {'uid': os.getuid(), 'root': root, 'runid': str(pathlib.Path(path).parent.resolve()) + ':' + uuid.uuid4().hex, 'boot': pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'min_start_ticks': int(float(pathlib.Path('/proc/uptime').read_text().split()[0]) * os.sysconf('SC_CLK_TCK')), 'created_epoch': time.time(), 'known': {}}
pathlib.Path(path).write_text(json.dumps(state, indent=2))
PY
RUNID=$("$CPU_PY" -I -S -B -c 'import json,sys; print(json.load(open(sys.argv[1]))["runid"])' "$STATE")
TARGET=(taskset -c 0-89 env -u LD_PRELOAD -u PYTHONHOME EXP_ROOT="$ROOT" REPRO_RUN_ID="$RUNID"
  CUDA_VISIBLE_DEVICES="$GPU_IDS" PYTHONPATH="$ROOT" OMP_NUM_THREADS=4 CUDA_IPC_LIB_PATH=/local/boyjiang/epd/assets/build/libcuda_ipc_utils.so
  RAY_ADDRESS=local RAY_TMPDIR="$RUN/ray-tmp" RAY_DEDUP_LOGS=0 PYTHONDONTWRITEBYTECODE=1)
finish_run() {
  rc=$?
  trap - EXIT
  trap '' INT TERM
  set +e
  timeout --signal=TERM --kill-after=5s 60s "$CPU_PY" -I -S -B "$HELPER" stop "$STATE" >"$RUN/cleanup.stdout" 2>"$RUN/cleanup.stderr"
  cleanup_rc=$?
  timeout --signal=TERM --kill-after=2s 5s nvidia-smi -i "$GPU_IDS" --query-compute-apps=pid,gpu_uuid,process_name,used_gpu_memory --format=csv >"$RUN/gpu-apps-after.csv" 2>"$RUN/gpu-apps-after.stderr"
  apps_rc=$?
  timeout --signal=TERM --kill-after=2s 5s nvidia-smi -i "$GPU_IDS" --query-gpu=uuid,memory.used,utilization.gpu --format=csv >"$RUN/gpu-memory-after.csv" 2>"$RUN/gpu-memory-after.stderr"
  memory_rc=$?
  printf '{"work_exit":%s,"cleanup_exit":%s,"gpu_query_exit":%s,"memory_query_exit":%s,"ended_epoch":%s}\n' "$rc" "$cleanup_rc" "$apps_rc" "$memory_rc" "$(date +%s)" >"$RUN/terminal.json"
  test "$cleanup_rc" = 0 && test "$apps_rc" = 0 && test "$memory_rc" = 0 || rc=1
  exit "$rc"
}
trap finish_run EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
cd "$ROOT"
"$CPU_PY" -I -S -B "$HELPER" observe "$STATE" >"$RUN/initial-processes.json"
remaining=$((LOAD_END - $(date +%s))); test "$remaining" -gt 0
"${TARGET[@]}" timeout --signal=TERM --kill-after=5s "$remaining" "$PY" -B - "$ROOT" >"$RUN/module-sources.json" 2>"$RUN/module-sources.stderr" <<'PY'
import json, pathlib, sys
import epdserve, torch, vllm
modules = {name: {'file': getattr(module, '__file__', None), 'version': getattr(module, '__version__', None)} for name, module in [('epdserve', epdserve), ('torch', torch), ('vllm', vllm)]}
extension = sys.modules.get('vllm._C')
modules['vllm._C_already_loaded'] = getattr(extension, '__file__', None)
print(json.dumps({'executable': sys.executable, 'python': sys.version, 'modules': modules}, indent=2), flush=True)
assert pathlib.Path(epdserve.__file__).resolve().is_relative_to(pathlib.Path(sys.argv[1]))
PY
remaining=$((LOAD_END - $(date +%s))); test "$remaining" -gt 0
"${TARGET[@]}" timeout --signal=TERM --kill-after=5s "$remaining" "$PY" -B - "$RUN" "$MODEL" >"$RUN/input.stdout" 2>"$RUN/input.stderr" <<'PY'
import hashlib, json, pathlib, sys
from transformers import AutoTokenizer
run, model = pathlib.Path(sys.argv[1]), sys.argv[2]
image_paths = ['/local/boyjiang/epd/assets/dataset/COCO_val2014_000000000328.jpg', '/local/boyjiang/epd/assets/dataset/COCO_val2014_000000000400.jpg', '/local/boyjiang/epd/assets/dataset/COCO_val2014_000000000623.jpg', '/local/boyjiang/epd/assets/dataset/COCO_val2014_000000001146.jpg']
image_fingerprints = [{'path': '/local/boyjiang/epd/assets/dataset/COCO_val2014_000000000328.jpg', 'bytes': 94868, 'sha256': 'cc5ceef6348a3d73d5742fc2fe8b3ad3636de1cdaa8b7ca18e5fee83335e93d6'}, {'path': '/local/boyjiang/epd/assets/dataset/COCO_val2014_000000000400.jpg', 'bytes': 85129, 'sha256': 'ce04b38a2be66569e8b632197188bada2b38be12bb010ae4f8f2b523b8c50510'}, {'path': '/local/boyjiang/epd/assets/dataset/COCO_val2014_000000000623.jpg', 'bytes': 82972, 'sha256': '802fb23e9766bc23ef9325afc05790b6d41a59f5055aad248b331ed7f8eb3b9a'}, {'path': '/local/boyjiang/epd/assets/dataset/COCO_val2014_000000001146.jpg', 'bytes': 49860, 'sha256': 'a05cd4f6d877f70c23da81d554d6435f18b179b6efe1553d37387d82e9c27059'}]
assert len({pathlib.Path(p).name for p in image_paths}) == 4
for expected in image_fingerprints:
    assert hashlib.sha256(pathlib.Path(expected['path']).read_bytes()).hexdigest() == expected['sha256']
(run/'image-fingerprints.json').write_text(json.dumps(image_fingerprints, indent=2))
tokenizer = AutoTokenizer.from_pretrained(model, trust_remote_code=True, local_files_only=True)
prompt = tokenizer.apply_chat_template([{'role': 'user', 'content': '(<image>./</image>)\nDescribe the image.'}], tokenize=False, add_generation_prompt=True)
payload = {'input': {'prompt': prompt, 'multi_modal_data': {'images_paths': [image_paths[0]]}}, 'n': 1, 'best_of': 1, 'use_beam_search': False, 'temperature': 0.0, 'top_p': 1.0, 'max_tokens': 128, 'ignore_eos': True, 'stream': False}
data = (json.dumps(payload, ensure_ascii=False, indent=2) + '\n').encode()
(run/'request.json').write_bytes(data)
(run/'request.sha256').write_text(hashlib.sha256(data).hexdigest() + '  request.json\n')
(run/'tokenizer-source.json').write_text(json.dumps({'class': type(tokenizer).__name__, 'module': type(tokenizer).__module__, 'prompt': prompt, 'prompt_tokens': tokenizer.encode(prompt)}, ensure_ascii=False))
PY
remaining=$((WORK_END - $(date +%s))); test "$remaining" -gt 120
"${TARGET[@]}" timeout --signal=TERM --kill-after=15s "$remaining" "$PY" -u -B -m epdserve.api_server \
  --host 127.0.0.1 --port "$PORT" --model "$MODEL" --tokenizer "$MODEL" \
  --encoding-data-parallel-size 1 --context-data-parallel-size 1 --decoding-data-parallel-size 1 \
  --intra-request-dp 0 --encoding-max-batch-size 1 --context-max-batch-size 1 \
  --decoding-max-batch-size 1 --limit-mm-per-prompt 4 --gpu-memory-utilization 0.65 \
  --swap-space 1 --seed 0 >"$RUN/server.stdout" 2>"$RUN/server.stderr" &
SERVER=$!
printf '%s\n' "$SERVER" >"$RUN/server-timeout.pid"
check_server() {
  "$CPU_PY" -I -S -B "$HELPER" observe "$STATE" >>"$RUN/process-observations.jsonl" || return 1
  kill -0 "$SERVER" || return 1
  if grep -q 'Traceback (most recent call last):' "$RUN/server.stdout" "$RUN/server.stderr"; then return 1; fi
}
check_listener() {
  ss -H -ltnp "( sport = :$PORT )" >"$RUN/listener.txt" || return 1
  "$CPU_PY" -I -S -B - "$STATE" "$RUN/listener.txt" <<'PY'
import json, pathlib, re, sys
state = json.loads(pathlib.Path(sys.argv[1]).read_text())
listeners = {int(pid) for pid in re.findall(r'pid=(\d+)', pathlib.Path(sys.argv[2]).read_text())}
known = {item['pid'] for item in state['known_live']}
raise SystemExit(0 if listeners and listeners <= known else 1)
PY
}
ready=0
while test "$(date +%s)" -lt "$LOAD_END"; do
  check_server || exit 1
  if check_listener; then ready=1; break; fi
  sleep 1
done
test "$ready" = 1
check_server || exit 1
check_listener || exit 1
remaining=$((WORK_END - $(date +%s))); test "$remaining" -ge 120
if timeout --signal=TERM --kill-after=5s "$remaining" "$CPU_PY" -I -S -B "$CLIENT" --endpoint "http://127.0.0.1:$PORT/generate" --template "$RUN/request.json" --images "$RUN/image-fingerprints.json" --run "$RUN" --deadline-epoch "$WORK_END" >"$RUN/client.stdout" 2>"$RUN/client.stderr"; then
  client_rc=0
else
  client_rc=$?
fi
echo "$client_rc" >"$RUN/client.exit"
"$CPU_PY" -I -S -B "$FINALIZER" "$RUN" "$client_rc" >"$RUN/finalization.stdout" 2>"$RUN/finalization.stderr"
test "$client_rc" = 0
check_server || exit 1
check_listener || exit 1
exit 0
