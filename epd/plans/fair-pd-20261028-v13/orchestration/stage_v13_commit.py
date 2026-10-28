"""Stage exactly the v13 code-publication paths and self-check staged blobs before G5.

Usage: python -X utf8 -I stage_v13_commit.py
Prints the staged tree hash; refuses if anything outside the intended paths is staged.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

CHECKOUT = Path(__file__).resolve().parents[2] / "repository-upload" / "checkout"
CODE = "epd/code/fair-pd-candidate-20261028-v13"
PLAN = "epd/plans/fair-pd-20261028-v13"
NAV = ["epd/README.md", "epd/code/README.md"]
REQUIRED = ["scope.json", "G1-original.json", "G2-original.json", "user-CPU-grant.json",
            "user-original-instruction.txt", "source-manifest-v13.json", "README.md"]


def git(*args, data=None):
    return subprocess.run(["git", "-C", str(CHECKOUT), *args], input=data, capture_output=True, check=True).stdout


def main():
    missing = [name for name in REQUIRED if not (CHECKOUT / PLAN / name).exists()]
    if missing:
        raise SystemExit(f"missing plan files: {missing}")
    if git("diff", "--cached", "--name-only").strip():
        raise SystemExit("index already has staged changes; refusing")
    git("add", "--", CODE, PLAN, *NAV)
    staged = git("diff", "--cached", "--name-only").decode().split()
    outside = [p for p in staged if not (p.startswith(CODE + "/") or p.startswith(PLAN + "/") or p in NAV)]
    if outside:
        raise SystemExit(f"unexpected staged paths: {outside}")
    manifest = json.loads(git("show", f":{PLAN}/source-manifest-v13.json"))
    bad = [f["path"] for f in manifest["files"]
           if hashlib.sha256(git("show", f":{CODE}/{f['path']}")).hexdigest() != f["sha256"]]
    code_paths = sorted(p[len(CODE) + 1:] for p in staged if p.startswith(CODE + "/"))
    if bad or code_paths != sorted(f["path"] for f in manifest["files"]):
        raise SystemExit(f"staged code differs from manifest: {bad}")
    tree = git("write-tree").decode().strip()
    print(json.dumps({"staged_paths": len(staged), "code_files": len(code_paths), "tree": tree,
                      "manifest_sha256": hashlib.sha256(git("show", f":{PLAN}/source-manifest-v13.json")).hexdigest()},
                     indent=2))


if __name__ == "__main__":
    sys.exit(main())
