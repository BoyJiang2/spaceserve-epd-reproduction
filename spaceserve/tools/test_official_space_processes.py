"""CPU-only Linux process tests; no torch, vLLM, Ray or GPU interfaces."""
import os
import json
from pathlib import Path
import signal
import subprocess
import sys
import time
import unittest
from unittest import mock
import uuid

import official_space_processes as owned


class ProcessTests(unittest.TestCase):
    def setUp(self):
        self.children = []
        self.state = {'uid': os.getuid(), 'root': '/local/boyjiang/SpaceServe-official',
                      'runid': '/tmp/space-cpu-test:' + uuid.uuid4().hex,
                      'boot': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                      'min_start_ticks': int(float(Path('/proc/uptime').read_text().split()[0]) * os.sysconf('SC_CLK_TCK')),
                      'known': {}}

    def tearDown(self):
        for child in self.children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)
            child.stdout.close()

    def child(self, identity=True, ignore_term=False):
        env = dict(os.environ, EXP_ROOT=self.state['root'],
                   REPRO_RUN_ID=self.state['runid'] if identity else 'foreign-cpu-fixture')
        source = 'import signal,time; '
        if ignore_term:
            source += 'signal.signal(signal.SIGTERM, signal.SIG_IGN); '
        source += 'print("ready",flush=True); time.sleep(300)'
        child = subprocess.Popen([sys.executable, '-I', '-S', '-B', '-c', source],
                                 env=env, stdout=subprocess.PIPE, text=True)
        self.children.append(child)
        self.assertEqual(child.stdout.readline().strip(), 'ready')
        return child

    def test_real_term_preserves_foreign_process(self):
        child, foreign = self.child(), self.child(identity=False)
        observed = owned.observe(self.state)
        self.assertEqual([x['pid'] for x in observed], [child.pid])
        self.assertEqual(owned.stop(self.state), [])
        child.wait(timeout=5)
        self.assertEqual(child.returncode, -signal.SIGTERM)
        self.assertIsNone(foreign.poll())

    def test_real_kill_after_ignored_term(self):
        child = self.child(ignore_term=True)
        start = time.monotonic()
        self.assertEqual(owned.stop(self.state), [])
        child.wait(timeout=5)
        self.assertGreaterEqual(time.monotonic() - start, 8)
        self.assertEqual(child.returncode, -signal.SIGKILL)

    def test_refuses_wrong_birth_and_token(self):
        child = self.child()
        saved = owned.observe(self.state)[0]
        wrong = dict(saved, start_ticks=str(int(saved['start_ticks']) + 1))
        with self.assertRaises(AssertionError):
            owned.send(wrong, self.state, signal.SIGTERM)
        wrong_state = dict(self.state, runid='different-token')
        with self.assertRaises(AssertionError):
            owned.send(saved, wrong_state, signal.SIGTERM)
        self.assertIsNone(child.poll())

    def test_wrong_boot_and_lost_identity_fail(self):
        self.child()
        saved = owned.observe(self.state)
        with self.assertRaises(AssertionError):
            owned.observe(dict(self.state, boot='wrong-boot'))
        with self.assertRaises(AssertionError):
            owned.observe(dict(self.state, runid='wrong-token'))
        self.assertTrue(saved)

    def test_unreadable_known_live_process_is_not_signalled(self):
        child = self.child()
        owned.observe(self.state)
        original = owned.process

        def denied(pid):
            if pid == child.pid:
                raise PermissionError('simulated live /proc denial')
            return original(pid)

        with mock.patch.object(owned, 'process', side_effect=denied):
            with self.assertRaises(RuntimeError):
                owned.stop(self.state)
        self.assertIsNone(child.poll())

    def test_process_older_than_run_is_refused(self):
        child = self.child()
        item = owned.process(child.pid)
        later_state = dict(self.state, min_start_ticks=int(item['start_ticks']) + 1)
        self.assertFalse(owned.matches(item, later_state))

    def test_helper_inheriting_run_tags_survives_stop(self):
        source = ('import runpy,json,sys; m=runpy.run_path(sys.argv[1]); '
                  'm["stop"](json.loads(sys.argv[2])); print("survived")')
        env = dict(os.environ, EXP_ROOT=self.state['root'], REPRO_RUN_ID=self.state['runid'])
        result = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', source,
                                 owned.__file__, json.dumps(self.state)],
                                env=env, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'survived')

    def test_optimized_interpreter_is_refused_before_operations(self):
        result = subprocess.run([sys.executable, '-I', '-S', '-B', '-O', '-c',
                                 'import runpy,sys; runpy.run_path(sys.argv[1])',
                                 owned.__file__], capture_output=True, text=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('optimized Python', result.stderr)


if __name__ == '__main__':
    unittest.main()
