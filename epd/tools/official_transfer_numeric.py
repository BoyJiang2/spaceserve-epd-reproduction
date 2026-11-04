"""Explicitly synchronized tiny-tensor diagnostic; not a model or performance test."""
import contextlib
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import signal
import sys
import time
import traceback

LIB = "/local/boyjiang/epd/assets/build/libcuda_ipc_utils.so"
LIB_SHA = "fdb86ae5a5658d17c98cc8cc17e3b0d911433bf270fb8bcfbb381a99f66a970e"
CFG = [1, 0, 1, 0, 1, 0]
SRC, DST = [4, 1, 3], [0, 4, 2]


def save(path, value):
    with open(path, "x") as f:
        json.dump(value, f, indent=2)
        f.write("\n")


def receive(conn, deadline):
    if not conn.poll(max(0, deadline - time.monotonic())):
        raise TimeoutError("shared diagnostic deadline exceeded")
    return conn.recv()


def worker(role, conn, run, deadline):
    with open(run / (role + ".stdout"), "x", buffering=1) as out, open(
        run / (role + ".stderr"), "x", buffering=1
    ) as err, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            import torch
            rank = {"E": 0, "P": 1, "D": 2}[role]
            torch.cuda.set_device(rank)
            assert hashlib.sha256(Path(LIB).read_bytes()).hexdigest() == LIB_SHA
            torch.ops.load_library(LIB)
            ops = torch.ops.block_migration_ops
            props = torch.cuda.get_device_properties(rank)
            identity = dict(role=role, pid=os.getpid(), rank=rank,
                            device=str(props), library=LIB, library_sha256=LIB_SHA,
                            torch=torch.__version__, executable=sys.executable,
                            caching_disabled=os.environ["PYTORCH_NO_CUDA_MEMORY_CACHING"])
            save(run / (role + ".identity.json"), identity)
            if role == "E":
                source = (torch.arange(120, dtype=torch.int32).reshape(5, 3, 8) % 1024).to(
                    device=rank, dtype=torch.float16)
                torch.cuda.synchronize(rank)
                conn.send(ops.get_ipc_mem_handle(source))
                assert receive(conn, deadline + 120) == "release"
            elif role == "P":
                handle = receive(conn, deadline)
                target = torch.full((5, 3, 8), -2048, device=rank, dtype=torch.float16)
                torch.cuda.synchronize(rank)
                assert ops.register_ipc_mem_handle_encoding(handle, CFG, CFG)
                ops.migrate_blocks_encoding(1, 1, 0, SRC, 1, 1, 0, 0, DST, target)
                torch.cuda.synchronize(rank)
                actual = target.cpu()
                expected = torch.full((5, 3, 8), -2048, dtype=torch.float16)
                original = torch.arange(120).reshape(5, 3, 8).to(torch.float16)
                for a, b in zip(SRC, DST):
                    expected[b] = original[a]
                result = dict(path="E_to_P_embedding", exact=torch.equal(actual, expected),
                              mismatches=int((actual != expected).sum()),
                              expected_sha256=hashlib.sha256(expected.numpy().tobytes()).hexdigest(),
                              actual_sha256=hashlib.sha256(actual.numpy().tobytes()).hexdigest())
                save(run / "embedding.json", result)
                assert result["exact"], result
                source = (torch.arange(480, dtype=torch.int32).reshape(2, 2, 5, 3, 2, 4) % 1024).to(
                    device=rank, dtype=torch.float16)
                torch.cuda.synchronize(rank)
                conn.send(ops.get_ipc_mem_handle(source))
                assert receive(conn, deadline + 120) == "release"
            else:
                handle = receive(conn, deadline)
                target = torch.full((2, 2, 5, 3, 2, 4), -2048, device=rank, dtype=torch.float16)
                torch.cuda.synchronize(rank)
                assert ops.register_ipc_mem_handle_context(handle, 2, 2, CFG, CFG)
                try:
                    ops.migrate_blocks_context(1, 1, 0, SRC, 1, 1, 0, 0, DST, target)
                    torch.cuda.synchronize(rank)
                    actual = target.cpu()
                    expected = torch.full((2, 2, 5, 3, 2, 4), -2048, dtype=torch.float16)
                    original = torch.arange(480).reshape(2, 2, 5, 3, 2, 4).to(torch.float16)
                    for a, b in zip(SRC, DST):
                        expected[:, :, b] = original[:, :, a]
                    result = dict(path="P_to_D_KV", exact=torch.equal(actual, expected),
                                  mismatches=int((actual != expected).sum()),
                                  expected_sha256=hashlib.sha256(expected.numpy().tobytes()).hexdigest(),
                                  actual_sha256=hashlib.sha256(actual.numpy().tobytes()).hexdigest())
                    save(run / "kv.json", result)
                    assert result["exact"], result
                finally:
                    assert ops.unregister_ipc_mem_handle_context(2, 2, CFG, CFG)
                conn.send("complete")
            print(json.dumps({"role": role, "completed": True}), flush=True)
        except BaseException:
            traceback.print_exc()
            raise


