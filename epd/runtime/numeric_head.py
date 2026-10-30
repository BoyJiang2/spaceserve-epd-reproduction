"""Owned Ray2.10 Node construction primitive; not an authorization or GPU entrypoint."""
import contextlib
import hashlib
from pathlib import Path
import signal
import subprocess
import sys
import threading


SOURCE_SHA256 = {
    'node':'923e30633a4d2ea2ccfbe67b5c6211bbcb670738abb866825cbc318398c95b24',
    'services':'385604d4ecda5febb280435e1129512c5802c3d520581b6a7470ceeef4c8c60f',
    'parameter':'1242f4110da8f8acafeb1a6cd816addc8a8f322aa3f56fad5bf23cdbe3e1a0f2'}


def load_runtime():
    import ray
    from ray._private import node, services, parameter
    if ray.__version__ != '2.10.0': raise ValueError('Exact reviewed Ray2.10.0 required')
    for name, module in (('node',node),('services',services),('parameter',parameter)):
        if hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() != SOURCE_SHA256[name]:
            raise ValueError('Installed Ray source differs: '+name)
    return node.Node, parameter.RayParams, services


def node_parameters(temp_dir, port, *, gpu_count=3):
    path = Path(temp_dir)
    if (not path.is_absolute() or '..' in path.parts or str(path) != str(temp_dir)
            or len(str(path)) > 48 or type(port) is not int or not 1024 <= port <= 65535
            or type(gpu_count) is not int or gpu_count not in (0,3)):
        raise ValueError('Frozen short private head directory/port and exact GPU count required')
    address='127.0.0.2' if gpu_count==0 else '127.0.0.1'
    return dict(temp_dir=str(path), gcs_server_port=port, node_ip_address=address,
        raylet_ip_address=address, num_cpus=3, num_gpus=gpu_count,
        object_store_memory=128<<20, memory=512<<20,
        include_dashboard=False, no_monitor=True, include_log_monitor=False, _system_config={})


@contextlib.contextmanager
def deferred_signals(check):
    """Background-thread delivery may schedule a Python handler on the main thread."""
    numbers = (signal.SIGTERM, signal.SIGINT, signal.SIGALRM)
    previous = {number:signal.getsignal(number) for number in numbers}
    cancelled = set()
    def remember(number, frame): cancelled.add(number)
    def controlled_check():
        check()
        if any(signal.getsignal(number) is not remember for number in numbers):
            raise RuntimeError('Owned head controlled signal handler changed')
        if cancelled: raise RuntimeError('Owned head startup cancelled: '+repr(sorted(cancelled)))
    try:
        for number in numbers: signal.signal(number, remember)
        if {signal.SIGTERM,signal.SIGALRM} & signal.pthread_sigmask(signal.SIG_BLOCK, set()):
            raise RuntimeError('Supervisor already masks controlled shutdown signals')
        yield controlled_check
    finally:
        for number, handler in previous.items(): signal.signal(number, handler)


@contextlib.contextmanager
def registered_spawns(services, check, register, processes):
    """Caller installs non-raising cancellation handlers before loading Ray."""
    original = services.ConsolePopen
    if original.__init__ is not subprocess.Popen.__init__:
        raise ValueError('Unexpected Linux ConsolePopen implementation')
    class RegisteredPopen(original):
        def __init__(self, *args, **kwargs):
            check()
            # No new inherited mask or preexec wrapper; preserve Ray's official child policy.
            super().__init__(*args, **kwargs)
            processes.append(self)  # Keep the real Popen even if identity/durable recording fails.
            register(self)
            check()

    services.ConsolePopen = RegisteredPopen
    try:
        yield
    finally:
        services.ConsolePopen = original


def construct_node(parameters, check, register, processes):
    """Caller owns authorization, private-directory/port checks and all final cleanup.

    `processes` must survive constructor exceptions in the independent supervisor;
    registration must bind actual UID/startticks/root/session and fsync the receipt.
    No generic Ray shutdown is used here, including on partial constructor failure.
    """
    expected = node_parameters(parameters['temp_dir'], parameters['gcs_server_port'],
                               gpu_count=parameters['num_gpus'])
    if parameters != expected or processes:
        raise ValueError('Exact fresh Node parameters and empty owned registry required')
    check()
    if sys.platform != 'linux' or threading.current_thread() is not threading.main_thread():
        raise RuntimeError('Owned Node startup requires the Linux main thread')
    with deferred_signals(check) as controlled_check:
        Node, RayParams, services = load_runtime()
        with registered_spawns(services, controlled_check, register, processes):
            node = Node(RayParams(**parameters), head=True, shutdown_at_exit=False, spawn_reaper=False)
        controlled_check()
    if (node.kernel_fate_share is not False or node.address != parameters['node_ip_address']+':'+str(parameters['gcs_server_port'])):
        raise ValueError('Actual Node fate-sharing or loopback address differs')
    return node
