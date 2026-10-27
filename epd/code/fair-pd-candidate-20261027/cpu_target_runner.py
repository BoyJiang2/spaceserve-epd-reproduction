"""One conditional qjh001 CPU50 test unit. No remote transport or GPU APIs."""
import argparse
import hashlib
import importlib.abc
import json
import os
from pathlib import Path
import re
import resource
import signal
import socket
import subprocess
import sys
import time
import unittest
from datetime import datetime

sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parent
sys.path.insert(0, str(SOURCE))
from admission import bound_bytes, integer
from preflight_guard import digest, require_review

POLICY = {"host": "qjh001", "cpu": 50, "memory_bytes": 1073741824, "wall_seconds": 300,
          "cleanup_seconds": 30, "earliest_ms": int(datetime.fromisoformat("2026-10-27T18:00:00+08:00").timestamp()*1000),
          "safe_end_ms": int(datetime.fromisoformat("2026-10-27T19:00:00+08:00").timestamp()*1000),
          "booking_start_ms": int(datetime.fromisoformat("2026-10-27T15:00:00+08:00").timestamp()*1000),
          "booking_end_ms": int(datetime.fromisoformat("2026-10-27T21:00:00+08:00").timestamp()*1000)}
GPU_MODULES = {"torch", "ray", "vllm", "pynvml", "nvidia", "cupy", "tensorflow", "jax"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def document(owner, desc):
    return json.loads(bound_bytes(owner, desc["path"], desc["sha256"]))


def fresh(value, now_ms):
    integer(value, "actual observation UTC")
    if not 0 <= now_ms - value <= 300000:
        raise ValueError("CPU/handoff observation is not fresh")


def source_hashes(root, manifest):
    result = {}
    for item in manifest["files"]:
        path = (root / item["path"]).resolve()
        if not path.is_relative_to(root) or sha(path) != item["sha256"]:
            raise ValueError("Designated source file SHA differs")
        result[item["path"]] = item["sha256"]
    if "cpu_target_runner.py" not in result or sha(__file__) != result["cpu_target_runner.py"]:
        raise ValueError("Actual CPU runner is not the reviewed source")
    return result


def validate_observations(scope, booking, handoff, releases, now_ms):
    if scope["policy"] != POLICY:
        raise ValueError("Only fixed qjh001 CPU50/1GiB/300+30s is in scope")
    integer(now_ms, "current UTC")
    if now_ms < POLICY["earliest_ms"] or now_ms + 330000 > POLICY["safe_end_ms"]:
        raise ValueError("No complete CPU unit plus cleanup fits after handoff and before 19:00")
    fresh(booking["observed_ms"], now_ms); fresh(handoff["observed_ms"], now_ms)
    if booking.get("origin") != "gputime_read_only_api" or booking.get("read_only") is not True:
        raise ValueError("Actual read-only CPU booking is required; GPU ticket is insufficient")
    own = [row for row in booking["bookings"] if row["id"] == scope["booking_id"]]
    resources = [row for row in booking["resources"] if row["id"] == "h20/qjh001"]
    if len(resources) != 1 or resources[0].get("active") is not True:
        raise ValueError("CPU booking resource is inactive")
    if len(own) != 1 or any(own[0].get(key) != value for key, value in {
            "kind": "cpu", "node": "qjh001", "user": scope["booking_user"],
            "resource_id": "h20/qjh001", "start_ms": POLICY["booking_start_ms"],
            "end_ms": POLICY["booking_end_ms"]}.items()):
        raise ValueError("Exact fresh 15–21 CPU booking does not match")
    if (handoff.get("host") != "qjh001" or handoff.get("boot_id") != scope["boot_id"]
            or handoff.get("origin") != "actual_read_only_host_probe"
            or handoff["active_control_domains"] or handoff["cpu50_conflicting_pids"]):
        raise ValueError("Old control not handed off, new takeover present, or CPU50 conflict")
    if len(scope["prior_control_domains"]) != 4 or set(releases) != set(scope["prior_control_domains"]):
        raise ValueError("All four exact prior control domains must have original release evidence")
    for name, release in releases.items():
        integer(release["released_ms"], "actual domain release UTC")
        if (release["domain"] != name or release["host"] != "qjh001"
                or release["boot_id"] != scope["boot_id"]
                or release["remaining_owned_pids"] or release["controller_state"] != "released"
                or not POLICY["earliest_ms"] <= release["released_ms"] <= handoff["observed_ms"]):
            raise ValueError("A prior control domain has no actual 18:00+ release")


def preflight(path):
    path = Path(path).resolve()
    permit = json.loads(path.read_bytes())
    scope = permit["scope"]
    now_ms = int(time.time()*1000)
    root = Path(scope["source_root"]).resolve()
    if (socket.gethostname() != "qjh001" or os.getuid() != scope["uid"] or root != SOURCE
            or not (root / "runtime").resolve().is_relative_to(root)
            or any(root.is_relative_to(Path(old).resolve()) for old in scope["old_control_roots"])
            or os.sched_getaffinity(0) != {50}):
        raise ValueError("Actual CPU host/UID/source root/CPU50 availability differs")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or os.environ.get("NVIDIA_VISIBLE_DEVICES") != "void":
        raise ValueError("CPU runner itself must have empty CUDA visibility")
    if Path("/proc/sys/kernel/random/boot_id").read_text().strip() != scope["boot_id"]:
        raise ValueError("Actual CPU host boot differs")
    authority = {"reviewer_ids": scope["reviewer_ids"], "executor_id": scope["executor_id"]}
    require_review(path, permit["G1"]["path"], permit["G1"]["sha256"], "G1", digest(scope), authority)
    require_review(path, permit["G2"]["path"], permit["G2"]["sha256"], "G2", digest({
        "scope_sha256": digest(scope), "source_manifest_sha256": permit["source_manifest"]["sha256"]}), authority)
    booking, handoff = document(path, permit["cpu_booking"]), document(path, permit["handoff"])
    releases = {name: document(path, desc) for name, desc in handoff["release_files"].items()}
    validate_observations(scope, booking, handoff, releases, now_ms)
    pushed = document(path, permit["pushed_commit"])
    original = document(path, pushed["raw_remote"])
    commit = pushed["commit"]
    if (not re.fullmatch(r"[a-f0-9]{40}", commit) or original["sha"] != commit
            or original["repository"] != scope["repository"]
            or pushed["source_manifest_sha256"] != permit["source_manifest"]["sha256"]):
        raise ValueError("Actual designated remote commit proof differs")
    for command, expected in ((["git", "-C", str(root), "rev-parse", "HEAD"], commit),
                               (["git", "-C", str(root), "remote", "get-url", "origin"], scope["repository"]),
                               (["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"], "")):
        if subprocess.check_output(command, text=True).strip() != expected:
            raise ValueError("Actual CPU checkout commit/origin/tracked source changed")
    permit["_verified_commit"] = commit
    permit["_verified_permit_sha256"] = sha(path)
    return permit, root, source_hashes(root, document(path, permit["source_manifest"]))


def process_identity(pid):
    status = Path(f"/proc/{pid}/status").read_text()
    if any(int(value) != os.getuid() for value in next(line for line in status.splitlines() if line.startswith("Uid:")).split()[1:]):
        raise ValueError("Unknown/foreign child UID; do not signal")
    raw = Path(f"/proc/{pid}/stat").read_text()
    return {"pid": pid, "start_ticks": int(raw[raw.rfind(")")+2:].split()[19]),
            "uid": os.getuid(), "cwd": str(Path(f"/proc/{pid}/cwd").resolve(strict=True))}


class NoGPU(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in GPU_MODULES:
            raise ImportError("CPU-only unit forbids GPU packages: " + fullname)


def child(permit_path, output, parent_pid, parent_ticks, run_id):
    permit, root, before = preflight(permit_path)
    if (process_identity(parent_pid)["start_ticks"] != parent_ticks or os.getppid() != parent_pid
            or os.sched_getaffinity(0) != {50} or resource.getrlimit(resource.RLIMIT_AS)[0] != 1073741824
            or resource.getrlimit(resource.RLIMIT_CPU)[0] != 300
            or os.getpriority(os.PRIO_PROCESS, 0) != 10
            or os.environ.get("CUDA_VISIBLE_DEVICES") != "" or os.environ.get("NVIDIA_VISIBLE_DEVICES") != "void"
            or os.environ.get("EPD_CPU_RUN_ID") != run_id):
        raise ValueError("Actual child affinity/memory/parent/CUDA identity differs")
    sys.meta_path.insert(0, NoGPU())
    def deny(*args, **kwargs): raise RuntimeError("CPU tests cannot start services/subprocesses/network")
    original_popen = subprocess.Popen
    def owned_cpu_process(argv, *args, **kwargs):
        if not isinstance(argv, (list, tuple)) or not argv or kwargs.get("shell"):
            raise RuntimeError("Only reviewed explicit git/own-Python CPU argv is allowed")
        executable = str(argv[0])
        if executable != "git" and Path(executable).resolve() != Path(sys.executable).resolve():
            raise RuntimeError("CPU tests cannot start model/services executables")
        if executable == "git" and any(token in argv for token in ("push", "pull", "fetch", "clone", "ls-remote")):
            raise RuntimeError("CPU tests cannot use network Git commands")
        cwd = Path(kwargs.get("cwd", root)).resolve()
        if not cwd.is_relative_to(root):
            raise RuntimeError("CPU helper must stay in this owned source/runtime root")
        process = original_popen(argv, *args, **kwargs)
        try:
            identity = process_identity(process.pid)
            with (Path(output) / "helper-pids.jsonl").open("a", encoding="utf-8") as file:
                file.write(json.dumps({"run_id": run_id, "identity": identity, "argv": list(map(str,argv))})+"\n")
        except FileNotFoundError:
            pass  # An already-exited child has no live process to clean up.
        return process
    subprocess.Popen = owned_cpu_process
    os.system = deny
    # Preserve this process's AF_UNIX socketpair/self-pipe for real asyncio loops.
    for name in ("connect", "connect_ex", "bind", "listen", "sendto", "sendmsg"):
        if not hasattr(socket.socket, name): continue
        original = getattr(socket.socket, name)
        def local_unix_only(sock, *args, _original=original, **kwargs):
            if sock.family in (socket.AF_INET, socket.AF_INET6):
                raise RuntimeError("CPU tests forbid TCP/UDP services and outbound network")
            return _original(sock, *args, **kwargs)
        setattr(socket.socket, name, local_unix_only)
    output = Path(output)
    sys.path.insert(0, str(root / "tests"))
    ids = (output / "test-events.jsonl").open("x", encoding="utf-8")
    class Result(unittest.TextTestResult):
        def startTest(self, test):
            ids.write(json.dumps({"event": "start", "test_id": test.id()})+"\n"); ids.flush(); super().startTest(test)
        def addSuccess(self, test):
            ids.write(json.dumps({"event": "success", "test_id": test.id()})+"\n"); ids.flush(); super().addSuccess(test)
        def addFailure(self, test, error):
            ids.write(json.dumps({"event": "failure", "test_id": test.id()})+"\n"); ids.flush(); super().addFailure(test,error)
        def addError(self, test, error):
            ids.write(json.dumps({"event": "error", "test_id": test.id()})+"\n"); ids.flush(); super().addError(test,error)
        def addSkip(self, test, reason):
            ids.write(json.dumps({"event": "skip", "test_id": test.id(), "reason": reason})+"\n"); ids.flush(); super().addSkip(test,reason)
        def addSubTest(self, test, subtest, error):
            if error is not None:
                ids.write(json.dumps({"event": "subtest_failure", "test_id": subtest.id()})+"\n"); ids.flush()
            super().addSubTest(test,subtest,error)
    loader = unittest.TestLoader()
    suite = unittest.TestSuite(loader.loadTestsFromName(name) for name in ("test_pd_cpu", "test_preflight_v5", "test_cpu_target_runner"))
    result = unittest.TextTestRunner(verbosity=2, resultclass=Result).run(suite)
    ids.close()
    with (output / "test-result.json").open("x",encoding="utf-8") as file:
        json.dump({"tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
            "skipped": len(result.skipped), "successful": result.wasSuccessful(), "GPU_imports_allowed": False},file,indent=2)
    if source_hashes(root, document(permit_path, permit["source_manifest"])) != before:
        raise ValueError("Source changed during CPU tests")
    return 0 if result.wasSuccessful() else 1


class ParentInterrupted(RuntimeError):
    def __init__(self, number):
        self.number = number
        super().__init__("CPU parent interrupted by signal " + str(number))


def _cleanup_owned(known, root, deadline, process=None):
    record = {"identity": known, "signals": [], "observations": []}
    if process is not None:
        try:
            if process.poll() is not None:
                return {**record, "state": "already_exited", "exit_code": process.returncode}
        except Exception as error:
            record["poll_error"] = str(error)
    if known is None:
        return {**record, "state": "identity_unknown_refused"}
    for number in (signal.SIGTERM, signal.SIGKILL):
        if time.monotonic() >= deadline:
            break
        try:
            current = process_identity(known["pid"])
        except FileNotFoundError:
            stat_path = Path(f'/proc/{known["pid"]}/stat')
            if not stat_path.exists(): return {**record, "state": "gone"}
            # An exited helper can be a zombie whose cwd no longer exists.
            try:
                raw = stat_path.read_text(); fields = raw[raw.rfind(")")+2:].split()
                status = Path(f'/proc/{known["pid"]}/status').read_text()
                uids = next(line for line in status.splitlines() if line.startswith("Uid:")).split()[1:]
                if int(fields[19]) != known["start_ticks"] or any(int(uid) != known["uid"] for uid in uids):
                    return {**record, "state": "identity_changed_refused"}
                if fields[0] != "Z": return {**record, "state": "cwd_unknown_refused"}
                record["observations"].append("zombie")
                while time.monotonic() < deadline and stat_path.exists(): time.sleep(.05)
                return {**record, "state": "gone" if not stat_path.exists() else "zombie_not_reaped"}
            except FileNotFoundError:
                return {**record, "state": "gone"}
            except Exception as error:
                return {**record, "state": "identity_unknown_refused", "error": str(error)}
        except Exception as error:
            return {**record, "state": "identity_unknown_refused", "error": str(error)}
        if current != known or not Path(known["cwd"]).is_relative_to(root):
            return {**record, "state": "identity_changed_refused"}
        try:
            os.kill(known["pid"], number); record["signals"].append(number)
        except ProcessLookupError:
            return {**record, "state": "gone"}
        except Exception as error:
            return {**record, "state": "signal_failed", "error": str(error)}
        wait_end = min(deadline, time.monotonic()+10)
        while time.monotonic() < wait_end:
            if process is not None:
                try:
                    if process.poll() is not None:
                        return {**record, "state": "exited", "exit_code": process.returncode}
                except Exception as error:
                    record["poll_error"] = str(error)
            try:
                if process_identity(known["pid"]) != known:
                    return {**record, "state": "identity_changed_refused"}
            except FileNotFoundError:
                if not Path(f'/proc/{known["pid"]}/stat').exists(): return {**record, "state": "gone"}
                break  # Recheck UID/start and record zombie in the next outer iteration.
            except Exception as error:
                return {**record, "state": "identity_unknown_refused", "error": str(error)}
            time.sleep(.05)
    return {**record, "state": "deadline_unconfirmed"}


def run(path):
    started = time.monotonic()
    permit, root, before = preflight(path)
    run_id = "cpu50-" + str(time.time_ns())
    output = root / "runtime" / run_id
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    (output / "test-tmp").mkdir()
    parent = process_identity(os.getpid())
    command = [sys.executable, "-I", "-S", "-B", str(SOURCE / "cpu_target_runner.py"),
        "--child", str(Path(path).resolve()), str(output), str(parent["pid"]), str(parent["start_ticks"]), run_id]
    env = {"PATH": os.environ.get("PATH", ""), "CUDA_VISIBLE_DEVICES": "", "NVIDIA_VISIBLE_DEVICES": "void",
           "PYTHONDONTWRITEBYTECODE": "1", "EPD_CPU_RUN_ID": run_id, "EPD_CPU_TEST_TMP": str(output / "test-tmp"),
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"}
    def limits():
        os.sched_setaffinity(0, {50})
        os.setpriority(os.PRIO_PROCESS, 0, 10)
        if os.getpriority(os.PRIO_PROCESS, 0) != 10: raise ValueError("Child nice10 not effective")
        resource.setrlimit(resource.RLIMIT_AS, (1073741824, 1073741824))
        resource.setrlimit(resource.RLIMIT_CPU, (300, 300))
    previous = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT)}
    starting, pending_signal, startup_attempted = True, None, False
    def interrupted(number, frame):
        nonlocal pending_signal
        if starting:
            pending_signal = pending_signal or number
            return  # Popen may have forked but not yet returned its owned object.
        for item in previous: signal.signal(item, signal.SIG_IGN)
        raise ParentInterrupted(number)
    process, identity, code, failure = None, None, 1, None
    cleanup, parent_nice, child_nice = [], None, None
    for number in previous: signal.signal(number, interrupted)
    try:
        os.setpriority(os.PRIO_PROCESS, 0, 10)
        parent_nice = os.getpriority(os.PRIO_PROCESS, 0)
        if parent_nice != 10: raise ValueError("Parent nice10 not effective")
        with (output / "raw-test.log").open("xb") as log:
            if time.monotonic()-started >= 300: raise TimeoutError("Preflight consumed the CPU unit")
            if pending_signal is not None: raise ParentInterrupted(pending_signal)
            startup_attempted = True
            process = subprocess.Popen(command,
                cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True, preexec_fn=limits)
            try:
                identity = process_identity(process.pid)
                child_nice = os.getpriority(os.PRIO_PROCESS, process.pid)
                if child_nice != 10: raise ValueError("Actual child nice10 differs")
            except FileNotFoundError:
                identity = None
            starting = False
            if pending_signal is not None: raise ParentInterrupted(pending_signal)
            code = process.wait(timeout=max(0, 300-(time.monotonic()-started)))
    except BaseException as error:
        failure = {"type": type(error).__name__, "message": str(error), "signal": getattr(error, "number", None)}
        code = 128+error.number if isinstance(error, ParentInterrupted) else 1
    finally:
        # All exits (signals, wait/log errors and normal completion) use this path.
        for number in previous: signal.signal(number, signal.SIG_IGN)
        deadline = min(time.monotonic()+30, started+330)
        try:
            if process is not None:
                cleanup.append(_cleanup_owned(identity, root, deadline, process))
            journal = output / "helper-pids.jsonl"
            if journal.exists():
                for line in reversed(journal.read_bytes().splitlines()):
                    try:
                        entry = json.loads(line)
                        if entry["run_id"] != run_id:
                            cleanup.append({"state": "helper_run_id_unknown_refused"}); continue
                        cleanup.append(_cleanup_owned(entry["identity"], root, deadline))
                    except Exception as error:
                        cleanup.append({"state": "helper_identity_unknown_refused", "error": str(error)})
        except Exception as error:
            cleanup.append({"state": "cleanup_exception_unconfirmed", "error": str(error)})
        after = {}
        for relative in before:
            try: after[relative] = sha(root/relative)
            except Exception as error: after[relative] = "unreadable:"+type(error).__name__
        confirmed = process is not None and bool(cleanup) and all(item["state"] in ("gone", "exited", "already_exited") for item in cleanup)
        if not confirmed or before != after: code = 1
        artifacts, terminal_errors = {}, []
        try: artifact_paths = list(output.iterdir())
        except Exception as error:
            artifact_paths = []; terminal_errors.append(type(error).__name__+":artifact-list")
        for artifact in artifact_paths:
            try:
                if artifact.is_file(): artifacts[artifact.name] = sha(artifact)
            except Exception as error:
                terminal_errors.append(type(error).__name__+":"+str(artifact))
        permit_sha, commit = permit.get("_verified_permit_sha256"), permit.get("_verified_commit")
        if permit_sha is None or commit is None: terminal_errors.append("missing-preflight-cache")
        if terminal_errors: code = 1
        report = {"scope": "actual_CPU_only_not_GPU_G3", "host": "qjh001", "cpu": 50,
            "child_RLIMIT_AS": 1073741824, "run_id": run_id, "exit_code": code,
            "child_exit_code": getattr(process, "returncode", None),
            "terminal_state": "completed" if failure is None and code == 0 else "stopped",
            "failure": failure, "cleanup_confirmed": confirmed, "cleanup": cleanup,
            "startup_attempted": startup_attempted, "child_object_obtained": process is not None,
            "startup_signal_deferred": pending_signal,
            "parent_nice": parent_nice, "child_nice": child_nice,
            "parent_identity": parent, "command": command,
            "duration_seconds": time.monotonic()-started, "source_before": before, "source_after": after,
            "source_unchanged": before == after, "permit_sha256": permit_sha, "commit": commit, "GPU_or_model_requests": 0,
            "SIGKILL_parent_guarantee": False,
            "terminal_errors": terminal_errors, "files": artifacts}
        receipt = output / "CPU-receipt.json"
        try:
            with (output / "CPU-receipt.partial").open("x", encoding="utf-8") as file:
                json.dump(report,file,indent=2); file.flush(); os.fsync(file.fileno())
            os.replace(output / "CPU-receipt.partial", receipt)
            print(json.dumps({"receipt": str(receipt), "sha256": sha(receipt), "exit_code": code}), flush=True)
        except Exception as error:
            os.write(2, (json.dumps({"terminal_report": report, "receipt_write_error": str(error)})+"\n").encode())
            code = 1
        finally:
            for number, handler in previous.items(): signal.signal(number, handler)
    return code


def main():
    if len(sys.argv) == 7 and sys.argv[1] == "--child":
        return child(sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), sys.argv[6])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--permit", type=Path, required=True)
    args = parser.parse_args()
    return run(args.permit.resolve())


if __name__ == "__main__":
    sys.exit(main())
