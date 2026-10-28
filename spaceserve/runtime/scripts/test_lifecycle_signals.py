"""Actual POSIX signals must enter finally without a GPU or model import."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import unittest

from resource_guard import RunInterrupted, run_signals


class SignalTests(unittest.TestCase):
    @unittest.skipUnless(hasattr(signal,'SIGALRM'),'requires POSIX SIGALRM')
    def test_short_alarm_executes_finally(self):
        events=[]
        with self.assertRaises(RunInterrupted):
            with run_signals():
                try:
                    signal.setitimer(signal.ITIMER_REAL,.02)
                    signal.pause()
                finally:
                    events.append('finally')
                    signal.setitimer(signal.ITIMER_REAL,0)
        self.assertEqual(events,['finally'])

    @unittest.skipUnless(os.name=='posix','requires POSIX SIGTERM')
    def test_actual_sigterm_child_executes_finally(self):
        code='''import json,os,signal
from resource_guard import RunInterrupted,run_signals
events=[]
try:
    with run_signals():
        try: os.kill(os.getpid(),signal.SIGTERM)
        finally: events.append("finally")
except RunInterrupted: events.append("interrupted")
print(json.dumps(events))
'''
        result=subprocess.run([sys.executable,'-B','-c',code],cwd=Path(__file__).resolve().parent,
                              text=True,capture_output=True,check=True,timeout=10)
        self.assertEqual(json.loads(result.stdout),['finally','interrupted'])


if __name__=='__main__':
    unittest.main()
