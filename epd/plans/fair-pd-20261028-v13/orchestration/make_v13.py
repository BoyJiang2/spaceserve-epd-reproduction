"""Derive v13 from frozen v13-a: only the CPU-unit POLICY for the 2026-10-28 qjh000 CPU ticket.

Byte-level replacement keeps the file's CRLF endings; v13-a is never modified.
"""
import hashlib
import json
import shutil
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
FOLLOWUP = PROJECT / "work" / "epd-pd-followup-20261027"
SRC, DST = FOLLOWUP / "v13-a", FOLLOWUP / "v13"
PROPOSAL = PROJECT / "outputs" / "pd-baseline-proposal"
PRIOR_MANIFEST = PROPOSAL / "source-manifest-v13-a.json"
NEW_MANIFEST = PROPOSAL / "source-manifest-v13.json"

OLD_POLICY = (
    b'POLICY = {"host": "qjh000", "uid": 2147, "boot_id": "c57aee5b-05dd-4c39-81fc-4c76b492d3d6",\r\n'
    b'          "source_root": "/var/tmp/boyjiang-epd-cpu-qjh000-20261027/epd/code/fair-pd-candidate-20261027-v11",\r\n'
    b'          "booking_id": "bk-20261027T1130-99a32163", "cpu": 50, "memory_bytes": 1073741824,\r\n'
    b'          "wall_seconds": 300, "cleanup_seconds": 30, "earliest_ms": 1793098800000,\r\n'
    b'          "safe_end_ms": 1793145600000, "booking_start_ms": 1793098800000,\r\n'
    b'          "booking_end_ms": 1793145600000}\r\n')
NEW_POLICY = (
    b'POLICY = {"host": "qjh000", "uid": 2147, "boot_id": "c57aee5b-05dd-4c39-81fc-4c76b492d3d6",\r\n'
    b'          "source_root": "/var/tmp/boyjiang-epd-cpu-qjh000-20261028/epd/code/fair-pd-candidate-20261028-v13",\r\n'
    b'          "booking_id": "bk-20261028T0141-8936eb9c", "cpu": 50, "memory_bytes": 1073741824,\r\n'
    b'          "wall_seconds": 300, "cleanup_seconds": 30, "earliest_ms": 1793149200000,\r\n'
    b'          "safe_end_ms": 1793185200000, "booking_start_ms": 1793149200000,\r\n'
    b'          "booking_end_ms": 1793185200000}\r\n')
OLD_MESSAGE = b'"Exact fresh qjh000 19:00-to-08:00 CPU booking differs"'
NEW_MESSAGE = b'"Exact fresh qjh000 09:00-to-19:00 CPU booking differs"'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    prior = json.loads(PRIOR_MANIFEST.read_bytes())
    for item in prior["files"]:
        if sha((SRC / item["path"]).read_bytes()) != item["sha256"]:
            raise SystemExit("v13-a differs from its manifest: " + item["path"])
    if DST.exists() or NEW_MANIFEST.exists():
        raise SystemExit("v13 already exists; refusing to overwrite")
    shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns("__pycache__"))
    runner = DST / "cpu_target_runner.py"
    data = runner.read_bytes()
    if data.count(OLD_POLICY) != 1 or data.count(OLD_MESSAGE) != 1:
        raise SystemExit("Expected v13-a POLICY/message text not found exactly once")
    runner.write_bytes(data.replace(OLD_POLICY, NEW_POLICY).replace(OLD_MESSAGE, NEW_MESSAGE))
    files, changed = [], []
    for item in prior["files"]:
        digest = sha((DST / item["path"]).read_bytes())
        files.append({"path": item["path"], "sha256": digest})
        if digest != item["sha256"]:
            changed.append(item["path"])
    if changed != ["cpu_target_runner.py"]:
        raise SystemExit("Unexpected changed files: %r" % changed)
    manifest = {
        "upstream_commit": prior["upstream_commit"],
        "state": "v13_CPU_unit_policy_qjh000_20261028_UNEXECUTED_pending_independent_G2",
        "prior_v13a_manifest_sha256": sha(PRIOR_MANIFEST.read_bytes()),
        "prior_v13a_members_verified_unchanged": len(files) - len(changed),
        "changed_source_files": changed,
        "files": files,
    }
    NEW_MANIFEST.write_bytes((json.dumps(manifest, indent=2) + "\n").encode())
    print("v13 created;", len(files), "files; manifest sha256", sha(NEW_MANIFEST.read_bytes()))


if __name__ == "__main__":
    main()
