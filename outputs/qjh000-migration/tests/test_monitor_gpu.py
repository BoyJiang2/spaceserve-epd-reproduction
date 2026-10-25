"""CPU-only ownership and sampling regressions; never initialize NVML."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import psutil

sys.modules['pynvml'] = SimpleNamespace()
spec = importlib.util.spec_from_file_location('monitor_gpu', Path(__file__).resolve().parents[1] / 'scripts/monitor_gpu.py')
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


class OwnershipTests(unittest.TestCase):
    def process(self, uid=None, name='python', parents=(), pipe=None):
        return SimpleNamespace(uids=lambda: SimpleNamespace(real=os.getuid() if uid is None else uid),
                               name=lambda: name, parents=lambda: list(parents),
                               environ=lambda: {'CUDA_MPS_PIPE_DIRECTORY': pipe})

    def test_private_mps_only_and_uid(self):
        with patch.dict(os.environ, {'CUDA_MPS_PIPE_DIRECTORY': '/private/test'}):
            for uid, name, pipe, expected in [(os.getuid(), 'nvidia-cuda-mps-server', '/private/test', True),
                                               (os.getuid(), 'nvidia-cuda-mps-server', '/other', False),
                                               (os.getuid(), 'python', '/private/test', False),
                                               (os.getuid() + 1, 'nvidia-cuda-mps-server', '/private/test', False)]:
                with self.subTest(uid=uid, name=name, pipe=pipe), patch.object(monitor.psutil, 'Process', return_value=self.process(uid, name, pipe=pipe)):
                    self.assertEqual(monitor.is_owned(123, []), expected)

    def test_gone_or_unreadable_process_is_foreign(self):
        for error in [psutil.NoSuchProcess(123), psutil.AccessDenied(123)]:
            with patch.object(monitor.psutil, 'Process', side_effect=error):
                self.assertFalse(monitor.is_owned(123, []))

    def test_reused_root_identity_is_rejected(self):
        root = SimpleNamespace(is_running=lambda: False)
        candidate = self.process(parents=[root])
        with patch.object(monitor.psutil, 'Process', return_value=candidate), patch.dict(os.environ, {}, clear=True):
            self.assertFalse(monitor.is_owned(123, [root]))

    def test_live_root_child_grandchild_and_unrelated(self):
        script = 'import subprocess,sys,time; p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"]); print(p.pid,flush=True); time.sleep(30)'
        child = subprocess.Popen([sys.executable, '-c', script], stdout=subprocess.PIPE, text=True)
        grandchild = psutil.Process(int(child.stdout.readline()))
        root = psutil.Process(child.pid)
        try:
            self.assertTrue(monitor.is_owned(root.pid, [root]))
            self.assertTrue(monitor.is_owned(grandchild.pid, [root]))
            self.assertFalse(monitor.is_owned(os.getpid(), [root]))
        finally:
            grandchild.terminate()
            child.terminate()
            child.wait(timeout=10)
            child.stdout.close()

    def test_new_gpu_pid_is_classified_each_sample(self):
        root = psutil.Process(os.getpid())
        candidate = SimpleNamespace(pid=root.pid, usedGpuMemory=100)
        foreign = SimpleNamespace(pid=99999999, usedGpuMemory=25)
        fake = SimpleNamespace(nvmlDeviceGetComputeRunningProcesses=lambda handle: [candidate] if count[0] == 0 else [candidate, foreign],
                               nvmlDeviceGetMemoryInfo=lambda handle: SimpleNamespace(total=1000, used=200),
                               nvmlDeviceGetClockInfo=lambda *args: 100, nvmlDeviceGetTemperature=lambda *args: 30,
                               nvmlDeviceGetUtilizationRates=lambda handle: SimpleNamespace(gpu=5), NVML_CLOCK_SM=0, NVML_TEMPERATURE_GPU=0)
        count = [0]
        def advance(_):
            count[0] += 1
            if count[0] == 2:
                monitor.running = False
        monitor.running = True
        output = io.StringIO()
        with patch.object(monitor, 'nv', fake), patch.object(monitor.time, 'sleep', side_effect=advance), contextlib.redirect_stdout(output):
            monitor.sample({0: None}, [root])
        samples = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(samples[0]['gpus'][0]['foreign_compute_pids'], [])
        self.assertEqual(samples[1]['gpus'][0]['foreign_compute_pids'], [foreign.pid])
        self.assertEqual(samples[1]['gpus'][0]['owned_process_sum_bytes'], 100)
        self.assertEqual(samples[1]['gpus'][0]['owned_processes'], [{'pid': root.pid, 'used_bytes': 100}])


if __name__ == '__main__':
    unittest.main(verbosity=2)
