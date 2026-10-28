"""Write reviews/CPU-stage-G2.json for the 2026-10-28 SpaceServe window from an approving G1+G2 review.

Usage: python -X utf8 -I write_stage_approval.py <review_text.md> <reviewer_id>
The approval pins the exact stage_cpu.py bytes it covers (stage_cpu.py checks stage_sha256) and the
review text by SHA; it grants CPU staging only, never GPU work.
"""
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

WINDOW = Path(__file__).resolve().parents[2] / "repository-upload" / "checkout" / "spaceserve" / "code" / "h20-window-20261028"


def main():
    review, reviewer = Path(sys.argv[1]), sys.argv[2]
    text = review.read_text(encoding="utf-8")
    result = json.loads(re.findall(r"^GATE_RESULT:\s*(\{.*\})\s*$", text, re.M)[-1])
    if result.get("gate") != "G1+G2" or result.get("decision") not in ("APPROVE", "APPROVE_WITH_NITS") or result.get("blocking") != 0:
        raise SystemExit(f"review does not approve: {result}")
    out = WINDOW / "reviews" / "CPU-stage-G2.json"
    if out.exists():
        raise SystemExit("approval exists; refusing to overwrite")
    approval = {
        "scope": "Space-CPU-stage-only",
        "passed": True,
        "stage_sha256": hashlib.sha256((WINDOW / "scripts" / "stage_cpu.py").read_bytes()).hexdigest(),
        "reviewer": reviewer,
        "review_path": f"reviews/{review.name}",
        "review_sha256": hashlib.sha256(review.read_bytes()).hexdigest(),
        "source": "/var/tmp/boyjiang-spaceserve-revision-20261027",
        "target": "/var/tmp/boyjiang-spaceserve-window-20261028-2300",
        "issued_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cpu_booking_id": "bk-20261028T0141-8936eb9c",
        "gpu_booking_id": "bk-20261028T0700-987277c5",
        "grants_no_GPU": True,
        "note": "CPU staging only, inside the user's CPU ticket before 19:00; deployment/numeric/model/formal need their own gates after 23:00.",
    }
    out.write_text(json.dumps(approval, indent=2) + "\n", encoding="utf-8")
    print(out.name, hashlib.sha256(out.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
