"""Derive the 2026-10-28 window's local helper tools from work/space1300-tools.

Usage: python -X utf8 -I make_space_tools.py <booking_id> <start_ms> <end_ms> [output_dir]

Same mechanical identity changes as make_space_window.py (root, batch, prefix, status file, booking
constants without an extension ticket). The one-off 13:00 failure-preservation tool and the local
copy of the deploy tool (canonical version lives in the repository) are not carried over.
"""
import re
import shutil
import sys
from pathlib import Path

WORK = Path(__file__).resolve().parents[2]
OLD = WORK / "space1300-tools"
NEW = WORK / "space2300-tools"
SKIP = {"save_numeric_review.py", "preserve_zero_request_failure.py", "test_preserve_failure.py", "deploy_commit_cpu.py",
        "test_deploy_commit_cpu.py"}
REPLACE = [
    (b"/var/tmp/boyjiang-spaceserve-window-20261027-1300", b"/var/tmp/boyjiang-spaceserve-window-20261028-2300"),
    (b"outputs/spaceserve-window-20261027-1300", b"outputs/spaceserve-window-20261028-2300"),
    (b"spaceserve/code/h20-window-20261027", b"spaceserve/code/h20-window-20261028"),
    (b"outputs/next-window-20261027/status.json", b"outputs/next-window-20261028/status.json"),
]
OLD_CONSTANTS = (b"BOOKING_ID = 'bk-20261027T0137-bcf3dd23'\n"
                 b"START = 1793077200000\n"
                 b"END = 1793091600000\n"
                 b"EXTENSION_ID = 'bk-20261027T0532-efb16fde'\n"
                 b"AUTHORIZED_END = 1793095200000\n")
OLD_EXTENSIONS = b"    extensions = [b for b in snapshot['bookings'] if b.get('id') == EXTENSION_ID]\n"
NEW_EXTENSIONS = (b"    extensions = [b for b in snapshot['bookings']\n"
                  b"                  if EXTENSION_ID is not None and b.get('id') == EXTENSION_ID]\n")
OLD_TEST_START = b"    def test_extension_is_actual_separate_record_clamped_and_fail_closed(self):\n"
OLD_TEST_END = b"\n\nif __name__ == '__main__':\n"
NEW_TEST = (
    b"    def test_window_without_extension_ignores_other_records_and_fails_closed(self):\n"
    b"        state=self.snapshot()\n"
    b"        other=dict(state['bookings'][0],id='bk-20261028T0000-ffffffff',\n"
    b"                   start_ms=refresh.END,end_ms=refresh.END+3600000)\n"
    b"        state['bookings'].append(other)\n"
    b"        result=refresh.select_booking(state,refresh.START+1000)\n"
    b"        self.assertNotIn('extension',result)\n"
    b"        self.assertEqual(result['authorized_effective_end_ms'],refresh.END)\n"
    b"        with self.assertRaises(RuntimeError): refresh.select_booking(state,refresh.END+1000)\n"
    b"        state = self.snapshot();state['resources'][0]['active'] = False\n"
    b"        with self.assertRaises(RuntimeError): refresh.select_booking(state, refresh.START+1000)\n")


def main():
    global NEW
    booking_id, start_ms, end_ms = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    if len(sys.argv) > 4:
        NEW = Path(sys.argv[4]).resolve()
    if not re.fullmatch(r"bk-\d{8}T\d{4}-[0-9a-f]{8}", booking_id) or not start_ms < end_ms:
        raise SystemExit("bad booking arguments")
    if NEW.exists():
        raise SystemExit("output directory exists; refusing to overwrite")
    NEW.mkdir()
    changed = []
    for source in sorted(OLD.glob("*.py")):
        if source.name in SKIP:
            continue
        data = original = source.read_bytes()
        for old, new in REPLACE:
            data = data.replace(old, new)
        if source.name == "refresh_booking.py":
            if data.count(OLD_CONSTANTS) != 1 or data.count(OLD_EXTENSIONS) != 1:
                raise SystemExit("refresh_booking anchors not found exactly once")
            data = data.replace(OLD_CONSTANTS, (
                f"BOOKING_ID = '{booking_id}'\nSTART = {start_ms}\nEND = {end_ms}\n"
                f"EXTENSION_ID = None  # No extension ticket in this window.\nAUTHORIZED_END = END\n").encode())
            data = data.replace(OLD_EXTENSIONS, NEW_EXTENSIONS)
        if source.name == "test_refresh_booking.py":
            start, end = data.find(OLD_TEST_START), data.find(OLD_TEST_END)
            if data.count(OLD_TEST_START) != 1 or not 0 < start < end:
                raise SystemExit("refresh test anchors not found exactly once")
            data = data[:start] + NEW_TEST + data[end:]
        (NEW / source.name).write_bytes(data)
        if data != original:
            changed.append(source.name)
    print("written:", sorted(p.name for p in NEW.iterdir()))
    print("changed:", changed)


if __name__ == "__main__":
    main()
