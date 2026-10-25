#!/usr/bin/env bash
set -euo pipefail
p=${1:?Experiment root}
host=$(hostname)
[[ -f "$p/results/$host-matrices-COMPLETED" && -f "$p/results/postflight-COMPLETED" ]]
cp "$p/results/$host-matrices-COMPLETED" "$p/results/postflight-COMPLETED" "$p/evidence/"
cp "$p/models/MiniCPM-V-2_6/download_manifest.json" "$p/evidence/model-manifest.json"
"$p/envs/tools/bin/uv" pip freeze --python "$p/envs/epd/bin/python" >"$p/evidence/epd-h20-freeze.txt"
"$p/envs/epd/bin/python" - "$p" <<'PY'
import hashlib, json, pathlib, shutil, subprocess, sys
p = pathlib.Path(sys.argv[1]); src = p / 'src/epdserve'
commit = subprocess.check_output(['git', '-C', str(src), 'rev-parse', 'HEAD'], text=True).strip()
assert commit == '9b111f710dfb4724072b603d626a1e4dad93ef1f'
files = subprocess.check_output(['git', '-C', str(src), 'ls-files', 'csrc'], text=True).splitlines()
records = []
for name in files:
    path = pathlib.Path(name)
    if 'build' in path.parts or not (path.suffix in ('.cpp', '.cc', '.h', '.hpp', '.cu', '.cuh') or path.name == 'CMakeLists.txt'):
        continue
    expected = subprocess.check_output(['git', '-C', str(src), 'rev-parse', f'HEAD:{name}'], text=True).strip()
    actual = subprocess.check_output(['git', '-C', str(src), 'hash-object', name], text=True).strip()
    assert expected == actual, name
    records.append({'file': name, 'git_blob': actual, 'sha256': hashlib.sha256((src / path).read_bytes()).hexdigest()})
assert records
(p / 'evidence/native-source-manifest.json').write_text(json.dumps({'commit': commit, 'native_sources_unmodified': True, 'files': records}, indent=2))
for file in (p / 'scripts').iterdir():
    target = p / 'evidence/used-scripts' / file.name
    if file.is_file() and not target.exists(): shutil.copyfile(file, target)
(p / 'evidence/epd-compat.patch').write_bytes(subprocess.check_output(['git', '-C', str(src), 'diff', '--', 'epdserve/api_server.py', 'epdserve/llm_async.py']))
PY
mkdir -p "$p/evidence/build"
cp "$p/build/epd-cuda/CMakeCache.txt" "$p/build/epd-cuda/CMakeFiles/cuda_ipc_utils.dir/flags.make" "$p/build/epd-cuda/CMakeFiles/cuda_ipc_utils.dir/link.txt" "$p/evidence/build/"
site="$p/envs/epd/lib/python3.10/site-packages"
sha256sum "$p/build/epd-cuda/libcuda_ipc_utils.so" "$site/nvidia/cublas/lib/libcublas.so.12" "$site/nvidia/cublas/lib/libcublasLt.so.12" >"$p/evidence/runtime-libraries.sha256"
nvidia-smi --query-compute-apps=gpu_uuid,pid --format=csv >"$p/evidence/gpu-processes-after.csv"
tar -czf "$p/tmp/h20-delivery.tar.gz" \
    --transform="s,^evidence,evidence/$host," \
    --transform="s,^logs,evidence/$host/logs," \
    --transform="s,^results/formal,data/raw/$host," \
    -C "$p" evidence logs results/formal
ls -lh "$p/tmp/h20-delivery.tar.gz"
