"""Assemble the fresh permit and run the single approved v13 CPU unit on qjh000.

Usage: python -X utf8 -I run_cpu_unit.py <commit>

Order: GitHub main ref -> clock skew -> fresh read-only booking and host probe back to back ->
upload inputs/permit without overwriting -> one runner invocation -> download originals.
Before a claim exists a refused attempt may be re-collected (at most three attempts, each in its
own attempt directory); once runtime/CPU-unit-claim.json exists the unit is consumed for good.
"""
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
import time
from pathlib import Path

HOST = "qjh000"
ROOT = "/var/tmp/boyjiang-epd-cpu-qjh000-20261028"
CODE_REL = "epd/code/fair-pd-candidate-20261028-v13"
PLAN_REL = "epd/plans/fair-pd-20261028-v13"
SOURCE_ROOT = f"{ROOT}/{CODE_REL}"
PLAN_DIR = f"{ROOT}/{PLAN_REL}"
BOOKING_ID = "bk-20261028T0141-8936eb9c"
BOOKING_START, BOOKING_END = 1793149200000, 1793185200000
REPO = "https://github.com/BoyJiang2/spaceserve-epd-reproduction.git"
API_REF = "https://api.github.com/repos/BoyJiang2/spaceserve-epd-reproduction/git/ref/heads/main"
HERE = Path(__file__).resolve().parent
WORK = HERE.parent
EVIDENCE = WORK / "cpu-unit-v13"
CHECKOUT_PLAN = WORK.parents[1] / "work" / "repository-upload" / "checkout" / PLAN_REL
GPUTIME = Path.home() / ".claude" / "skills" / "gputime-booking-agent" / "scripts" / "gputime_agent.py"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=30", "-o", "ServerAliveInterval=10", HOST]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def now_ms():
    return int(time.time() * 1000)


def ssh(command, data=None, timeout=600):
    return subprocess.run(SSH + [command], input=data, capture_output=True, timeout=timeout)


