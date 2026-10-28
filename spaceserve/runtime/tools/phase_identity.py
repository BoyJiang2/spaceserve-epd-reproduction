"""Read-only PID/ctime/UID terminal checks reused from the reviewed capture helper."""
def same_process_live(pid, created):
    import psutil
    try:
        process = psutil.Process(pid)
        if process.create_time() != created:
            return False
        if process.uids().real != 2147:
            raise RuntimeError('matching process identity has unexpected UID')
        return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False
    except psutil.AccessDenied as error:
        raise RuntimeError('cannot confirm process absence; do not capture bulk files') from error


def validate_terminal(started, terminal):
    keys = ('controller_id', 'pid', 'process_created', 'started_unix')
    if any(started[key] != terminal.get(key) for key in keys) or type(terminal.get('exit_code')) is not int:
        raise RuntimeError('phase exit does not belong to the actual initial controller')
    if same_process_live(started['pid'], started['process_created']):
        raise RuntimeError('phase controller still live; no bulk capture')
    if type(terminal.get('child_pid')) is not int or type(terminal.get('child_created')) not in (float, int):
        raise RuntimeError('terminal receipt missing actual child identity')
    if same_process_live(terminal['child_pid'], terminal['child_created']):
        raise RuntimeError('phase child still live; no bulk capture')

