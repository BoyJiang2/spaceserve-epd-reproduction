"""CPU-only delayed gzip-footer fixture: an API acknowledgement is insufficient."""
import gzip
from pathlib import Path
import tempfile
import threading
import time
import unittest
from wait_for_traces import wait


class ExportTests(unittest.TestCase):
    def test_waits_for_delayed_gzip_footer(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'host_123.1.pt.trace.json.gz'
            source = gzip.open(path, 'wb')
            source.write(b'{"traceEvents":[]}')
            source.flush()
            def finish():
                time.sleep(.15)
                source.close()
            thread = threading.Thread(target=finish)
            thread.start()
            try:
                begin = time.monotonic()
                result = wait(Path(directory), {123}, timeout=2, interval=.02)
                self.assertGreater(time.monotonic() - begin, .1)
                self.assertTrue(result[123]['gzip_complete_crc_checked'])
            finally:
                thread.join()

    def test_missing_worker_and_duplicate_exports_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, 'incomplete'):
                wait(Path(directory), {123}, timeout=.05, interval=.01)
            for suffix in [1, 2]:
                with gzip.open(Path(directory) / f'host_123.{suffix}.pt.trace.json.gz', 'wb') as stream:
                    stream.write(b'{}')
            with self.assertRaisesRegex(RuntimeError, 'multiple'):
                wait(Path(directory), {123}, timeout=.1, interval=.01)


if __name__ == '__main__':
    unittest.main()
