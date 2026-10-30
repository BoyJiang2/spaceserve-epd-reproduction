"""Read-only Ray descendant ownership; no signalling, GPU imports or cleanup grant."""
from pathlib import Path

from numeric_release import NumericProc


class HeadProc(NumericProc):
    def snapshot(self, pid, uid):
        base = Path('/proc')/str(pid)
        status = (base/'status').read_text()
        uids = next(line.split()[1:] for line in status.splitlines() if line.startswith('Uid:'))
        if len(uids) != 4 or any(int(value) != uid for value in uids):
            raise ValueError('Foreign descendant UID; no further inspection')
        stat = (base/'stat').read_text()
        fields = stat[stat.rfind(')')+2:].split()
        argv = (base/'cmdline').read_bytes().split(b'\0')
        if argv and argv[-1] == b'': argv.pop()
        identity = dict(pid=pid, uid=uid, proc_start_ticks=int(fields[19]), ppid=int(fields[1]),
            boot_id=self.boot(), cwd=str((base/'cwd').resolve(strict=True)),
            exe=str((base/'exe').resolve(strict=True)), argv=[value.decode('utf8') for value in argv],
            environment=self.environment(pid))
        return dict(identity=identity, raw=dict(status=status, stat=stat, argv=identity['argv']))

    def children(self, pid, check):
        tasks = Path('/proc')/str(pid)/'task'
        tids = sorted(tasks.iterdir(), key=lambda path:int(path.name))
        if len(tids) > 4096: raise ValueError('Head TID inventory exceeds frozen bound')
        result = []
        for task in tids:
            check()
            raw = (task/'children').read_text()
            children = [int(value) for value in raw.split()]
            if any(value <= 0 for value in children): raise ValueError('Invalid child PID')
            result.append(dict(tid=int(task.name), raw=raw, children=children))
        return result


class HeadDescendants:
    def __init__(self, *, uid, boot_id, root, run_id, session, supervisor_pid, proc, record, check):
        self.uid, self.boot, self.root, self.run_id = uid, boot_id, Path(root), run_id
        self.session, self.supervisor_pid = Path(session), supervisor_pid
        if (not self.root.is_absolute() or not self.session.is_absolute()
                or '..' in self.root.parts or '..' in self.session.parts or not run_id
                or type(uid) is not int or type(supervisor_pid) is not int or supervisor_pid <= 0):
            raise ValueError('Exact owned scope and private session required')
        self.proc, self.record, self.check = proc, record, check
        self.known = {}

    def observe(self, pid):
        self.check()
        row = self.proc.snapshot(pid, self.uid)
        value = row['identity']
        if (value['pid'] != pid or value['uid'] != self.uid or value['boot_id'] != self.boot
                or type(value['proc_start_ticks']) is not int or value['proc_start_ticks'] < 1
                or not Path(value['cwd']).is_relative_to(self.root)
                or value['environment'] != {'EXP_ROOT':str(self.root), 'REPRO_RUN_ID':self.run_id}):
            raise ValueError('Head process scope differs')
        previous = self.known.get(pid)
        if previous is not None and previous['proc_start_ticks'] != value['proc_start_ticks']:
            raise ValueError('Known head PID reused')
        return row

    @staticmethod
    def same_identity(left, right):
        return {k:v for k,v in left.items() if k != 'argv'} == {k:v for k,v in right.items() if k != 'argv'}

    def stable(self, observed):
        actual = self.observe(observed['identity']['pid'])
        if not self.same_identity(actual['identity'], observed['identity']):
            raise ValueError('Head identity changed during observation')
        return actual

    def register(self, process):
        self.check()
        if process.poll() is not None: raise ValueError('Direct Popen already exited')
        row = self.observe(process.pid)
        if row['identity']['ppid'] != self.supervisor_pid or process.pid in self.known:
            raise ValueError('Direct process is not a fresh child of this supervisor')
        flags = {'--session-dir','--session_dir','--log-dir','--log_dir','--runtime-env-dir',
                 '--raylet_socket_name','--store_socket_name','--object-store-name','--raylet-name'}
        argv = row['identity']['argv']
        if not isinstance(process.args, (list,tuple)) or list(process.args) != argv:
            raise ValueError('Actual direct Popen argv differs from held command')
        values = {}
        for arg in argv:
            name, separator, value = arg.partition('=')
            if name not in flags: continue
            canonical = name.replace('_','-')
            if (not separator or canonical in values or not Path(value).is_absolute()
                    or not Path(value).is_relative_to(self.session) or '..' in Path(value).parts
                    or str(Path(value)) != value
                    or canonical == '--session-dir' and Path(value) != self.session):
                raise ValueError('Duplicate/conflicting private session parameter')
            values[canonical] = value
        if not values: raise ValueError('Exact selected private session parameter absent')
        final = self.stable(row)
        if final['identity']['argv'] != argv: raise ValueError('Direct Popen argv changed during registration')
        self.record('head_process_registered', observation_before=row, observation_after=final, parent=None, popen_args=list(process.args), session=str(self.session))
        self.check()
        self.known[process.pid] = row['identity']

    def collect(self):
        pending, visited = list(self.known), set()
        while pending:
            self.check()
            pid = pending.pop(0)
            if pid in visited: continue
            visited.add(pid)
            if len(visited) > 4096: raise ValueError('Head descendant inventory exceeds frozen bound')
            try:
                parent = self.observe(pid)
            except (FileNotFoundError, ProcessLookupError):
                if self.proc.exists(pid):raise
                self.record('head_known_pid_absent',identity=dict(self.known[pid]),
                    release_or_quiescence_granted=False)
                continue
            if not self.same_identity(parent['identity'], self.known[pid]): raise ValueError('Known parent identity changed')
            tasks = self.proc.children(pid, self.check)
            parent_after = self.stable(parent)
            self.record('head_children_observed', parent_before=parent, parent_after=parent_after, tasks=tasks)
            for child_pid in sorted({child for task in tasks for child in task['children']}):
                self.check()
                if len(self.known) >= 4096 and child_pid not in self.known:
                    raise ValueError('Head descendant inventory exceeds frozen bound')
                child = self.observe(child_pid)
                value = child['identity']
                if value['ppid'] != pid or value['proc_start_ticks'] < parent['identity']['proc_start_ticks']:
                    raise ValueError('Actual child parent/start relation differs')
                parent_after = self.stable(parent); child_after = self.stable(child)
                if child_pid in self.known and not self.same_identity(self.known[child_pid], value):
                    raise ValueError('Known descendant identity changed')
                event = 'head_descendant_verified' if child_pid in self.known else 'head_descendant_registered'
                self.record(event, observation_before=child, observation_after=child_after,
                    parent_before=parent, parent_after=parent_after, session=str(self.session),
                    proof='verified_original_parent_chain')
                self.check()
                self.known[child_pid] = value
                pending.append(child_pid)
        return [dict(value) for value in self.known.values()]
