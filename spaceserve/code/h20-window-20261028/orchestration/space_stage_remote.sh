#!/usr/bin/env bash
# Runs on qjh000 via `ssh qjh000 bash -s -- <commit> <step>` during the user's CPU ticket (before 19:00).
# step=checkout : new stage dir, sparse checkout of exactly <commit> (spaceserve/code/h20-window-20261028)
# step=tests    : CPU-only stage tests with the frozen revision environment (no GPU, no model)
# step=stage    : stage_cpu.py copies the seven frozen members to the new window root (CPU only)
# Never deletes or reuses existing directories; failures leave everything in place.
set -euo pipefail
COMMIT="$1"
STEP="$2"
STAGE=/var/tmp/boyjiang-space2300-stage
CHECKOUT=$STAGE/git-checkout
PREFIX=spaceserve/code/h20-window-20261028
PY=/var/tmp/boyjiang-spaceserve-revision-20261027/envs/space/bin/python
REPO=https://github.com/BoyJiang2/spaceserve-epd-reproduction.git
[[ "$COMMIT" =~ ^[0-9a-f]{40}$ ]] || { echo "bad commit" >&2; exit 2; }
umask 077
export GIT_TERMINAL_PROMPT=0
case "$STEP" in
  checkout)
    [[ ! -e "$STAGE" ]] || { echo "stage dir exists; refusing" >&2; exit 3; }
    mkdir -m 700 "$STAGE" "$STAGE/evidence"
    timeout 600 git -c core.autocrlf=false clone -q --filter=blob:none --sparse --no-checkout --depth=1 "$REPO" "$CHECKOUT"
    git -C "$CHECKOUT" config core.autocrlf false
    git -C "$CHECKOUT" sparse-checkout set --no-cone "/$PREFIX/"
    timeout 600 git -C "$CHECKOUT" fetch -q --depth 1 --filter=blob:none origin "$COMMIT"
    timeout 600 git -C "$CHECKOUT" checkout -q --detach "$COMMIT"
    [[ "$(git -C "$CHECKOUT" rev-parse HEAD)" == "$COMMIT" ]] || { echo "HEAD differs" >&2; exit 4; }
    [[ -z "$(git -C "$CHECKOUT" status --porcelain --untracked-files=all)" ]] || { echo "checkout not clean" >&2; exit 5; }
    (cd "$CHECKOUT/$PREFIX" && sha256sum scripts/* configs/* tools/*) > "$STAGE/evidence/checkout-sha256.txt"
    echo "CHECKOUT_OK $COMMIT"
    ;;
  tests)
    cd "$CHECKOUT/$PREFIX/scripts"
    for t in test_stage_cpu test_lifecycle_signals test_window_booking; do
      CUDA_VISIBLE_DEVICES= taskset -c 50 nice -n 10 "$PY" -B -m unittest -v "$t" > "$STAGE/evidence/$t.log" 2>&1 \
        && echo "$t PASS" || { echo "$t FAIL"; tail -20 "$STAGE/evidence/$t.log"; exit 8; }
      if grep -Eiq 'skipped=|\.\.\. skipped|OK \(skipped' "$STAGE/evidence/$t.log"; then
        echo "$t SKIP refused" >&2
        exit 9
      fi
    done
    ;;
  stage)
    APPROVAL="$CHECKOUT/$PREFIX/reviews/CPU-stage-G2.json"  # committed with the reviewed window code
    [[ -f "$APPROVAL" ]] || { echo "stage approval missing" >&2; exit 6; }
    cd "$CHECKOUT/$PREFIX/scripts"
    CUDA_VISIBLE_DEVICES= nice -n 10 "$PY" -B stage_cpu.py --approval "$APPROVAL" > "$STAGE/evidence/stage-copy.log" 2>&1
    echo "STAGE_EXIT=$?"
    ;;
  place)
    # Copy the committed 56 scripts and static configs into the staged root (the deploy tool later only
    # re-verifies byte-identical files); relocated-inputs.json must already equal the committed copy.
    ROOT=/var/tmp/boyjiang-spaceserve-window-20261028-2300
    SRC="$CHECKOUT/$PREFIX"
    cmp -s "$SRC/configs/relocated-inputs.json" "$ROOT/configs/relocated-inputs.json" \
      || { echo "staged relocated-inputs.json differs from the committed copy" >&2; exit 7; }
    "$PY" -B -I - "$SRC" "$ROOT" <<'PY'
import hashlib, json, shutil, sys
from pathlib import Path
src, root = Path(sys.argv[1]), Path(sys.argv[2])
rows = json.loads((src / "configs/deployment-files.json").read_text())
for row in rows:
    s, t = src / row["path"], root / row["path"]
    if hashlib.sha256(s.read_bytes()).hexdigest() != row["sha256"]:
        sys.exit("checkout differs from deployment manifest: " + row["path"])
    if t.exists():
        if hashlib.sha256(t.read_bytes()).hexdigest() != row["sha256"]:
            sys.exit("existing runtime file differs; refusing to overwrite: " + row["path"])
        continue
    t.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(s, t)
    if hashlib.sha256(t.read_bytes()).hexdigest() != row["sha256"]:
        sys.exit("placed bytes differ: " + row["path"])
print("PLACED", len(rows))
PY
    ;;
  *) echo "unknown step" >&2; exit 2 ;;
esac
