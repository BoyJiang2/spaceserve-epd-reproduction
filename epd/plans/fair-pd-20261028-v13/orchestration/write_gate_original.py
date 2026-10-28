"""Wrap an independent reviewer's verbatim text into the gate JSON the CPU runner consumes.

Usage: python -X utf8 -I write_gate_original.py <G1|G2> <review_text.md> <reviewed_at_utc>

The scope digest is recomputed from the plan directory's scope.json (and, for G2, the manifest
bytes) instead of being copied from the review, and the review's own GATE_RESULT line must agree.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

PLAN = Path(__file__).resolve().parents[2] / "repository-upload" / "checkout" / "epd" / "plans" / "fair-pd-20261028-v13"
REVIEWERS = {"G1": "claude-code/subagent-G1-cpu-unit-20261028", "G2": "claude-code/subagent-G2-v13-code-20261028"}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    gate, text_path, reviewed_at = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    text = text_path.read_text(encoding="utf-8").strip()
    scope = json.loads((PLAN / "scope.json").read_bytes())
    scope_sha = digest(scope)
    if gate == "G2":
        manifest_sha = hashlib.sha256((PLAN / "source-manifest-v13.json").read_bytes()).hexdigest()
        scope_sha = digest({"scope_sha256": scope_sha, "source_manifest_sha256": manifest_sha})
    result = json.loads(re.findall(r"^GATE_RESULT:\s*(\{.*\})\s*$", text, re.M)[-1])
    if result["gate"] != gate or result["scope_sha256"] != scope_sha:
        raise SystemExit(f"review GATE_RESULT {result} does not bind the recomputed scope {scope_sha}")
    if result["decision"] not in ("APPROVE", "APPROVE_WITH_NITS") or result["blocking"] != 0:
        raise SystemExit("review does not approve this gate")
    if REVIEWERS[gate] not in scope["reviewer_ids"] or REVIEWERS[gate] == scope["executor_id"]:
        raise SystemExit("reviewer id is not an independent scope reviewer")
    record = {"gate": gate, "scope_sha256": scope_sha, "decision": result["decision"], "blocking": 0,
              "reviewer_id": REVIEWERS[gate], "reviewed_at_utc": reviewed_at, "original_review_text": text}
    out = PLAN / f"{gate}-original.json"
    if out.exists():
        raise SystemExit(f"{out.name} exists; refusing to overwrite")
    out.write_bytes((json.dumps(record, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    print(out.name, hashlib.sha256(out.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
