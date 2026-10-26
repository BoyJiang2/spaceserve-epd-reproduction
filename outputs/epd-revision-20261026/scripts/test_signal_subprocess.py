"""Linux CPU-only regression: real SIGTERM must reach cleanup before child exit."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest


class SignalProcessTest(unittest.TestCase):
    @unittest.skipUnless(os.name == 'posix', 'real target-host SIGTERM semantics require POSIX')
    def test_real_term_runs_finally(self):
        base = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory(dir=base) as temporary:
            folder = Path(temporary).resolve()
            if not folder.is_relative_to(base):
                raise RuntimeError('CPU fixture escaped test directory')
            ready, cleaned = folder / 'ready', folder / 'cleaned'
            code = '''import sys,time
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from resource_guard import run_signals
with run_signals():
    try:
        Path(sys.argv[2]).write_text('ready')
        time.sleep(60)
    finally:
        Path(sys.argv[3]).write_text('cleaned')
'''
            process = subprocess.Popen([sys.executable, '-B', '-c', code, str(base), str(ready), str(cleaned)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                deadline = time.monotonic() + 10
                while not ready.exists():
                    if process.poll() is not None or time.monotonic() > deadline:
                        self.fail('CPU child did not become ready')
                    time.sleep(.05)
                process.send_signal(signal.SIGTERM)
                self.assertNotEqual(process.wait(timeout=10), 0)
                self.assertEqual(cleaned.read_text(), 'cleaned')
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=10)


if __name__ == '__main__':
    unittest.main()
