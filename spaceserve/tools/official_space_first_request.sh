#!/usr/bin/env bash
# One diagnostic request, after independent runtime approval and fresh booking checks.
set -euo pipefail
: "${BOOK_START_EPOCH:?}" "${BOOK_END_EPOCH:?}" "${UNIT_START_EPOCH:?}"
: "${GPU_IDS:?}" "${PORT:?}" "${RUN:?}" "${HELPER:?}"
: "${SOURCE_ROLE:?native or fork}"
case "$SOURCE_ROLE" in
  native) EXPECTED_HEAD=d7ec548300d7950c1305231b2aaf970bab7569c1 ;;
  fork) EXPECTED_HEAD=66de079af4234b27f7f82ff91d238ef1351324ba ;;
  *) exit 1 ;;
esac
START=$UNIT_START_EPOCH
now=$(date +%s)
test "$now" -ge "$BOOK_START_EPOCH" && test "$now" -ge "$START"
test "$((now - START))" -le 5 && test "$((BOOK_END_EPOCH - START))" -ge 900
ROOT=/local/boyjiang/SpaceServe-official
PY=/local/boyjiang/spaceserve/assets/envs/space/bin/python
CPU_PY=/usr/bin/python3
MODEL="$ROOT/assets/models/Qwen2-VL-7B-Instruct"
LOAD_END=$((START + 600)); WORK_END=$((START + 720))
test "$(id -u)" = 2147
case "$RUN" in /local/boyjiang/spaceserve/runs/*) ;; *) exit 1 ;; esac
test -d "$RUN" && test ! -e "$RUN/identity.json"
test "$(sha256sum "$HELPER" | cut -d' ' -f1)" = 7b6ae95a889470bc8e5ac0b0618da2ae63f1db0a0b2534613a55a16ef3146136
command -v ss; command -v timeout; command -v curl
test "$(git --no-optional-locks -c core.fsmonitor=false -C "$ROOT" rev-parse HEAD)" = "$EXPECTED_HEAD"
test -z "$(git --no-optional-locks -c core.fsmonitor=false -C "$ROOT" status --porcelain=v1 --untracked-files=all)"
STATE="$RUN/identity.json"
"$CPU_PY" -I -S -B - "$STATE" "$ROOT" "$GPU_IDS" "$PORT" <<'PY'
import json, os, pathlib, socket, sys, time, uuid
path, root, gpu_ids, port = sys.argv[1:]
assert len(gpu_ids.split(',')) == 1
assert all(value.isdigit() for value in gpu_ids.split(','))
assert 1024 <= int(port) <= 65535
with socket.socket() as probe:
    probe.bind(('127.0.0.1', int(port)))
state = {'uid': os.getuid(), 'root': root, 'runid': str(pathlib.Path(path).parent.resolve()) + ':' + uuid.uuid4().hex, 'boot': pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'min_start_ticks': int(float(pathlib.Path('/proc/uptime').read_text().split()[0]) * os.sysconf('SC_CLK_TCK')), 'created_epoch': time.time(), 'known': {}}
pathlib.Path(path).write_text(json.dumps(state, indent=2))
PY
RUNID=$("$CPU_PY" -I -S -B -c 'import json,sys; print(json.load(open(sys.argv[1]))["runid"])' "$STATE")
TARGET=(taskset -c 0-89 env -u LD_PRELOAD -u PYTHONHOME -u RAY_ADDRESS -u RAY_TMPDIR -u VLLM_TORCH_PROFILER_DIR EXP_ROOT="$ROOT" REPRO_RUN_ID="$RUNID"
  CUDA_VISIBLE_DEVICES="$GPU_IDS" PYTHONPATH="$ROOT" VLLM_USE_V1=1 OMP_NUM_THREADS=4
  PYTHONDONTWRITEBYTECODE=1)
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
import torch, vllm
modules = {name: {'file': getattr(module, '__file__', None), 'version': getattr(module, '__version__', None)} for name, module in [('torch', torch), ('vllm', vllm)]}
extension = sys.modules.get('vllm._C')
modules['vllm._C_already_loaded'] = getattr(extension, '__file__', None)
print(json.dumps({'executable': sys.executable, 'python': sys.version, 'modules': modules}, indent=2), flush=True)
assert pathlib.Path(vllm.__file__).resolve().is_relative_to(pathlib.Path(sys.argv[1]))
PY
remaining=$((LOAD_END - $(date +%s))); test "$remaining" -gt 0
"$CPU_PY" -I -S -B - "$RUN" <<'PY'
import base64, hashlib, json, pathlib, sys
run = pathlib.Path(sys.argv[1])
image = pathlib.Path('/local/boyjiang/epd/assets/dataset/COCO_val2014_000000000328.jpg')
data = image.read_bytes()
assert hashlib.sha256(data).hexdigest() == 'cc5ceef6348a3d73d5742fc2fe8b3ad3636de1cdaa8b7ca18e5fee83335e93d6'
payload = {'model': 'reproduction-qwen2-vl7b', 'messages': [{'role': 'user', 'content': [{'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' + base64.b64encode(data).decode()}}, {'type': 'text', 'text': 'Describe the image.'}]}], 'n': 1, 'temperature': 0.0, 'top_p': 1.0, 'max_tokens': 128, 'ignore_eos': True, 'stream': False}
encoded = (json.dumps(payload, ensure_ascii=False) + '\n').encode()
(run/'request.json').write_bytes(encoded)
(run/'request.sha256').write_text(hashlib.sha256(encoded).hexdigest() + '  request.json\n')
(run/'image.sha256').write_text(hashlib.sha256(data).hexdigest() + '  ' + str(image) + '\n')
PY
remaining=$((WORK_END - $(date +%s))); test "$remaining" -gt 120
"${TARGET[@]}" timeout --signal=TERM --kill-after=15s "$remaining" "$PY" -u -B -m vllm.entrypoints.openai.api_server \
  --host 127.0.0.1 --port "$PORT" --model "$MODEL" --served-model-name reproduction-qwen2-vl7b \
  --dtype half --tensor-parallel-size 1 --enforce-eager --gpu-memory-utilization 0.8 \
  --limit-mm-per-prompt '{"image":1}' --seed 0 --disable-log-requests \
  >"$RUN/server.stdout" 2>"$RUN/server.stderr" &
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
limit=$remaining; test "$limit" -le 120 || limit=120
if curl --silent --show-error --connect-timeout 5 --max-time "$limit" --retry 0 \
  -D "$RUN/response.headers" -o "$RUN/response.json" -w '%{http_code}\n' \
  -H 'Content-Type: application/json' --data-binary "@$RUN/request.json" \
  "http://127.0.0.1:$PORT/v1/chat/completions" >"$RUN/http-code.txt" 2>"$RUN/curl.stderr"; then
  curl_rc=0
else
  curl_rc=$?
fi
printf '%s\n' "$curl_rc" >"$RUN/curl.exit"
test "$curl_rc" = 0
check_server || exit 1
check_listener || exit 1
"$CPU_PY" -I -S -B - "$RUN" <<'PY'
import json, pathlib, sys
run = pathlib.Path(sys.argv[1])
assert (run/'http-code.txt').read_text().strip() == '200'
data = json.loads((run/'response.json').read_text())
assert len(data['choices']) == 1
content = data['choices'][0]['message']['content']
assert isinstance(content, str) and content.strip()
usage = data['usage']
assert isinstance(usage['completion_tokens'], int)
summary = {'output': content, 'usage': usage, 'actual_output_tokens': usage['completion_tokens'], 'target_output_tokens': 128, 'finish_reason': data['choices'][0]['finish_reason'], 'semantic_correctness': 'PENDING_IMAGE_AND_OUTPUT_REVIEW', 'client_TTFT': None, 'actual_visual_tokens': None, 'mechanisms_verified': False}
(run/'response-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))
assert usage['completion_tokens'] == 128, 'retain short/extra output as failure'
PY
exit 0