def dump(obj):
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def main():
    commit = sys.argv[1]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise SystemExit("commit must be a full SHA")
    attempt = 1 + len(list(EVIDENCE.glob("attempt-*"))) if EVIDENCE.exists() else 1
    if attempt > 3:
        raise SystemExit("three pre-claim attempts already recorded; stop")
    claimed = ssh(f"test -e {SOURCE_ROOT}/runtime/CPU-unit-claim.json && echo CLAIMED || echo NONE")
    if claimed.returncode or claimed.stdout.strip() != b"NONE":
        raise SystemExit("a claim already exists (or the check failed); the unit is consumed")
    suffix = "" if attempt == 1 else f"-attempt{attempt}"
    input_rel, permit_name = f"cpu-inputs{suffix}", f"cpu-permit{suffix}.json"

    # Committed plan artifacts, read from the local checkout at the designated commit.
    committed = {}
    for name in ("scope.json", "G1-original.json", "G2-original.json", "user-CPU-grant.json",
                 "user-original-instruction.txt", "source-manifest-v13.json"):
        blob = subprocess.run(["git", "-C", str(CHECKOUT_PLAN), "show", f"{commit}:{PLAN_REL}/{name}"],
                              capture_output=True, check=True).stdout
        committed[name] = blob
    scope = json.loads(committed["scope.json"])

    # 1. Deployment record written by deploy_v13_remote.sh (read-only fetch of its exact bytes).
    result = ssh(f"cat {PLAN_DIR}/cpu-inputs/deployment.json")
    if result.returncode:
        raise SystemExit("deployment.json unavailable: " + result.stderr.decode(errors="replace"))
    deployment_raw = result.stdout
    deployment = json.loads(deployment_raw)
    if (deployment["commit"] != commit or deployment["head"] != commit or not deployment["tracked_clean"]
            or deployment["mismatched_files"] or deployment["unlisted_files"]
            or deployment["manifest_sha256"] != sha(committed["source-manifest-v13.json"])):
        raise SystemExit("deployment record does not prove the designated clean commit")

    # 2. Actual remote main ref (anonymous read-only GET) proving the designated commit is pushed.
    ref = subprocess.run(["curl", "-sS", "--fail", "--max-time", "60", "-H", "Accept: application/vnd.github+json",
                          API_REF], capture_output=True, timeout=90)
    if ref.returncode:
        raise SystemExit("GitHub ref GET failed: " + ref.stderr.decode(errors="replace"))
    ref_raw = ref.stdout
    if json.loads(ref_raw)["object"]["sha"] != commit:
        raise SystemExit("remote main is not the designated commit")
    receipt = {"sha": commit, "repository": REPO,
               "origin": "actual GitHub API GET git/ref/heads/main, normalized receipt", "read_only": True,
               "raw_response_file": f"{input_rel}/github-main-ref.json", "raw_response_sha256": sha(ref_raw),
               "observed_ms": now_ms()}
    receipt_raw = dump(receipt)
    pushed_raw = dump({"commit": commit, "source_manifest_sha256": sha(committed["source-manifest-v13.json"]),
                       "raw_remote": {"path": f"{input_rel}/github-main-receipt.json", "sha256": sha(receipt_raw)}})

    # 3. Clock skew: the booking observation uses the local clock, the runner the server clock.
    before = now_ms()
    remote = ssh("date +%s%3N")
    after = now_ms()
    remote_ms = int(remote.stdout.strip())
    skew = remote_ms - (before + after) // 2
    if abs(skew) > 60000:
        raise SystemExit(f"clock skew {skew} ms too large for the five-minute freshness check")
    # Read-only preparation succeeded; only from here on does a collection count as an attempt.
    run_dir = EVIDENCE / f"attempt-{attempt}"
    inputs = run_dir / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "deployment.json").write_bytes(deployment_raw)
    (run_dir / "clock-skew.json").write_bytes(dump({
        "local_before_ms": before, "remote_ms": remote_ms, "local_after_ms": after,
        "remote_minus_local_ms": skew, "round_trip_ms": after - before}))

    # 4. Fresh read-only booking snapshot, then the host probe, back to back.
    snap = subprocess.run([sys.executable, "-X", "utf8", str(GPUTIME), "snapshot"], capture_output=True, timeout=120)
    observed = now_ms()
    if snap.returncode:
        raise SystemExit("booking snapshot failed: " + snap.stderr.decode(errors="replace"))
    (run_dir / "booking-snapshot-raw.json").write_bytes(snap.stdout)  # local only, never published
    raw = json.loads(snap.stdout)
    own = [b for b in raw["bookings"] if b.get("id") == BOOKING_ID]
    resources = [r for r in raw["resources"] if r.get("id") == "h20/qjh000"]
    if (len(own) != 1 or len(resources) != 1 or resources[0].get("active") is not True
            or own[0].get("kind") != "cpu" or own[0].get("user") != "boyjiang"
            or own[0].get("start_ms") != BOOKING_START or own[0].get("end_ms") != BOOKING_END):
        raise SystemExit("fresh booking does not match the approved CPU ticket")
    booking = {"origin": "gputime_read_only_api", "read_only": True, "observed_ms": observed,
               "raw_snapshot_sha256": sha(snap.stdout),
               "resources": [{"id": "h20/qjh000", "active": resources[0]["active"]}], "bookings": own}
    booking_raw = dump(booking)
    probe = ssh(f"/usr/bin/python3 -I -S - {SOURCE_ROOT}", data=(HERE / "remote_host_probe.py").read_bytes())
    if probe.returncode:
        raise SystemExit("host probe failed: " + probe.stderr.decode(errors="replace"))
    probe_raw = probe.stdout
    host = json.loads(probe_raw)
    if (host["host"] != HOST or host["boot_id"] != scope["boot_id"] or host["cpu50_conflicting_pids"]
            or host["root_active_units"] or host["available_affinity"] != [50]):
        (inputs / "host-probe-REFUSED.json").write_bytes(probe_raw)
        raise SystemExit("host probe refuses the unit: " + probe_raw.decode())

    descriptor = lambda name, data: {"path": name, "sha256": sha(data)}
    permit = {
        "scope": scope,
        "G1": descriptor("G1-original.json", committed["G1-original.json"]),
        "G2": descriptor("G2-original.json", committed["G2-original.json"]),
        "source_manifest": descriptor("source-manifest-v13.json", committed["source-manifest-v13.json"]),
        "user_CPU_grant": descriptor("user-CPU-grant.json", committed["user-CPU-grant.json"]),
        "pushed_commit": descriptor(f"{input_rel}/pushed-commit.json", pushed_raw),
        "cpu_booking": descriptor(f"{input_rel}/booking.json", booking_raw),
        "host_probe": descriptor(f"{input_rel}/host-probe.json", probe_raw),
        "actual_deployment": descriptor("cpu-inputs/deployment.json", deployment_raw),
    }
    permit_raw = dump(permit)
    uploads = {f"{input_rel}/booking.json": booking_raw, f"{input_rel}/host-probe.json": probe_raw,
               f"{input_rel}/github-main-ref.json": ref_raw, f"{input_rel}/github-main-receipt.json": receipt_raw,
               f"{input_rel}/pushed-commit.json": pushed_raw, permit_name: permit_raw}
    for name, data in uploads.items():
        (inputs / Path(name).name).write_bytes(data)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for name, data in uploads.items():
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(data), 0o600, int(time.time())
            tar.addfile(info, io.BytesIO(data))
    put = ssh(f"tar -x -k -C {PLAN_DIR} -f -", data=buffer.getvalue())
    if put.returncode:
        raise SystemExit("upload refused (no overwrite): " + put.stderr.decode(errors="replace"))
    if skew < 0:  # server clock behind: wait until the server sees a non-negative booking age
        wait_ms = -skew + 3000 - (now_ms() - observed)
        if wait_ms > 0:
            time.sleep(wait_ms / 1000)
    age = now_ms() - observed
    if age > 200000:
        raise SystemExit(f"booking observation already {age} ms old; not starting")

    # 5. The single runner invocation. Output goes to files so an SSH drop cannot break the receipt.
    stdout_name, stderr_name = f"runner-stdout{suffix}.txt", f"runner-stderr{suffix}.txt"
    command = (f"cd {SOURCE_ROOT} && taskset -c 50 nice -n 10 env CUDA_VISIBLE_DEVICES= "
               f"NVIDIA_VISIBLE_DEVICES=void PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -I -S -B "
               f"{SOURCE_ROOT}/cpu_target_runner.py --permit {PLAN_DIR}/{permit_name} "
               f"> {PLAN_DIR}/{stdout_name} 2> {PLAN_DIR}/{stderr_name}; echo RUNNER_EXIT=$?")
    (run_dir / "actual-command.txt").write_text(command + "\n", encoding="utf-8")
    started = now_ms()
    run = ssh(command, timeout=900)
    (run_dir / "ssh-run.json").write_bytes(dump({
        "ssh_exit": run.returncode, "stdout": run.stdout.decode(errors="replace"),
        "stderr": run.stderr.decode(errors="replace"), "local_start_ms": started, "local_end_ms": now_ms(),
        "booking_age_at_start_ms": started - observed}))
    print(run.stdout.decode(errors="replace").strip(), "| ssh exit", run.returncode)
    if run.returncode or b"RUNNER_EXIT=" not in run.stdout:
        # SSH dropped: never rerun; wait read-only until a claimed runner has written its receipt.
        for _ in range(42):
            state = ssh(f"cd {SOURCE_ROOT} && if [ ! -e runtime/CPU-unit-claim.json ]; then echo NOCLAIM; "
                        f"elif ls runtime/*/CPU-receipt.json >/dev/null 2>&1; then echo RECEIPT; else echo WAIT; fi")
            if state.stdout.strip() in (b"NOCLAIM", b"RECEIPT"):
                break
            time.sleep(10)

    # 6. Download originals read-only (runtime dir if any, plan-side inputs, runner output).
    members = list(dict.fromkeys([f"{PLAN_REL}/cpu-inputs", f"{PLAN_REL}/{input_rel}", f"{PLAN_REL}/{permit_name}",
                                  f"{PLAN_REL}/{stdout_name}", f"{PLAN_REL}/{stderr_name}", f"{CODE_REL}/runtime"]))
    listing = " ".join(members)
    pack = ssh(f"cd {ROOT} && tar -c -f - $(for m in {listing}; do [ -e $m ] && echo $m; done)", timeout=600)
    (run_dir / "result-download.tar").write_bytes(pack.stdout)
    with tarfile.open(fileobj=io.BytesIO(pack.stdout)) as tar:
        tar.extractall(run_dir / "result-original", filter="data")
    print("download tar exit", pack.returncode, "bytes", len(pack.stdout))


if __name__ == "__main__":
    main()
