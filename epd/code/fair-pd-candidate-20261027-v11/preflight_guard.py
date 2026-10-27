"""Offline authorization/booking consumers and non-refundable preflight claims.

No network client, deployment command, GPU launcher or formal-run permission.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess
import time

from admission import bound_bytes
from experiment_plan import CANDIDATES, candidate_id, config_sha256

PHASE_LIMITS = {"numeric": (0, 36, 1800), "qualification": (120, 0, 2400),
                "calibration": (960, 0, 10800), "selected_g3": (360, 0, 4800),
                "cleanup_reserve": (0, 0, 600)}
STATIC_KEYS = {"schema", "state", "host", "uid", "root", "gpu_uuids", "numa_by_uuid",
               "resource_id", "booking_user", "booking_windows", "authorized_start_ms",
               "authorized_end_ms", "cleanup_seconds", "executor_id", "reviewer_ids",
               "phase_limits", "runtime_prefix", "max_idle_bytes", "max_auto_retries"}
INPUT_KEYS = {"run_id", "booking_file", "booking_sha256", "source_manifest_file",
              "source_manifest_sha256", "deploy_file", "deploy_sha256", "push_file", "push_sha256",
              "G1_file", "G1_sha256", "G2_file", "G2_sha256", "user_file", "user_sha256"}
INPUT_KEYS |= {"prerequisite_file", "prerequisite_sha256"}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load_bound(owner, filename, sha):
    return json.loads(bound_bytes(owner, filename, sha))


def require_review(owner, filename, sha, gate, scope_sha, config):
    # This consumes original independently authored JSON; there is no issuer here.
    review = load_bound(owner, filename, sha)
    if (review.get("gate") != gate or review.get("scope_sha256") != scope_sha
            or review.get("decision") not in ("APPROVE", "APPROVE_WITH_NITS")
            or type(review.get("blocking")) is not int or review["blocking"] != 0
            or review.get("reviewer_id") not in config["reviewer_ids"]
            or review.get("reviewer_id") == config["executor_id"]
            or not review.get("original_review_text")):
        raise ValueError("Independent original review does not approve this exact gate/scope")
    return review


def validate_static(config):
    if set(config) != STATIC_KEYS or config["schema"] != "epd-preflight-static-v1":
        raise ValueError("Unknown/missing static authorization keys")
    if config["state"] != "approved_preflight_only":
        raise ValueError("Candidate configuration has no GPU authorization")
    if (type(config["uid"]) is not int or config["uid"] < 0 or not config["host"]
            or not Path(config["root"]).is_absolute() or len(set(config["gpu_uuids"])) != 3
            or len(config["gpu_uuids"]) != 3 or set(config["numa_by_uuid"]) != set(config["gpu_uuids"])):
        raise ValueError("Exact host/UID/root/three UUID/NUMA scope required")
    if any(type(numa) is not int or numa < 0 for numa in config["numa_by_uuid"].values()):
        raise ValueError("NUMA grouping is unresolved")
    expected = {phase: list(limits) for phase, limits in PHASE_LIMITS.items()}
    if (config["phase_limits"] != expected or config["max_auto_retries"] != 0
            or config["cleanup_seconds"] < 120 or config["runtime_prefix"] != "runtime/"
            or not config["reviewer_ids"] or config["executor_id"] in config["reviewer_ids"]):
        raise ValueError("Budget, cleanup, retry or independent-review scope differs")
    if not config["authorized_start_ms"] < config["authorized_end_ms"] or not config["booking_windows"]:
        raise ValueError("Explicit approved time/booking scope missing")
    if config["resource_id"] != "h20/" + config["host"]:
        raise ValueError("This fixed experiment accepts only the explicitly approved H20 host")


def booking_remaining(raw, config, now_ms):
    observed = raw["observed_ms"]
    if (type(observed) is not int or observed > now_ms + 2000 or now_ms - observed > 300000
            or raw.get("read_only") is not True or raw.get("origin") != "gputime_read_only_api"):
        raise ValueError("Booking must be a fresh actual read-only API receipt, at most five minutes old")
    resources = [r for r in raw["resources"] if r["id"] == config["resource_id"]]
    if len(resources) != 1 or resources[0].get("active") is not True:
        raise ValueError("Wrong/inactive booking resource")
    allowed = {row["id"]: row for row in config["booking_windows"]}
    intervals = []
    for booking in raw["bookings"]:
        if booking["id"] not in allowed:
            continue
        approved = allowed[booking["id"]]
        if (booking["resource_id"] != config["resource_id"] or booking["node"] != config["host"]
                or booking["user"] != config["booking_user"] or booking["kind"] != "gpu"
                or booking["start_ms"] != approved["start_ms"] or booking["end_ms"] != approved["end_ms"]):
            raise ValueError("Booking identity/window differs from approved scope")
        intervals.append((booking["start_ms"], booking["end_ms"]))
    end = now_ms
    for start, stop in sorted(intervals):
        if start <= end < stop:
            end = stop
    end = min(end, config["authorized_end_ms"]) - config["cleanup_seconds"] * 1000
    if now_ms < config["authorized_start_ms"] or end <= now_ms:
        raise ValueError("No continuous owned booking before cleanup deadline")
    return (end - now_ms) / 1000


def unit_budget(phase, unit, candidate=None):
    ids = {candidate_id(c): c for c in CANDIDATES}
    if phase == "numeric" and unit == "numeric":
        return 0, 36, 1800
    if phase == "qualification" and unit in ids and candidate == unit:
        return 15, 0, 300
    if phase == "calibration":
        for cid in ids:
            if unit in {f"{cid}/{repeat}/{load}" for repeat in (0, 1) for load in "CDE"} and candidate == cid:
                return 20, 0, 225
    if phase == "selected_g3" and unit in ("replicas", "pd", "epd") and candidate in ids and ids[candidate][0] == unit:
        return 120, 0, 1600
    if phase == "cleanup_reserve" and unit == "cleanup_reserve":
        return 0, 0, 600
    raise ValueError("Unknown unit, candidate, phase or formal request")


def verify_checkout(config, inputs, owner, command=subprocess.check_output):
    root = Path(config["root"]).resolve()
    manifest = load_bound(owner, inputs["source_manifest_file"], inputs["source_manifest_sha256"])
    pushed = load_bound(owner, inputs["push_file"], inputs["push_sha256"])
    deploy = load_bound(owner, inputs["deploy_file"], inputs["deploy_sha256"])
    commit = pushed["commit"]
    if (not re.fullmatch(r"[0-9a-f]{40}", commit) or pushed.get("remote_verified") is not True
            or pushed["source_manifest_sha256"] != inputs["source_manifest_sha256"]):
        raise ValueError("Designated pushed commit/source proof missing")
    remote = load_bound(owner, pushed["raw_remote_file"], pushed["raw_remote_sha256"])
    if remote.get("sha") != commit or remote.get("repository") != pushed["repository"]:
        raise ValueError("Raw remote commit evidence differs")
    expected = {"commit": commit, "source_manifest_sha256": inputs["source_manifest_sha256"],
                "host": config["host"], "uid": config["uid"], "root": str(root),
                "gpu_uuids": config["gpu_uuids"], "numa_by_uuid": config["numa_by_uuid"]}
    if any(deploy.get(key) != value for key, value in expected.items()):
        raise ValueError("Deployment commit/manifest/host/UID/root/GPU/NUMA differs")
    if command(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip() != commit:
        raise ValueError("Actual source checkout is not the designated commit")
    if command(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"], text=True).strip():
        raise ValueError("Tracked source changed after deployment")
    untracked = command(["git", "-C", str(root), "ls-files", "--others", "--exclude-standard"], text=True).splitlines()
    if any(not rel.startswith("runtime/") or Path(rel).suffix in (".py", ".so", ".sh", ".pth") for rel in untracked):
        raise ValueError("Untracked code/out-of-whitelist files in source checkout")
    required = {"preflight_guard.py", "live_evidence.py", "selected_g3.py", "admission.py",
                "experiment_plan.py", "benchmark.py", "client_window.py", "preflight-static.json"}
    if not required <= {item["path"] for item in manifest["files"]}:
        raise ValueError("Source manifest omits an execution/admission component")
    if json.loads((root / "preflight-static.json").read_bytes()) != config:
        raise ValueError("Approved static config differs from the Git-pinned source file")
    command(["git", "-C", str(root), "ls-files", "--error-unmatch", "preflight-static.json"], text=True)
    for item in manifest["files"]:
        path = (root / item["path"]).resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("Actual deployment file SHA differs")
    own = next(item for item in manifest["files"] if item["path"] == "preflight_guard.py")
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != own["sha256"]:
        raise ValueError("Executing guard bytes differ from the deployed source pin")
    return {**expected, "boot_id": deploy["boot_id"], "deploy_sha256": inputs["deploy_sha256"]}


def validate_resources(snapshot, config, run_id, deployed, now_ms):
    if not 0 <= now_ms - snapshot["observed_ms"] <= 300000:
        raise ValueError("GPU resource receipt is stale/future")
    expected = {"host": config["host"], "uid": config["uid"], "root": config["root"],
                "boot_id": deployed["boot_id"], "run_id": run_id}
    if any(snapshot.get(key) != value for key, value in expected.items()):
        raise ValueError("Actual resource host/UID/root/boot/run identity differs")
    if set(snapshot["gpus"]) != set(config["gpu_uuids"]):
        raise ValueError("Actual resource receipt must contain exactly the approved three UUIDs")
    for uuid, gpu in snapshot["gpus"].items():
        if gpu["numa"] != config["numa_by_uuid"][uuid] or gpu["unit"] != "bytes":
            raise ValueError("Actual NUMA/units differ")
        if "H20" not in gpu.get("name", ""):
            raise ValueError("Actual selected GPU is not an H20")
        if (type(gpu["capacity_bytes"]) is not int or type(gpu["used_bytes"]) is not int
                or gpu["capacity_bytes"] <= 0 or not 0 <= gpu["used_bytes"] <= gpu["capacity_bytes"] * 65 // 100):
            raise ValueError("Actual GPU bytes exceed the common memory cap")
        if gpu["processes"]:
            for process in gpu["processes"]:
                if any(process.get(key) != expected[key] for key in ("uid", "root", "run_id", "boot_id")):
                    raise ValueError("Foreign/unknown GPU process; do not kill or borrow it")
                if type(process.get("pid")) is not int or type(process.get("proc_start_ticks")) is not int:
                    raise ValueError("PID/start identity is unresolved")
        elif gpu["used_bytes"] > config["max_idle_bytes"]:
            raise ValueError("GPU not empty enough for owned startup")


def require_prerequisite(owner, inputs, phase, candidate, config):
    if phase in ("numeric", "cleanup_reserve"):
        return
    bundle = load_bound(owner, inputs["prerequisite_file"], inputs["prerequisite_sha256"])
    body = bundle["proof"]
    kinds = {"qualification": "numeric_communication", "calibration": "exact_candidate_eligibility",
             "selected_g3": "calibration_selection"}
    if (body.get("kind") != kinds[phase]
            or body.get("source_manifest_sha256") != inputs["source_manifest_sha256"]
            or body.get("deploy_sha256") != inputs["deploy_sha256"]
            or not body.get("raw_files")):
        raise ValueError("Actual prerequisite evidence is missing or unbound")
    if phase == "calibration" and body.get("candidate") != candidate:
        raise ValueError("Eligibility proof is for another exact candidate/profile")
    if phase == "selected_g3" and candidate not in body.get("selected_candidates", []):
        raise ValueError("Candidate was not selected by the reviewed calibration proof")
    for item in body["raw_files"]:
        if not bound_bytes(owner, item["path"], item["sha256"]):
            raise ValueError("Prerequisite raw evidence is empty")
    require_review(owner, bundle["review_file"], bundle["review_sha256"], "G3", digest(body), config)


class Claim:
    def __init__(self, config, inputs, owner, unit, phase, candidate, snapshot, *, now_ms,
                 clock=time.perf_counter, command=subprocess.check_output, actual=None):
        validate_static(config)
        if set(inputs) != INPUT_KEYS or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", inputs["run_id"]):
            raise ValueError("Runtime input whitelist/run identity differs")
        actual = actual or {"host": socket.gethostname(), "uid": os.getuid(), "root": str(Path.cwd().resolve())}
        if any(actual[key] != config[key] for key in ("host", "uid", "root")):
            raise ValueError("Actual executor host/UID/root differs")
        cfg_sha = digest(config)
        user = load_bound(owner, inputs["user_file"], inputs["user_sha256"])
        if (user.get("author") != "human_user" or user.get("scope") != "EPD_preflight_only"
                or user.get("static_config_sha256") != cfg_sha):
            raise ValueError("Exact user approval is required; a lock/booking is not authorization")
        if not bound_bytes(owner, user["original_instruction_file"], user["original_instruction_sha256"]).strip():
            raise ValueError("Original human instruction missing")
        require_review(owner, inputs["G1_file"], inputs["G1_sha256"], "G1", cfg_sha, config)
        scope = digest({"static_config_sha256": cfg_sha, "source_manifest_sha256": inputs["source_manifest_sha256"]})
        require_review(owner, inputs["G2_file"], inputs["G2_sha256"], "G2", scope, config)
        self.deployed = verify_checkout(config, inputs, owner, command)
        require_prerequisite(owner, inputs, phase, candidate, config)
        validate_resources(snapshot, config, inputs["run_id"], self.deployed, now_ms)
        remaining = booking_remaining(load_bound(owner, inputs["booking_file"], inputs["booking_sha256"]), config, now_ms)
        self.requests, self.transfers, seconds = unit_budget(phase, unit, candidate)
        if seconds > remaining:
            raise ValueError("Insufficient booking wallclock for the complete unit plus cleanup")
        self.config, self.inputs, self.owner = config, inputs, Path(owner)
        self.phase, self.unit, self.candidate = phase, unit, candidate
        self.clock = clock
        start = clock()
        self.deadline = start + seconds
        self.booking_deadline_ms = now_ms + remaining * 1000
        self.timing = {"clock": "time.perf_counter", "host": config["host"], "boot_id": self.deployed["boot_id"],
            "start_monotonic": start, "start_utc_ms": now_ms, "deadline_monotonic": self.deadline,
            "deadline_utc_ms": min(now_ms + seconds * 1000, self.booking_deadline_ms), "allocation_seconds": seconds}
        self.config_sha256, self.resources = cfg_sha, snapshot
        self.command = command

    def check(self, now_ms=None):
        now_ms = int(time.time() * 1000) if now_ms is None else now_ms
        current = self.clock()
        expected_utc = self.timing["start_utc_ms"] + (current - self.timing["start_monotonic"]) * 1000
        if (not math.isfinite(current) or not math.isfinite(expected_utc) or abs(now_ms - expected_utc) > 100
                or current >= self.deadline or now_ms >= self.timing["deadline_utc_ms"]
                or now_ms >= self.booking_deadline_ms):
            raise TimeoutError("Unit wallclock/booking deadline reached; no next request")

    def reserve(self, ledger):
        # Separate persistent flock plus atomic replace: locking is not a booking.
        import fcntl
        import stat
        import tempfile
        self.check()
        now_ms = int(time.time() * 1000)
        validate_resources(self.resources, self.config, self.inputs["run_id"], self.deployed, now_ms)
        if unit_budget(self.phase, self.unit, self.candidate)[2] > booking_remaining(
                load_bound(self.owner, self.inputs["booking_file"], self.inputs["booking_sha256"]),
                self.config, now_ms):
            raise ValueError("Booking became insufficient before durable claim")
        verify_checkout(self.config, self.inputs, self.owner, self.command)
        ledger = Path(ledger).resolve()
        runtime = (Path(self.config["root"]) / "runtime").resolve()
        if not ledger.is_relative_to(runtime):
            raise ValueError("Budget ledger must stay in the approved runtime data directory")
        fd = os.open(str(ledger) + ".lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "r+", encoding="utf-8") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            info = os.fstat(lock.fileno())
            if info.st_uid != self.config["uid"] or not stat.S_ISREG(info.st_mode):
                raise ValueError("Budget lock is not an owned regular file")
            state = json.loads(ledger.read_bytes()) if ledger.exists() else {
                "static_config_sha256": self.config_sha256, "units": {}, "spent": {}}
            # The actual durable unit starts here, before accounting/fsync or model startup.
            start_utc_ms, start_monotonic = int(time.time() * 1000), self.clock()
            seconds = unit_budget(self.phase, self.unit, self.candidate)[2]
            if start_utc_ms + seconds * 1000 > self.booking_deadline_ms:
                raise ValueError("Complete unit no longer fits before booking cleanup")
            self.deadline = start_monotonic + seconds
            self.timing = {"clock": "time.perf_counter", "host": self.config["host"], "boot_id": self.deployed["boot_id"],
                "start_monotonic": start_monotonic, "start_utc_ms": start_utc_ms,
                "deadline_monotonic": self.deadline, "deadline_utc_ms": start_utc_ms + seconds * 1000,
                "allocation_seconds": seconds}
            self.account(state)
            claims = runtime / "claims"
            claims.mkdir(exist_ok=True)
            if not claims.resolve().is_relative_to(runtime):
                raise ValueError("Claim directory escaped runtime whitelist")
            key = self.phase + "/" + self.unit
            claim_path = claims / (digest(key) + ".json")
            with claim_path.open("x", encoding="utf-8") as file:
                json.dump({"unit": state["units"][key], "resources": self.resources, "timing": self.timing,
                           "source": self.deployed, "static_config_sha256": self.config_sha256}, file, indent=2)
                file.flush(); os.fsync(file.fileno())
            temp_fd, temp_name = tempfile.mkstemp(prefix=".budget-", dir=ledger.parent)
            with os.fdopen(temp_fd, "w", encoding="utf-8") as file:
                json.dump(state, file, indent=2); file.flush(); os.fsync(file.fileno())
            os.replace(temp_name, ledger)
            directory_fd = os.open(ledger.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        self.reserved = True
        self.reservation_receipt = {"ledger": str(ledger), "claim": str(claim_path),
            "claim_sha256": hashlib.sha256(claim_path.read_bytes()).hexdigest(), "key": key}
        return state

    def verify_reservation(self):
        self.check()
        evidence = getattr(self, "reservation_receipt", None)
        if evidence is None:
            raise ValueError("No actual durable claim evidence; reserved boolean is insufficient")
        runtime = (Path(self.config["root"]) / "runtime").resolve()
        paths = [Path(evidence[key]).resolve() for key in ("ledger", "claim")]
        if any(not path.is_relative_to(runtime) for path in paths):
            raise ValueError("Durable claim escaped the runtime whitelist")
        if hashlib.sha256(paths[1].read_bytes()).hexdigest() != evidence["claim_sha256"]:
            raise ValueError("Durable claim bytes changed")
        claim, ledger = json.loads(paths[1].read_bytes()), json.loads(paths[0].read_bytes())
        if (claim["static_config_sha256"] != self.config_sha256 or ledger["static_config_sha256"] != self.config_sha256
                or ledger["units"].get(evidence["key"]) != claim["unit"]
                or claim["unit"]["run_id"] != self.inputs["run_id"]
                or claim["unit"]["candidate"] != self.candidate
                or claim["unit"]["phase"] != self.phase or claim["unit"]["unit"] != self.unit
                or claim["timing"] != self.timing or claim["unit"]["timing"] != self.timing):
            raise ValueError("Actual durable ledger/unit/source scope differs")

    def account(self, state):
        key = self.phase + "/" + self.unit
        if state["static_config_sha256"] != self.config_sha256 or key in state["units"]:
            raise ValueError("Budget scope differs or unit already attempted; zero automatic retries")
        recomputed = {}
        for old_key, record in state["units"].items():
            if old_key != record["phase"] + "/" + record["unit"]:
                raise ValueError("Budget unit key/record differs")
            allocation = list(unit_budget(record["phase"], record["unit"], record["candidate"]))
            if allocation != record["allocation"]:
                raise ValueError("Budget allocation was changed")
            previous = recomputed.get(record["phase"], [0, 0, 0])
            recomputed[record["phase"]] = [a + b for a, b in zip(previous, allocation)]
        if state["spent"] != recomputed:
            raise ValueError("Budget summary differs from consumed unit records")
        spent = state["spent"].get(self.phase, [0, 0, 0])
        allocation = [self.requests, self.transfers, unit_budget(self.phase, self.unit, self.candidate)[2]]
        total = [a + b for a, b in zip(spent, allocation)]
        if any(value > limit for value, limit in zip(total, PHASE_LIMITS[self.phase])):
            raise ValueError("Phase request/transfer/wallclock budget exceeded")
        state["spent"][self.phase] = total
        state["units"][key] = {"run_id": self.inputs["run_id"], "candidate": self.candidate,
            "phase": self.phase, "unit": self.unit,
            "timing": dict(self.timing),
            "allocation": allocation, "state": "claimed_consumed_even_if_launch_fails",
            "deploy_sha256": self.inputs["deploy_sha256"], "booking_sha256": self.inputs["booking_sha256"]}

    def admit_request(self, count=1):
        self.verify_reservation()
        if not getattr(self, "reserved", False) or type(count) is not int or count < 1:
            raise ValueError("Requests require an already recorded budget claim")
        used = getattr(self, "issued_requests", 0) + count
        if used > self.requests:
            raise ValueError("Unit request budget exhausted")
        self.issued_requests = used

    def admit_transfer(self, count=1):
        self.verify_reservation()
        if not getattr(self, "reserved", False) or type(count) is not int or count < 1:
            raise ValueError("Transfers require an already recorded numeric claim")
        used = getattr(self, "issued_transfers", 0) + count
        if used > self.transfers:
            raise ValueError("Numeric transfer budget exhausted")
        self.issued_transfers = used
