#!/usr/bin/env bash
# Runs on qjh000 via `ssh qjh000 bash -s -- <commit> <manifest_sha256>`.
# Creates the new owned root, sparse-checks-out exactly <commit>, and records per-file SHAs.
# Never deletes or reuses an existing root; a failure leaves everything in place for inspection.
set -euo pipefail
COMMIT="$1"
MANIFEST_SHA="$2"
ROOT=/var/tmp/boyjiang-epd-cpu-qjh000-20261028
REPO=https://github.com/BoyJiang2/spaceserve-epd-reproduction.git
CODE_REL=epd/code/fair-pd-candidate-20261028-v13
PLAN_REL=epd/plans/fair-pd-20261028-v13
[[ "$COMMIT" =~ ^[0-9a-f]{40}$ ]] || { echo "bad commit" >&2; exit 2; }
[[ ! -e "$ROOT" ]] || { echo "ROOT already exists; refusing to reuse" >&2; exit 3; }
umask 077
export GIT_TERMINAL_PROMPT=0
# Same clone pattern as the verified SpaceServe Git-first deployment.
timeout 600 git -c core.autocrlf=false clone -q --filter=blob:none --sparse --no-checkout --depth=1 "$REPO" "$ROOT"
chmod 700 "$ROOT"
cd "$ROOT"
git config core.autocrlf false
git sparse-checkout set --no-cone "/$CODE_REL/" "/$PLAN_REL/"
timeout 600 git fetch -q --depth 1 --filter=blob:none origin "$COMMIT"
timeout 600 git checkout -q --detach "$COMMIT"
taskset -c 50 nice -n 10 /usr/bin/python3 -I -S -B - "$ROOT" "$COMMIT" "$MANIFEST_SHA" "$CODE_REL" "$PLAN_REL" <<'PY'
import hashlib, json, os, subprocess, sys
from pathlib import Path
root, commit, manifest_sha, code_rel, plan_rel = sys.argv[1:6]
code, plan = Path(root, code_rel), Path(root, plan_rel)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest_path = plan / "source-manifest-v13.json"
if sha(manifest_path) != manifest_sha:
    sys.exit("checked-out manifest SHA differs")
manifest = json.loads(manifest_path.read_bytes())
files = [{"path": f["path"], "sha256": sha(code / f["path"])} for f in manifest["files"]]
mismatch = [f["path"] for f, m in zip(files, manifest["files"]) if f["sha256"] != m["sha256"]]
actual = sorted(p.relative_to(code).as_posix() for p in code.rglob("*") if p.is_file())
git = lambda *a: subprocess.check_output(["git", "-C", str(code), *a], text=True).strip()
record = {
    "scope": "actual_CPU_deployment_only_not_tests",
    "commit": commit, "head": git("rev-parse", "HEAD"), "origin": git("remote", "get-url", "origin"),
    "source_root": str(code), "uid": os.getuid(),
    "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
    "affinity": sorted(os.sched_getaffinity(0)), "nice": os.getpriority(os.PRIO_PROCESS, 0),
    "python": sys.version, "manifest_sha256": manifest_sha,
    "tracked_clean": git("status", "--porcelain", "--untracked-files=no") == "",
    "unlisted_files": sorted(set(actual) - {f["path"] for f in files}),
    "mismatched_files": mismatch, "files": files,
}
out = plan / "cpu-inputs"
out.mkdir(mode=0o700)
(out / "deployment.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({k: record[k] for k in ("commit", "head", "tracked_clean", "mismatched_files", "unlisted_files", "affinity", "nice")}))
if record["head"] != commit or not record["tracked_clean"] or mismatch or record["unlisted_files"]:
    sys.exit("deployment verification failed")
PY
echo "DEPLOY_OK"
