"""Real CPU child signals must preserve finally and its actual exit receipt."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch,Mock


class LauncherTests(unittest.TestCase):
    def test_identity_failure_cannot_signal_again_in_exception_cleanup(self):
        try:
            import numeric_launcher as launcher
        except ModuleNotFoundError as error:
            if error.name=='psutil':
                self.skipTest('requires copied target psutil')
            raise
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            root=Path(directory)
            (root/'evidence').mkdir()
            child=Mock(pid=123)
            child.poll.return_value=None
            actual=Mock()
            # Initial binding succeeds; the next verification sees a recycled identity.
            actual.create_time.side_effect=[10,11]
            actual.uids.return_value=Mock(real=0)
            parent=Mock()
            parent.create_time.return_value=3
            with patch.object(launcher.subprocess,'Popen',return_value=child), \
                 patch.object(launcher.psutil,'Process',side_effect=lambda *args: actual if args else parent), \
                 patch.object(launcher.os,'getuid',return_value=0,create=True), \
                 patch.object(launcher.time,'sleep',side_effect=RuntimeError('injected wrapper failure')):
                with self.assertRaisesRegex(RuntimeError,'injected wrapper'):
                    launcher.launch(['CPU fixture'],root)
            child.terminate.assert_not_called()
            child.wait.assert_not_called()
            state=json.loads((root/'evidence/numeric-exit.json').read_text())
            self.assertIn('cleanup_identity_unconfirmed',state)

    @unittest.skipUnless(os.name=='posix','requires actual POSIX SIGINT/TERM')
    def test_signal_is_forwarded_without_killing_child_finally(self):
        for number in (signal.SIGINT,signal.SIGTERM):
            with self.subTest(signal=number),tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
                root=Path(directory)
                (root/'evidence').mkdir()
                worker='''import signal,time,sys
from pathlib import Path
running=True
def stop(*args):
    global running
    running=False
signal.signal(signal.SIGTERM,stop)
root=Path(sys.argv[1])
(root/"ready").write_text("ready")
try:
    while running: time.sleep(.02)
finally:
    (root/"finally").write_text("executed")
raise SystemExit(23)
'''
                code='from pathlib import Path; from numeric_launcher import launch; import sys; raise SystemExit(launch([sys.executable,"-B","-c",sys.argv[2],sys.argv[1]],Path(sys.argv[1])))'
                process=subprocess.Popen([sys.executable,'-B','-c',code,str(root),worker],cwd=Path(__file__).resolve().parent)
                try:
                    deadline=time.monotonic()+10
                    while not (root/'ready').exists() and process.poll() is None and time.monotonic()<deadline:
                        time.sleep(.02)
                    self.assertTrue((root/'ready').exists())
                    process.send_signal(number)
                    self.assertEqual(process.wait(timeout=10),23)
                    state=json.loads((root/'evidence/numeric-exit.json').read_text())
                    self.assertEqual(state['exit_code'],23)
                    self.assertTrue(state['forwarded_controlled_SIGTERM'])
                    self.assertEqual((root/'finally').read_text(),'executed')
                finally:
                    if process.poll() is None:
                        process.terminate()
                        process.wait(timeout=10)


if __name__=='__main__':
    unittest.main()
