"""Derive the 2026-10-28 SpaceServe window code from the frozen 13:00 window (Git 83edff6).

Usage: python -X utf8 -I make_space_window.py <booking_id> <start_ms> <end_ms>

Only window identity changes: the new owned root / Ray temp dir / repository prefix, the booking
constants in booking_window.py, regenerated source+deployment manifests, and the deploy tool's
pinned manifest SHAs. Model, inputs, schedule (seed 20261027), budgets and cell rules are untouched.
Byte-level replacement preserves each file's line endings.
"""
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

CHECKOUT = Path(__file__).resolve().parents[2] / "repository-upload" / "checkout"
OLD = CHECKOUT / "spaceserve" / "code" / "h20-window-20261027"
NEW = CHECKOUT / "spaceserve" / "code" / "h20-window-20261028"
REPLACE = [
    (b"/var/tmp/boyjiang-spaceserve-window-20261027-1300", b"/var/tmp/boyjiang-spaceserve-window-20261028-2300"),
    (b"/var/tmp/bj-space1300-qjh000-ray", b"/var/tmp/bj-space2300-qjh000-ray"),
    (b"spaceserve/code/h20-window-20261027", b"spaceserve/code/h20-window-20261028"),
]
OLD_BOOKING = (
    b"START_MS = 1793077200000  # 2026-10-27 13:00 Asia/Shanghai\n"
    b"LATEST_END_MS = 1793091600000  # User's stated latest possible end: 2026-10-27 17:00\n"
    b"AUTHORIZED_EXTENDED_END_MS = 1793095200000  # User explicitly authorized 18:00, not the ticket's 19:00.\n"
    b"EXTENSION_ID = 'bk-20261027T0532-efb16fde'\n"
    b"CLEANUP_SECONDS = 120\n"
    b"BOOKING_ID = 'bk-20261027T0137-bcf3dd23'\n")


# This window has no extension ticket: any receipt carrying one is refused.
EXTENSION_GUARD_OLD = b"    if extension is not None:\n"
EXTENSION_GUARD_NEW = (b"    if extension is not None:\n"
                       b"        if EXTENSION_ID is None:\n"
                       b"            raise RuntimeError('this window has no extension ticket')\n")
OLD_FOUR_HOURS = b"self.assertEqual(booking.validate(receipt, now, True), 4*3600-121)"
NEW_WINDOW_HOURS = b"self.assertEqual(booking.validate(receipt, now, True), (booking.LATEST_END_MS-booking.START_MS)//1000-121)"
OLD_EXTENSION_TEST_START = b"    def test_contiguous_extension_clamps_to_user_end_and_rejects_invalid(self):\n"
NEXT_TEST_START = b"    def test_numeric_archive_preserves_original_identity_without_numeric_restart(self):\n"
NEW_EXTENSION_TEST = (
    b"    def test_window_has_no_extension_ticket(self):\n"
    b"        now = booking.START_MS + 1000\n"
    b"        receipt = self.receipt(now)\n"
    b"        receipt['extension'] = dict(receipt['booking'], id='bk-20261028T0000-ffffffff',\n"
    b"            start_ms=booking.LATEST_END_MS, end_ms=booking.LATEST_END_MS+3600000)\n"
    b"        with self.assertRaises(RuntimeError): booking.validate(receipt, now, True)\n"
    b"        receipt['extension']['id'] = booking.EXTENSION_ID\n"
    b"        with self.assertRaises(RuntimeError): booking.validate(receipt, now, True)\n"
    b"        del receipt['extension']\n"
    b"        self.assertEqual(booking.validate(receipt, now, True), (booking.LATEST_END_MS-booking.START_MS)//1000-121)\n"
    b"\n")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rows(paths):
    return [{"path": p, "bytes": len((NEW / p).read_bytes()), "sha256": sha((NEW / p).read_bytes())} for p in paths]


