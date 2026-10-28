"""Pure CPU booking/path rejection contracts, no remote actions or target writes."""
import copy
from pathlib import Path
import unittest
import io
import os
import json
import subprocess
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parent))
from unittest.mock import patch
import migrate_code_cpu as migration


class MigrationTests(unittest.TestCase):
    def snapshot(self,now):
        return {'origin':'gputime_read_only_api','read_only':True,'observed_ms':now,
            'resources':[{'id':'h20/qjh003','active':True}],
            'bookings':[{'id':migration.TICKET,'kind':'cpu','node':'qjh003','resource_id':'h20/qjh003',
                'user':'boyjiang','start_ms':migration.START,'end_ms':migration.END}]}

    def test_exact_cpu_window_accepts_only_the_real_ticket_fields(self):
        now=migration.START+1000
        self.assertEqual(migration.booking(self.snapshot(now),now)['id'],migration.TICKET)
        for key,value in [('kind','gpu'),('user','OTHER'),('node','qjh000'),('id','OLD'),('end_ms',migration.END+1)]:
            data=self.snapshot(now);data['bookings'][0][key]=value
            with self.assertRaises(ValueError):migration.booking(data,now)

    def test_stale_duplicate_future_and_incomplete_unit_refused(self):
        now=migration.START+400000
        for data in [self.snapshot(now-300001),self.snapshot(now+1),{**self.snapshot(now),'read_only':False},
                     {**self.snapshot(now),'resources':[]}]:
            with self.assertRaises(ValueError):migration.booking(data,now)
        data=self.snapshot(now);data['bookings'].append(copy.deepcopy(data['bookings'][0]))
        with self.assertRaises(ValueError):migration.booking(data,now)
        for current in (migration.START-1,migration.END-1020000+1):
            with self.assertRaises(ValueError):migration.booking(self.snapshot(current),current)

    def test_linked_parent_and_wrong_actual_host_refused_before_operations(self):
        target=Path('/local/boyjiang/spaceserve/staging')
        with patch.object(Path,'is_symlink',lambda path:path==Path('/local/boyjiang')):
            with self.assertRaises(ValueError):migration.real_ancestry(target)
        with patch.object(migration.socket,'gethostname',return_value='WRONG'):
            with self.assertRaises(ValueError):migration.validate_executor()

    def test_failed_command_preserves_original_diagnostics_and_status(self):
        log=io.BytesIO()
        with self.assertRaises(subprocess.CalledProcessError):
            migration.command_output([sys.executable,'-I','-S','-B','-c',
                'print("CPU-MOCK original diagnostic",flush=True);raise SystemExit(7)'],log,2,time.monotonic()+10)
        raw=log.getvalue()
        self.assertIn(b'CPU-MOCK original diagnostic',raw)
        self.assertEqual(json.loads(raw.splitlines()[-1])['exit_code'],7)

    def test_timeout_releases_both_actual_owned_child_and_helper(self):
        with tempfile.TemporaryDirectory() as directory:
            marker=Path(directory)/'pids.json'
            code=r"""
import json,os,signal,subprocess,sys,time
from pathlib import Path
child=subprocess.Popen([sys.executable,'-I','-S','-B','-c','import time;time.sleep(60)'])
Path(sys.argv[1]).write_text(json.dumps([os.getpid(),child.pid]))
print('CPU-MOCK before timeout',flush=True)
def stop(*args):raise SystemExit(23)
signal.signal(signal.SIGTERM,stop)
try:
    while True:time.sleep(.02)
finally:
    if child.poll() is None:child.terminate()
    child.wait(timeout=2)
    print('CPU-MOCK helper reaped',flush=True)
"""
            log=io.BytesIO()
            with self.assertRaises(subprocess.TimeoutExpired):
                migration.command_output([sys.executable,'-I','-S','-B','-c',code,str(marker)],log,.5,time.monotonic()+10)
            self.assertTrue(marker.exists())
            for pid in json.loads(marker.read_text()):self.assertFalse(Path('/proc',str(pid)).exists())
            self.assertIn(b'CPU-MOCK before timeout',log.getvalue())
            self.assertNotIn(b'release_unconfirmed',log.getvalue())


if __name__=='__main__':unittest.main()
