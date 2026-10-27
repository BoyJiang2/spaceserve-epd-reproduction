"""New edit-only CPU runner tests; not executed locally."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest
import asyncio
import subprocess
import os
import json
import signal
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import cpu_target_runner as runner
TEST_TMP = Path(os.environ.get("EPD_CPU_TEST_TMP", ROOT / "tests")).resolve()


class ConditionalCPUWindow(unittest.TestCase):
    def fixture(self):
        now = runner.POLICY["earliest_ms"] + 60000
        scope = {"policy": dict(runner.POLICY), "boot_id": "CPU-MOCK-boot",
            "booking_id": "CPU-MOCK-booking", "booking_user": "CPU-MOCK-user",
            "prior_control_domains": ["CPU-MOCK-a", "CPU-MOCK-b", "CPU-MOCK-c", "CPU-MOCK-d"]}
        booking = {"origin": "gputime_read_only_api", "read_only": True, "observed_ms": now,
            "resources": [{"id": "h20/qjh001", "active": True}],
            "bookings": [{"id": scope["booking_id"], "kind": "cpu", "node": "qjh001",
                "resource_id": "h20/qjh001", "user": scope["booking_user"],
                "start_ms": runner.POLICY["booking_start_ms"], "end_ms": runner.POLICY["booking_end_ms"]}]}
        handoff = {"origin": "actual_read_only_host_probe", "host": "qjh001", "boot_id": scope["boot_id"],
            "observed_ms": now, "active_control_domains": [], "cpu50_conflicting_pids": []}
        releases = {name: {"domain": name, "host": "qjh001", "remaining_owned_pids": [],
            "controller_state": "released", "boot_id": scope["boot_id"], "released_ms": runner.POLICY["earliest_ms"]} for name in scope["prior_control_domains"]}
        return scope, booking, handoff, releases, now

    def test_exact_conditional_cpu_window_and_completed_handoff(self):
        runner.validate_observations(*self.fixture())

    def test_gpu_ticket_or_unreleased_control_or_cpu50_conflict_rejected(self):
        for mode in ("gpu_ticket", "old_control", "new_takeover", "cpu_conflict"):
            with self.subTest(mode=mode):
                scope, booking, handoff, releases, now = self.fixture()
                if mode == "gpu_ticket": booking["bookings"][0]["kind"] = "gpu"
                elif mode == "old_control": releases[scope["prior_control_domains"][0]]["remaining_owned_pids"] = [123]
                elif mode == "new_takeover": handoff["active_control_domains"] = ["foreign"]
                else: handoff["cpu50_conflicting_pids"] = [456]
                with self.assertRaises(ValueError):
                    runner.validate_observations(scope, booking, handoff, releases, now)

    def test_stale_or_before_18_or_too_late_for_19_cleanup_rejected(self):
        scope, booking, handoff, releases, now = self.fixture()
        for time_ms in (runner.POLICY["earliest_ms"] - 1, runner.POLICY["safe_end_ms"] - 329999):
            with self.assertRaises(ValueError):
                runner.validate_observations(scope, booking, handoff, releases, time_ms)
        handoff["observed_ms"] = now - 300001
        with self.assertRaises(ValueError):
            runner.validate_observations(scope, booking, handoff, releases, now)

    def test_gpu_import_finder_refuses_actual_gpu_libraries(self):
        finder = runner.NoGPU()
        for name in ("torch", "pynvml", "ray", "vllm", "nvidia.cuda"):
            with self.assertRaises(ImportError): finder.find_spec(name)

    def test_real_posix_asyncio_selfpipe_is_allowed(self):
        async def one():
            await asyncio.sleep(.001)
            return "native-event-loop"
        self.assertEqual(asyncio.run(one()), "native-event-loop")

    def test_reviewed_git_and_owned_python_posix_helpers_are_allowed(self):
        git = subprocess.run(["git", "--version"], cwd=ROOT, capture_output=True, text=True, check=True)
        self.assertTrue(git.stdout.startswith("git version"))
        child = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", "import os; print(os.getpid())"],
                               cwd=ROOT, capture_output=True, text=True, check=True)
        self.assertGreater(int(child.stdout.strip()), 0)


class ParentExitPOSIX(unittest.TestCase):
    """Real owned Python children/signals; source only, UNEXECUTED in v7."""
    def lifecycle(self, mode):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as directory:
            case = Path(directory).resolve()
            assert case.is_relative_to(TEST_TMP)
            worker = r'''
import json,os,subprocess,sys,time
from pathlib import Path
root,case=map(Path,sys.argv[1:3]);sys.path.insert(0,str(root))
import cpu_target_runner as r
helper=subprocess.Popen([sys.executable,"-I","-S","-B","-c","import time; time.sleep(120)"],cwd=root)
entry={"run_id":os.environ["EPD_CPU_RUN_ID"],"identity":r.process_identity(helper.pid),"argv":["CPU-OWNED-SLEEP"]}
output=root/"runtime"/os.environ["EPD_CPU_RUN_ID"]
with (output/"helper-pids.jsonl").open("a") as f:f.write(json.dumps(entry)+"\n")
(case/"helper-ready.json").write_text(json.dumps(entry))
time.sleep(120)
'''
            harness = r'''
import json,os,sys,time
from pathlib import Path
root,case=map(Path,sys.argv[1:3]);mode=sys.argv[3];sys.path.insert(0,str(root))
import cpu_target_runner as r
path=case/"permit.json";path.write_text("{}")
permit={"_verified_commit":"a"*40,"_verified_permit_sha256":r.sha(path)}
r.preflight=lambda p:(permit,root,{"cpu_target_runner.py":r.sha(root/"cpu_target_runner.py")})
original=r.subprocess.Popen
worker=(case/"worker-code.txt").read_text()
def spawn(argv,*args,**kwargs):
    process=original([sys.executable,"-I","-S","-B","-c",worker,str(root),str(case)],*args,**kwargs)
    end=time.monotonic()+5
    while not (case/"helper-ready.json").exists() and time.monotonic()<end:time.sleep(.01)
    (case/"ready.json").write_text(json.dumps({"parent":r.process_identity(os.getpid()),"child":r.process_identity(process.pid),"run_id":kwargs["env"]["EPD_CPU_RUN_ID"]}))
    if mode.endswith("_during_start"):
        (case/"startup-window-open").write_text("forked; Popen wrapper has not returned")
        deadline=time.monotonic()+5
        while not (case/"resume-startup").exists() and time.monotonic()<deadline:time.sleep(.01)
    if mode=="wait_error":
        def fail(timeout=None):raise OSError("injected_wait_failure")
        process.wait=fail
    return process
r.subprocess.Popen=spawn
sys.exit(r.run(path))
'''
            (case / "worker-code.txt").write_text(worker, encoding="utf-8")
            parent = subprocess.Popen([sys.executable, "-I", "-S", "-B", "-c", harness, str(ROOT), str(case), mode], cwd=ROOT)
            parent_id = runner.process_identity(parent.pid)
            try:
                ready_path = case / "ready.json"
                deadline = time.monotonic() + 8
                while not ready_path.exists() and time.monotonic() < deadline:
                    if parent.poll() is not None: break
                    time.sleep(.02)
                self.assertTrue(ready_path.exists(), "owned POSIX harness did not become ready")
                ready = json.loads(ready_path.read_bytes())
                if mode != "wait_error":
                    self.assertEqual(runner.process_identity(parent.pid), parent_id)
                    if mode.endswith("_during_start"):
                        window = case / "startup-window-open"
                        while not window.exists() and time.monotonic() < deadline: time.sleep(.01)
                        self.assertTrue(window.exists(), "deterministic pre-return fork window missing")
                    os.kill(parent.pid, signal.SIGTERM if mode.startswith("term") else signal.SIGINT)
                    if mode.endswith("_during_start"):
                        time.sleep(.05)
                        self.assertIsNone(parent.poll(), "startup handler must defer rather than throw before Popen returns")
                        self.assertEqual(runner.process_identity(ready["child"]["pid"]), ready["child"])
                        (case / "resume-startup").write_text("return the Popen object and bind identity", encoding="utf-8")
                parent.wait(timeout=40)
                receipt = json.loads((ROOT / "runtime" / ready["run_id"] / "CPU-receipt.json").read_bytes())
                expected = 1 if mode == "wait_error" else 143 if mode.startswith("term") else 130
                self.assertEqual(receipt["exit_code"], expected)
                self.assertTrue(receipt["cleanup_confirmed"])
                self.assertEqual(receipt["parent_nice"], 10)
                self.assertEqual(receipt["child_nice"], 10)
                self.assertEqual(receipt["commit"], "a"*40)
                self.assertTrue(receipt["command"])
                if mode.endswith("_during_start"):
                    self.assertTrue(receipt["child_object_obtained"])
                    self.assertEqual(receipt["startup_signal_deferred"], signal.SIGTERM if mode.startswith("term") else signal.SIGINT)
                self.assertFalse(receipt["SIGKILL_parent_guarantee"])
                self.assertTrue(all(row["state"] in ("gone","exited","already_exited") for row in receipt["cleanup"]))
            finally:
                if parent.poll() is None:
                    self.assertEqual(runner.process_identity(parent.pid), parent_id)
                    os.kill(parent.pid,signal.SIGTERM)
                    parent.wait(timeout=40)

    def test_parent_term_always_cleans_owned_child_and_helper(self): self.lifecycle("term")
    def test_parent_int_always_cleans_owned_child_and_helper(self): self.lifecycle("int")
    def test_wait_exception_always_cleans_owned_child_and_helper(self): self.lifecycle("wait_error")
    def test_term_after_fork_before_Popen_return_is_deferred_then_cleaned(self): self.lifecycle("term_during_start")
    def test_int_after_fork_before_Popen_return_is_deferred_then_cleaned(self): self.lifecycle("int_during_start")


if __name__ == "__main__":
    unittest.main(verbosity=2)
