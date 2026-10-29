"""Native36 importer-before-exporter cleanup; no Ray shutdown or GPU imports."""
import json
import os
from pathlib import Path
import signal
import stat
import time

from numeric_unit import identity_scope, validate_identity, validate_release
from live_evidence import ProcReader


class NumericProc(ProcReader):
    def exists(self, pid):
        try: (Path('/proc')/str(pid)).stat()
        except FileNotFoundError: return False
        return True

    def open_pidfd(self, pid):
        if not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
            raise RuntimeError('Stable Linux pidfd signalling required; no numeric-PID fallback')
        return os.pidfd_open(pid, 0)

    def signal_pidfd(self, descriptor, number):
        signal.pidfd_send_signal(descriptor, number, None, 0)

    def close_pidfd(self, descriptor): os.close(descriptor)

    def environment(self, pid):
        wanted = {b'EXP_ROOT', b'REPRO_RUN_ID'}
        result = {}
        for field in (Path('/proc')/str(pid)/'environ').read_bytes().split(b'\0'):
            key, separator, value = field.partition(b'=')
            if separator and key in wanted:
                name = key.decode('ascii')
                if name in result: raise ValueError('Duplicate numeric process scope key')
                result[name] = value.decode('utf8')
        return result


class NumericRelease:
    def __init__(self, claim, profile_sha256, nvml, proc, journal, *,
                 clock=time.perf_counter, sleep=time.sleep):
        self.claim, self.nvml, self.proc, self.journal = claim, nvml, proc, Path(journal)
        self.scope = identity_scope(claim, profile_sha256)
        self.clock, self.sleep = clock, sleep
        self.known, self.released, self.attempted, self.dependencies = {}, set(), set(), {}
        expected = Path(self.scope['root'])/'runtime'/self.scope['run_id']/'numeric-lifecycle.jsonl'
        if self.journal != expected:
            raise ValueError('Numeric journal must belong to this exact claimed unit')
        for path in (self.journal.parent, *self.journal.parent.parents):
            if path.is_symlink(): raise ValueError('Linked numeric journal ancestry')
            if path.is_relative_to(Path(self.scope['root'])):
                if not path.is_dir() or path.stat().st_uid != self.scope['uid']:
                    raise ValueError('Numeric journal parent is not an owned directory')
        with self.journal.open('x', encoding='utf8'):
            pass
        self.record('supervisor_registry_started', scope=self.scope)

    def record(self, event, **data):
        # The parent supervisor owns this journal; copy is allowed only after fsync succeeds.
        descriptor = os.open(self.journal, os.O_WRONLY | os.O_APPEND | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(descriptor, 'a', encoding='utf8') as output:
            info = os.fstat(output.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != self.scope['uid']:
                raise ValueError('Numeric journal is not an owned regular file')
            output.write(json.dumps(dict(event=event, monotonic_s=self.clock(), **data))+'\n')
            output.flush(); os.fsync(output.fileno())

    def live_identity(self, identity):
        actual = self.proc.identity(identity['pid'], self.scope['uid'])
        if any(actual.get(k) != identity[k] for k in ('pid', 'uid', 'proc_start_ticks', 'boot_id', 'cwd')):
            raise ValueError('Numeric process identity changed; refuse signal')
        # Read only this already UID/start/root-bound process, never dump its environment.
        environment = self.proc.environment(identity['pid'])
        if environment != {'EXP_ROOT':self.scope['root'], 'REPRO_RUN_ID':self.scope['run_id']}:
            raise ValueError('Actual numeric root/RUNID differs; refuse signal')
        if self.proc.identity(identity['pid'], self.scope['uid']) != actual:
            raise ValueError('Numeric process changed during scope observation')

    def register(self, identity):
        validate_identity(identity, self.scope, self.claim.config['gpu_uuids'])
        key = identity['pid'], identity['proc_start_ticks']
        if key in self.known or any(r['gpu_uuid'] == identity['gpu_uuid']
                                  for k, r in self.known.items() if k not in self.released):
            raise ValueError('Duplicate/unreleased numeric actor')
        self.live_identity(identity)
        self.record('actor_registered', identity=identity)
        self.known[key] = dict(identity)

    def mapping_possible(self, source, importer):
        for row in (source, importer):
            key = row['pid'], row['proc_start_ticks']
            if self.known.get(key) != row or key in self.released:
                raise ValueError('Only registered live actors can enter an IPC dependency')
            self.live_identity(row)
        source_key = source['pid'], source['proc_start_ticks']
        target_key = importer['pid'], importer['proc_start_ticks']
        if source_key == target_key:
            raise ValueError('Native IPC source and importer must differ')
        if source_key in self.dependencies and self.dependencies[source_key] != target_key:
            raise ValueError('A fresh actor may not change importer')
        self.record('mapping_possible', source=source, importer=importer)
        self.dependencies[source_key] = target_key

    def close(self, uuid, identity, *, timeout):
        key = identity['pid'], identity['proc_start_ticks']
        if (identity['gpu_uuid'] != uuid or self.known.get(key) != identity
                or key in self.released or key in self.attempted):
            raise ValueError('Exact unattempted numeric actor required')
        if self.dependencies.get(key) is not None and self.dependencies[key] not in self.released:
            self.record('cleanup_blocked', identity=identity, importer=self.dependencies[key])
            raise RuntimeError('Importer exit unconfirmed; retain exporter')
        start = self.clock(); end = min(start+timeout, self.claim.deadline)
        if not 0 < timeout <= 1800 or end <= start:
            raise TimeoutError('No bounded cleanup time remains')
        self.attempted.add(key)
        descriptor = None
        try:
            term_sent = kill_sent = False
            while self.clock() < end:
                try:
                    self.live_identity(identity); exists = True
                except FileNotFoundError as error:
                    directory_exists = self.proc.exists(identity['pid'])
                    self.record('proc_identity_lookup_failed', identity=identity, error=repr(error),
                        directory_observation=dict(path='/proc/'+str(identity['pid']), exists=directory_exists,
                            boot_id=self.proc.boot(), monotonic_s=self.clock()))
                    if directory_exists:
                        raise RuntimeError('Numeric identity unavailable while /proc PID still exists')
                    exists = False
                raw = self.nvml.read(uuid)
                observation = dict(path='/proc/'+str(identity['pid']), exists=exists,
                                   boot_id=self.proc.boot(), monotonic_s=self.clock())
                self.record('release_observation', identity=identity, proc_observation=observation, raw_nvml=raw)
                if self.clock() >= end: break
                if not exists:
                    receipt = dict(identity=identity, gpu_uuid=uuid, proc_observation=observation, raw_nvml=raw)
                    try:
                        validate_release(receipt, identity, self.claim.resources['gpus'][uuid]['capacity_bytes'],
                                         self.claim.config['max_idle_bytes'], start, self.clock())
                    except ValueError:
                        pass  # Process exit alone is insufficient; wait for the actual CUDA context.
                    else:
                        self.record('actor_released', receipt=receipt)
                        self.released.add(key)
                        return receipt
                if exists and (not term_sent or self.clock()-start >= 1 and not kill_sent):
                    number = signal.SIGTERM if not term_sent else signal.SIGKILL
                    if descriptor is None:
                        try: descriptor = self.proc.open_pidfd(identity['pid'])
                        except ProcessLookupError:
                            self.sleep(min(.05, max(0, end-self.clock())))
                            continue
                    try:
                        self.live_identity(identity)  # Recheck immediately before this exact PID signal.
                    except FileNotFoundError:
                        self.sleep(min(.05, max(0, end-self.clock())))
                        continue
                    self.record('signal_intent', identity=identity, signal=int(number))
                    if self.clock() >= end: break
                    try:
                        self.proc.signal_pidfd(descriptor, number)
                    except ProcessLookupError:
                        self.record('signal_pid_disappeared', identity=identity, signal=int(number))
                    else:
                        self.record('signal_sent', identity=identity, signal=int(number))
                    if number == signal.SIGTERM: term_sent = True
                    else: kill_sent = True
                self.sleep(min(.05, max(0, end-self.clock())))
            self.record('FAILED_RELEASE_UNCONFIRMED', identity=identity,
                        retained_exporters=[list(k) for k, dependency in self.dependencies.items() if dependency == key])
            raise TimeoutError('FAILED_RELEASE_UNCONFIRMED: no new transfer or implicit shutdown')
        finally:
            if descriptor is not None: self.proc.close_pidfd(descriptor)

    def known_identities(self):
        return [dict(row) for key, row in self.known.items() if key not in self.released]
