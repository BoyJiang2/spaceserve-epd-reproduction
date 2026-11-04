"""One-GPU isolated MPS numerical admission; no model or overlap claim."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

ROOT = "/local/boyjiang/SpaceServe-official"
GPU = "GPU-6186aa04-e2e2-84c4-0c50-a8d1bb260e32"
CONTROL = "/usr/bin/nvidia-cuda-mps-control"
PY = "/local/boyjiang/spaceserve/assets/envs/space/bin/python"


def save(path, value):
    with path.open("x") as f:
        json.dump(value, f, indent=2)
        f.write("\n")


def identity(pid, env, minimum):
    proc = Path("/proc") / str(pid)
    assert proc.stat().st_uid == os.getuid()
    stat = (proc / "stat").read_text()
    ticks = int(stat.rsplit(") ", 1)[1].split()[19])
    assert ticks >= minimum
    raw = (proc / "environ").read_bytes().split(b"\0")
    actual = dict(x.split(b"=", 1) for x in raw if b"=" in x)
    for key in ("EXP_ROOT", "REPRO_RUN_ID", "CUDA_MPS_PIPE_DIRECTORY"):
        assert actual.get(key.encode()) == env[key].encode(), (pid, key)
    return dict(pid=pid, uid=os.getuid(), start_ticks=ticks, stat=stat,
                boot=Path("/proc/sys/kernel/random/boot_id").read_text().strip())


def pid_list(text):
    values = text.split()
    assert all(x.isdecimal() and int(x) > 0 for x in values), repr(text)
    return {int(x) for x in values}


def rpc(env, command, deadline, run):
    remaining = deadline - time.monotonic()
    assert remaining > 0, "shared deadline exceeded"
    p = subprocess.run([CONTROL], input=command + "\n", text=True, capture_output=True,
                       env=env, timeout=min(3, remaining))
    with (run / "control.jsonl").open("a") as f:
        f.write(json.dumps(dict(epoch=time.time(), command=command, exit=p.returncode,
                               stdout=p.stdout, stderr=p.stderr)) + "\n")
    assert p.returncode == 0, (command, p.returncode, p.stderr)
    return p.stdout


def stop(process, fd, sig=signal.SIGTERM):
    if process.poll() is None:
        try:
            if fd is not None:
                signal.pidfd_send_signal(fd, sig)
            elif sig == signal.SIGTERM:
                process.terminate()
            else:
                process.kill()
        except ProcessLookupError:
            pass


def client(index, run):
    import torch
    assert torch.cuda.device_count() == 1
    torch.cuda.set_device(0)
    cpu = torch.arange(1024, dtype=torch.float32).remainder(64).to(torch.float16)
    tensor = cpu.to("cuda")
    result = (tensor + index) * 2
    torch.cuda.synchronize()
    actual, expected = result.cpu(), (cpu + index) * 2
    exact = torch.equal(actual, expected)
    save(run / ("client-" + str(index) + ".ready.json"), dict(
        pid=os.getpid(), index=index, exact=exact,
        mismatches=int((actual != expected).sum()),
        actual_sha256=hashlib.sha256(actual.numpy().tobytes()).hexdigest(),
        expected_sha256=hashlib.sha256(expected.numpy().tobytes()).hexdigest(),
        device=str(torch.cuda.get_device_properties(0)), torch=torch.__version__,
        visible_devices=os.environ["CUDA_VISIBLE_DEVICES"], epoch=time.time()))
    assert exact
    assert sys.stdin.readline().strip() == "release"


def interrupt(signum, frame):
    raise TimeoutError("supervisor received signal " + str(signum))


def main(run):
    assert os.getuid() == 2147
    assert run.resolve().parent == Path("/local/boyjiang/spaceserve/runs")
    assert not run.exists()
    run.mkdir(mode=0o700)
    for name in ("pipe", "log"):
        (run / name).mkdir(mode=0o700)
    minimum = int(float(Path("/proc/uptime").read_text().split()[0]) * os.sysconf("SC_CLK_TCK"))
    env = dict(os.environ, EXP_ROOT=ROOT, REPRO_RUN_ID=str(run) + ":" + uuid.uuid4().hex,
               CUDA_VISIBLE_DEVICES=GPU, CUDA_MPS_PIPE_DIRECTORY=str(run / "pipe"),
               CUDA_MPS_LOG_DIRECTORY=str(run / "log"), OMP_NUM_THREADS="4")
    signal.signal(signal.SIGTERM, interrupt)
    work_end = time.monotonic() + 180
    children, fds, handles = [], {}, []
    controller = None
    success, cleanup_error = False, None
    registered = set()
    device = subprocess.check_output(["nvidia-smi", "-i", "3", "--query-gpu=uuid",
                                      "--format=csv,noheader"], text=True).strip()
    assert device == GPU
    before = subprocess.check_output(["nvidia-smi", "-i", "3", "--query-compute-apps=pid",
                                      "--format=csv,noheader"], text=True).strip()
    assert not before, "GPU has compute clients"
    try:
        out = (run / "controller.stdout").open("x")
        err = (run / "controller.stderr").open("x")
        handles += [out, err]
        controller = subprocess.Popen([CONTROL, "-f"], env=env, stdin=subprocess.DEVNULL,
                                      stdout=out, stderr=err, start_new_session=True)
        fds[controller.pid] = os.pidfd_open(controller.pid)
        save(run / "controller.identity.json", identity(controller.pid, env, minimum))
        while not (run / "pipe/control").exists():
            assert controller.poll() is None
            assert time.monotonic() < work_end
            time.sleep(.05)
        assert not pid_list(rpc(env, "get_server_list", work_end, run)), "unexpected initial server"
        for i in range(2):
            out = (run / ("client-" + str(i) + ".stdout")).open("x")
            err = (run / ("client-" + str(i) + ".stderr")).open("x")
            handles += [out, err]
            p = subprocess.Popen([PY, str(Path(__file__).resolve()), "client", str(i), str(run)],
                                 env=env, stdin=subprocess.PIPE, stdout=out, stderr=err, text=True)
            children.append(p)
            registered.add(p.pid)
            fds[p.pid] = os.pidfd_open(p.pid)
            save(run / ("client-" + str(i) + ".identity.json"), identity(p.pid, env, minimum))
        for i, p in enumerate(children):
            path = run / ("client-" + str(i) + ".ready.json")
            while True:
                assert p.poll() is None, ("client failed", i, p.returncode)
                assert time.monotonic() < work_end
                try:
                    result = json.loads(path.read_text())
                    break
                except (FileNotFoundError, json.JSONDecodeError):
                    time.sleep(.05)
            assert result["pid"] == p.pid and result["exact"]
        servers = pid_list(rpc(env, "get_server_list", work_end, run))
        assert len(servers) == 1
        server = next(iter(servers))
        save(run / "server.identity.json", identity(server, env, minimum))
        clients = pid_list(rpc(env, "get_client_list " + str(server), work_end, run))
        assert clients == registered, (clients, registered)
        save(run / "membership.json", dict(server=server, clients=sorted(clients)))
        save(run / "gpu-during.json", dict(epoch=time.time(), rows=subprocess.check_output(
            ["nvidia-smi", "--query-compute-apps=pid,gpu_uuid,used_gpu_memory",
             "--format=csv,noheader"], text=True)))
        for p in children:
            p.stdin.write("release\n")
            p.stdin.flush()
        for p in children:
            p.wait(timeout=max(.01, work_end - time.monotonic()))
            assert p.returncode == 0
        success = True
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        cleanup_end = time.monotonic() + 120
        child_errors = []
        for p in children:
            try:
                stop(p, fds.get(p.pid))
                try:
                    p.wait(timeout=min(5, max(.01, cleanup_end - time.monotonic())))
                except subprocess.TimeoutExpired:
                    stop(p, fds.get(p.pid), signal.SIGKILL)
                    p.wait(timeout=max(.01, cleanup_end - time.monotonic()))
            except Exception as error:
                child_errors.append(dict(pid=p.pid, error=repr(error)))
        try:
            if controller is not None and controller.poll() is None:
                identity(controller.pid, env, minimum)
                pipe = run / "pipe"
                assert pipe.stat().st_uid == os.getuid() and pipe.stat().st_mode & 0o777 == 0o700
                for server in pid_list(rpc(env, "get_server_list", cleanup_end, run)):
                    identity(server, env, minimum)
                    clients = pid_list(rpc(env, "get_client_list " + str(server), cleanup_end, run))
                    assert not clients, ("refuse quit: clients still present", clients)
                rpc(env, "quit", cleanup_end, run)
                controller.wait(timeout=min(15, max(.01, cleanup_end - time.monotonic())))
        except Exception as error:
            cleanup_error = repr(error)  # No quit/kill of an unidentified service.
        after = None
        gpu_error = None
        try:
            after = subprocess.run(["nvidia-smi", "-i", "3", "--query-gpu=uuid,memory.used",
                                    "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5)
        except Exception as error:
            gpu_error = repr(error)
        save(run / "terminal.json", dict(work_success=success, cleanup_error=cleanup_error, child_errors=child_errors, gpu_error=gpu_error,
             clients={str(p.pid): p.returncode for p in children},
             controller_exit=None if controller is None else controller.poll(),
             gpu_after=None if after is None else after.stdout, gpu_query_exit=None if after is None else after.returncode, ended_epoch=time.time()))
        for fd in fds.values():
            os.close(fd)
        for handle in handles:
            handle.close()
    assert success and cleanup_error is None and controller.returncode == 0
    assert not child_errors and after is not None and after.returncode == 0 and after.stdout.strip() == GPU + ", 0"


if __name__ == "__main__":
    if sys.argv[1] == "client":
        client(int(sys.argv[2]), Path(sys.argv[3]))
    else:
        main(Path(sys.argv[1]))