def join_before(process, deadline):
    process.join(max(0, deadline - time.monotonic()))
    if process.is_alive():
        raise TimeoutError("child did not exit before shared deadline")
    assert process.exitcode == 0, (process.name, process.exitcode)


def stop_child(process, fd, sig):
    if not process.is_alive():
        return
    try:
        if fd is not None:
            signal.pidfd_send_signal(fd, sig)
        elif sig == signal.SIGTERM:
            process.terminate()
        else:
            process.kill()
    except ProcessLookupError:
        pass  # The owned child exited between observation and signaling.


def interrupt(signum, frame):
    raise TimeoutError("supervisor received signal " + str(signum))


def main():
    run = Path(sys.argv[1]).resolve()
    assert run.parent == Path("/local/boyjiang/epd/runs") and not run.exists()
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "0,1,2"
    assert os.environ["PYTORCH_NO_CUDA_MEMORY_CACHING"] == "1"
    signal.signal(signal.SIGTERM, interrupt)
    run.mkdir()
    deadline = time.monotonic() + 180
    ctx = mp.get_context("spawn")
    children, channels, fds = {}, {}, {}
    ok = False
    try:
        for role in ("E", "P", "D"):
            parent, child = ctx.Pipe()
            p = ctx.Process(target=worker, args=(role, child, run, deadline), name=role)
            p.start()
            children[role], channels[role] = p, parent
            fds[role] = os.pidfd_open(p.pid)
            child.close()
            save(run / (role + ".spawn.json"), dict(pid=p.pid, parent=os.getpid(),
                uid=os.getuid(), boot=Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
                stat=Path("/proc/" + str(p.pid) + "/stat").read_text(), created_epoch=time.time()))
        channels["P"].send(receive(channels["E"], deadline))
        channels["D"].send(receive(channels["P"], deadline))
        assert receive(channels["D"], deadline) == "complete"
        join_before(children["D"], deadline)
        channels["P"].send("release")
        join_before(children["P"], deadline)
        channels["E"].send("release")
        join_before(children["E"], deadline)
        ok = True
    finally:
        cleanup_deadline = time.monotonic() + 120
        for role in ("D", "P", "E"):
            if role in children:
                stop_child(children[role], fds.get(role), signal.SIGTERM)
        for p in children.values():
            p.join(max(0, min(5, cleanup_deadline - time.monotonic())))
        for role, p in children.items():
            stop_child(p, fds.get(role), signal.SIGKILL)
        for p in children.values():
            p.join(max(0, cleanup_deadline - time.monotonic()))
        exits = {role: p.exitcode for role, p in children.items()}
        save(run / "terminal.json", dict(success=ok, exits=exits, ended_epoch=time.time(),
            scope="explicit synchronization, tiny tensors, existing binary only"))
        for fd in fds.values():
            os.close(fd)
        for conn in channels.values():
            conn.close()
    assert ok and all(v == 0 for v in exits.values())


if __name__ == "__main__":
    main()