def main():
    global NEW
    booking_id, start_ms, end_ms = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    if len(sys.argv) > 4:  # dry run into another directory
        NEW = Path(sys.argv[4]).resolve()
    if not re.fullmatch(r"bk-\d{8}T\d{4}-[0-9a-f]{8}", booking_id) or not start_ms < end_ms:
        raise SystemExit("bad booking arguments")
    deployment = json.loads((OLD / "configs" / "deployment-files.json").read_bytes())
    for row in deployment:
        data = (OLD / row["path"]).read_bytes()
        if len(data) != row["bytes"] or sha(data) != row["sha256"]:
            raise SystemExit("frozen 13:00 window differs from its deployment manifest: " + row["path"])
    if NEW.exists():
        raise SystemExit("new window directory exists; refusing to overwrite")
    NEW.mkdir()
    for member in ("scripts", "tools", "configs", "patches"):
        shutil.copytree(OLD / member, NEW / member)
    changed = set()
    for path in sorted(p for p in NEW.rglob("*") if p.is_file() and p.parent.name in ("scripts", "tools")):
        data = original = path.read_bytes()
        for old, new in REPLACE:
            data = data.replace(old, new)
        if data != original:
            path.write_bytes(data)
            changed.add(path.relative_to(NEW).as_posix())
    window = NEW / "scripts" / "booking_window.py"
    data = window.read_bytes()
    if data.count(OLD_BOOKING) != 1:
        raise SystemExit("booking constants block not found exactly once")
    new_booking = (
        f"START_MS = {start_ms}  # Booking start (Asia/Shanghai 2026-10-28 23:00)\n"
        f"LATEST_END_MS = {end_ms}  # Booking end; the window ends here\n"
        f"AUTHORIZED_EXTENDED_END_MS = LATEST_END_MS  # No extension ticket in this window.\n"
        f"EXTENSION_ID = None\n"
        f"CLEANUP_SECONDS = 120\n"
        f"BOOKING_ID = '{booking_id}'\n").encode()
    data = data.replace(OLD_BOOKING, new_booking)
    if data.count(EXTENSION_GUARD_OLD) != 1:
        raise SystemExit("extension block not found exactly once")
    window.write_bytes(data.replace(EXTENSION_GUARD_OLD, EXTENSION_GUARD_NEW))
    changed.add("scripts/booking_window.py")
    test = NEW / "scripts" / "test_window_booking.py"
    data = test.read_bytes()
    start, end = data.find(OLD_EXTENSION_TEST_START), data.find(NEXT_TEST_START)
    if (data.count(OLD_EXTENSION_TEST_START) != 1 or data.count(OLD_FOUR_HOURS) != 1 or not 0 < start < end):
        raise SystemExit("window test anchors not found exactly once")
    data = data[:start] + NEW_EXTENSION_TEST + data[end:]
    test.write_bytes(data.replace(OLD_FOUR_HOURS, NEW_WINDOW_HOURS))
    changed.add("scripts/test_window_booking.py")
    old_sources = json.loads((OLD / "configs" / "runtime-extension-source-manifest.json").read_bytes())
    source_manifest = NEW / "configs" / "runtime-extension-source-manifest.json"
    source_manifest.write_bytes((json.dumps(rows([r["path"] for r in old_sources]), indent=2) + "\n").encode())
    deploy_manifest = NEW / "configs" / "deployment-files.json"
    deploy_manifest.write_bytes((json.dumps(rows([r["path"] for r in deployment]), indent=2) + "\n").encode())
    tool = NEW / "tools" / "deploy_commit_cpu.py"
    data = tool.read_bytes()
    for name, old_manifest, new_manifest in (
            ("SOURCE_SHA", OLD / "configs" / "runtime-extension-source-manifest.json", source_manifest),
            ("DEPLOYMENT_SHA", OLD / "configs" / "deployment-files.json", deploy_manifest)):
        old_line = f"{name}='{sha(old_manifest.read_bytes())}'".encode()
        if data.count(old_line) != 1:
            raise SystemExit(f"{name} pin not found exactly once")
        data = data.replace(old_line, f"{name}='{sha(new_manifest.read_bytes())}'".encode())
    tool.write_bytes(data)
    print(json.dumps({
        "changed_files": sorted(changed | {"tools/deploy_commit_cpu.py", "configs/runtime-extension-source-manifest.json",
                                           "configs/deployment-files.json"}),
        "source_manifest_sha256": sha(source_manifest.read_bytes()),
        "deployment_files_sha256": sha(deploy_manifest.read_bytes()),
    }, indent=2))


if __name__ == "__main__":
    main()
