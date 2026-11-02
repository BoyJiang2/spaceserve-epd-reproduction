"""Parent-owned native36 admission, private head, raw observation and cleanup.

Only original independently approved GPU scopes can reach NVML or spawn. This
module produces raw receipts, never a G3 decision or formal-run authorization.
"""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import queue
import secrets
import signal
import socket
import stat
import subprocess
import sys
import threading
import time

from live_evidence import NvmlBackend, snapshot
from numeric_channel import NumericChannel
from numeric_cpu_driver import CONTEXT_SHA
from numeric_cpu_lifecycle import check_cpu_port, control_service_exception, terminate
from numeric_cpu_ray import PINNED_SOURCES, verify_sources
from numeric_cpu_receipts import publish, sync_directory
from numeric_descendants import HeadDescendants, HeadProc
from numeric_driver_process import owned_bytes
from numeric_execution import validate
from numeric_gcs import GCSActorReader
from numeric_head import construct_node, node_parameters
from numeric_parent_backend import NumericParentBackend
from numeric_release import NumericRelease
from numeric_rpc import NumericRPC
from numeric_unit import execute
from preflight_controller import authorize, booking_for_unit
from preflight_guard import Claim, digest, load_bound, verify_checkout
from project_config import paths_for

SOURCE = Path(__file__).resolve().parent


def load_execution(template, layout, config, inputs, owner):
    if Path(template).is_symlink(): raise ValueError('Linked numeric template refused')
    template = Path(template).resolve(strict=True)
    relative = template.relative_to(SOURCE).as_posix()
    manifest = load_bound(owner, inputs['source_manifest_file'], inputs['source_manifest_sha256'])
    pin = next(row for row in manifest['files'] if row['path'] == relative)
    raw = template.read_bytes()
    if template.is_symlink() or hashlib.sha256(raw).hexdigest() != pin['sha256']:
        raise ValueError('Numeric template differs from committed source manifest')
    spec = json.loads(raw)
    if 'source_manifest_sha256' in spec: raise ValueError('Static numeric template cannot self-reference its manifest')
    return validate(dict(spec, source_manifest_sha256=inputs['source_manifest_sha256']),
                    layout, config, inputs['source_manifest_sha256'])


def active_state(path, value, uid):
    if path.exists() or path.is_symlink():
        owned_bytes(path, uid)
    temporary = path.with_name(path.name+'.pending')
    publish(temporary, value)
    os.replace(temporary, path); sync_directory(path.parent)


def run(config, inputs, owner, template):
    deployed = authorize(config, inputs, owner)
    layout = paths_for(config); layout.require_scope('numeric')
    spec = load_execution(template, layout, config, inputs, owner)
    if abs(time.perf_counter()-time.monotonic()) > .001:
        raise RuntimeError('Shared Linux monotonic/perf_counter clock required')
    runtime = Path(config['root'])/'runtime'; runtime.mkdir(mode=0o700, exist_ok=True)
    if runtime.resolve() != runtime or runtime.stat().st_uid != config['uid']:
        raise ValueError('Exact owned numeric runtime required')
    import contextlib
    import fcntl
    with contextlib.ExitStack() as stack:
        for path in (layout.host_lock, runtime/'controller.lock'):
            fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            handle = stack.enter_context(os.fdopen(fd, 'r+'))
            info = os.fstat(handle.fileno())
            if info.st_uid != config['uid'] or not stat.S_ISREG(info.st_mode):
                raise ValueError('Unknown numeric lock owner/type')
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        active = runtime/'controller-active.json'
        if active.exists() and json.loads(owned_bytes(active, config['uid'])).get('state') != 'released':
            raise ValueError('Prior unit unconfirmed or failed; no next unit')
        booking_for_unit(config, inputs, owner, spec, int(time.time()*1000))
        nvml = NvmlBackend(); supervisor = None
        try:
            fresh = snapshot(config, inputs['run_id'], deployed, nvml, HeadProc())
            if any(gpu['processes'] for gpu in fresh['gpus'].values()):
                raise ValueError('Three genuinely empty approved GPUs required')
            claim = Claim(config, inputs, owner, 'numeric', 'numeric', None, fresh, now_ms=int(time.time()*1000))
            ledger = runtime/'gpu-budget.json'
            if ledger.exists():
                units = json.loads(owned_bytes(ledger, config['uid']))['units'].values()
                first = min((u['timing']['start_monotonic'] for u in units), default=time.perf_counter())
                if time.perf_counter()+1800+600 > first+340*60:
                    raise TimeoutError('Complete numeric plus cleanup cannot fit original340min')
            claim.reserve(ledger, spec)
            output = runtime/inputs['run_id']; output.mkdir(mode=0o700, exist_ok=False)
            publish(output/'execution.json', spec)
            active_state(active, dict(state='claimed', claim=claim.reservation_receipt, run_id=inputs['run_id']), config['uid'])
            supervisor = NativeController(claim, spec, output, layout, nvml)
            report = supervisor.run()
            active_state(active, dict(state=report['state'] if report['failure'] is None and not report['errors']
                else 'stopped_no_next_unit', terminal=str(output/'terminal.json'),
                terminal_sha256=hashlib.sha256((output/'terminal.json').read_bytes()).hexdigest()), config['uid'])
            return report
        finally:
            if supervisor is None or supervisor.sampler is None or not supervisor.sampler.is_alive(): nvml.close()


class NativeController:
    def __init__(self, claim, spec, output, layout, nvml):
        claim.verify_reservation()
        self.claim, self.spec, self.output, self.layout, self.nvml = claim, spec, Path(output), layout, nvml
        self.config, self.inputs, self.proc = claim.config, claim.inputs, HeadProc()
        self.root, self.run_id = Path(claim.config['root']), claim.inputs['run_id']
        self.release = NumericRelease(claim, spec['candidate_config_sha256'], nvml, self.proc,
                                      self.output/'numeric-lifecycle.jsonl')
        self.record = self.release.record
        self.base = layout.ray_tmp/('n-'+digest(self.run_id)[:12])
        self.parameters = node_parameters(str(self.base), 27180)
        self.processes, self.logs, self.errors = [], [], []
        self.collector = self.reader = self.driver = self.driver_identity = self.backend = self.channel = None
        self.cancelled, self.stop = threading.Event(), threading.Event()
        self.samples, self.sample_errors = queue.Queue(maxsize=32), []
        self.sample_ready = threading.Event()
        self.sampler = None; self.cleaning = False
        self.events_seen = 0; self.submissions, self.actor_processes, self.bootstrap = {}, {}, {}

    def check(self):
        self.claim.check()
        if not self.cleaning and (self.cancelled.is_set() or self.sample_errors
                or time.perf_counter() >= self.claim.deadline-self.config['cleanup_seconds']):
            raise RuntimeError('Numeric cancelled, observation failed or cleanup interval reached')

    def reap(self):
        for process in self.processes: process.poll()

    def register(self, process):
        if self.collector is None:
            values = [a.split('=',1)[1] for a in process.args if a.startswith('--log_dir=')]
            if len(values) != 1: raise ValueError('First actual private GCS session missing')
            session = Path(values[0]).parent
            if session.parent != self.base or not session.name.startswith('session_'):
                raise ValueError('Head session escapes exact fresh private base')
            self.collector = HeadDescendants(uid=self.config['uid'], boot_id=self.claim.deployed['boot_id'],
                root=self.root, run_id=self.run_id, session=session, supervisor_pid=os.getpid(),
                proc=self.proc, record=self.record, check=self.check)
        self.collector.register(process)

    def driver_events(self):
        path = self.output/'driver-events.jsonl'
        if not path.exists(): return
        info = path.stat()
        if info.st_size == 0:
            if path.is_symlink() or info.st_uid != self.config['uid'] or not stat.S_ISREG(info.st_mode):
                raise ValueError('Unknown empty driver journal')
            return
        raw = owned_bytes(path, self.config['uid'], 64*1024**2)
        lines = raw.split(b'\n')[:-1]
        if len(lines) < self.events_seen: raise ValueError('Original driver journal truncated')
        for line in lines[self.events_seen:]:
            event = json.loads(line)
            self.record('driver_original_event', raw_event=event, line_sha256=hashlib.sha256(line).hexdigest())
            if event['event'] == 'numeric_driver_actor_submitted':
                intent, submitted = event['intent'], event['submitted']
                group, slot = intent['group'], intent['slot']
                expected = dict(namespace=self.run_id, name='native-g'+str(group)+'-n'+str(slot),
                    group=group, slot=slot, allowed_gpu_uuids=self.config['gpu_uuids'], scope=self.release.scope)
                if (type(group) is not int or type(slot) is not int or not 0 <= group < 12 or not 0 <= slot < 3
                        or intent != expected or submitted['name'] != expected['name']
                        or submitted['namespace'] != self.run_id or submitted['detached'] is not True
                        or submitted['name'] in self.submissions):
                    raise ValueError('Original driver submission differs from unique parent intent')
                self.submissions[submitted['name']] = dict(submitted)
            self.events_seen += 1

    def actor_observations(self):
        if self.reader is None: return
        for name, submitted in self.submissions.items():
            if name in self.actor_processes: continue
            row = self.reader.read(submitted, min(self.claim.deadline, time.monotonic()+.5))
            if row['pid'] > 0 and row['state'] in ('ALIVE','PENDING_CREATION'):
                original = self.collector.known.get(row['pid'])
                if original is not None:
                    actual = self.collector.stable({'identity':original})['identity']
                    self.record('actor_original_process_bound', submitted=submitted, GCS=row, identity=actual)
                    self.actor_processes[name] = dict(actual)

    def consume_samples(self):
        while True:
            try: sample = self.samples.get_nowait()
            except queue.Empty: break
            for uuid, raw in sample['gpus'].items():
                if (raw['capacity_bytes'] != self.claim.resources['gpus'][uuid]['capacity_bytes']
                        or raw['used_bytes'] > raw['capacity_bytes']*65//100):
                    raise ValueError('Actual numeric memory/capacity exceeds common profile')
                for row in raw['processes']:
                    pid = row['pid']; original = self.collector.known.get(pid) if self.collector else None
                    if original is None or self.driver is not None and pid == self.driver.pid:
                        raise ValueError('Foreign or extra driver CUDA PID; no signal authorized')
                    observation = sample['process_observations'][uuid][str(pid)]
                    if observation.get('state') == 'original_registered_PID_absent_after_NVML':
                        registered = observation['original']
                        key = registered['pid'], registered['proc_start_ticks']
                        if (self.release.known.get(key) != registered or registered['gpu_uuid'] != uuid
                                or any(registered[k] != original[k] for k in ('pid','uid','proc_start_ticks','boot_id','cwd'))
                                or observation['proc_observation']['path'] != '/proc/'+str(pid)
                                or observation['proc_observation']['exists'] is not False
                                or observation['proc_observation']['boot_id'] != registered['boot_id']):
                            raise ValueError('Original sampled exit proof differs from registered actor')
                        actual = original
                    else: actual = observation['identity']
                    if not self.collector.same_identity(actual, original):
                        raise ValueError('Sampled GPU PID identity differs from original private descendant')
                    previous = self.bootstrap.get(pid)
                    binding = dict(identity=actual, gpu_uuid=uuid)
                    if previous is not None and previous != binding: raise ValueError('Bootstrap PID/UUID changed')
                    self.bootstrap[pid] = binding
            if self.backend is not None and self.backend.creating is None:
                identities = {(r['pid'],r['proc_start_ticks'],r['gpu_uuid']) for r in self.release.known.values()}
                for binding in self.bootstrap.values():
                    identity = binding['identity']
                    if (identity['pid'],identity['proc_start_ticks'],binding['gpu_uuid']) not in identities:
                        raise ValueError('Observed CUDA worker never bound to original numeric identity')

    def poll(self):
        self.check(); self.reap()
        if self.collector is not None: self.collector.collect()
        self.driver_events(); self.actor_observations(); self.consume_samples()

    def sample_process(self, pid, uuid):
        try: return self.proc.snapshot(pid, self.config['uid'])
        except (FileNotFoundError, ProcessLookupError) as error:
            known = [dict(row) for row in list(self.release.known.values())
                     if row['pid'] == pid and row['gpu_uuid'] == uuid]
            if len(known) != 1 or self.proc.exists(pid): raise
            boot = self.proc.boot(); observed = time.perf_counter()
            if boot != known[0]['boot_id'] or self.proc.exists(pid): raise
            return dict(state='original_registered_PID_absent_after_NVML', original=known[0],
                proc_observation=dict(path='/proc/'+str(pid), exists=False, boot_id=boot, monotonic_s=observed),
                original_error=repr(error), release_or_context_quiescence_granted=False)

    def sampling(self):
        last = None
        try:
            with (self.output/'nvml-raw.jsonl').open('x', encoding='utf8') as output:
                while not self.stop.is_set():
                    now = time.perf_counter()
                    sample = dict(monotonic_s=now, provider=self.nvml.version,
                                  gpus={u:self.nvml.read(u) for u in self.config['gpu_uuids']})
                    output.write(json.dumps(sample)+'\n'); output.flush(); os.fsync(output.fileno())
                    observations = {u:{str(p['pid']):self.sample_process(p['pid'],u)
                        for p in raw['processes']} for u,raw in sample['gpus'].items()}
                    sample['process_observations'] = observations
                    output.write(json.dumps(dict(event='sample_process_bindings', **sample))+'\n')
                    output.flush(); os.fsync(output.fileno())
                    for uuid,raw in sample['gpus'].items():
                        if (raw['capacity_bytes'] != self.claim.resources['gpus'][uuid]['capacity_bytes']
                                or raw['used_bytes'] > raw['capacity_bytes']*65//100):
                            raise ValueError('Raw numeric memory exceeds65percent')
                    if self.backend is None and any(r['processes'] for r in sample['gpus'].values()):
                        raise ValueError('Unexpected CUDA process before the private actor RPC backend')
                    if last is not None and now-last > 1: raise RuntimeError('Numeric raw memory observation gap exceeds1s')
                    if not self.cleaning and self.backend is not None: self.samples.put_nowait(sample)
                    self.sample_ready.set()
                    last = now
                    self.stop.wait(.2)
        except BaseException as error: self.sample_errors.append(repr(error))

    def start(self):
        self.check(); check_cpu_port(self.parameters['gcs_server_port'])
        if self.base.exists() or self.base.is_symlink(): raise ValueError('Private numeric head base is not fresh')
        self.base.mkdir(mode=0o700)
        package = Path(importlib.metadata.distribution('ray').locate_file('ray')).absolute()
        if importlib.metadata.version('ray') != '2.10.0': raise ValueError('Exact installed Ray2.10 required')
        if any(name in ('ray','torch','epdserve') or name.startswith(('ray.','torch.','epdserve.')) for name in sys.modules):
            raise ValueError('Hardware libraries imported before numeric parent source checks')
        verify_sources(package, dict(PINNED_SOURCES, **{'runtime_context.py':CONTEXT_SHA}), self.config['uid'])
        self.sampler = threading.Thread(target=self.sampling, daemon=True); self.sampler.start()
        while not self.sample_ready.wait(.05): self.check()
        self.check()
        node = construct_node(self.parameters, self.check, self.register, self.processes)
        if (Path(node.get_session_dir_path()) != self.collector.session
                or node.address != '127.0.0.1:'+str(self.parameters['gcs_server_port'])):
            raise ValueError('Actual private head address/session differs')
        self.reader = GCSActorReader.connect(node.address, package, self.record, self.check, expected_gpu_count=1)
        parent = self.proc.snapshot(os.getpid(), self.config['uid'])['identity']
        driver_spec = dict(config=self.config, inputs=self.inputs, owner=str(self.claim.owner),
            reservation=self.claim.reservation_receipt, execution=self.spec, parent=parent,
            parameters=self.parameters, session=str(self.collector.session), ray_package=str(package),
            nonce=secrets.token_hex(32), scope=self.release.scope)
        publish(self.output/'driver-spec.json', driver_spec)
        local, remote = socket.socketpair(); local.setblocking(False); remote.setblocking(False)
        self.channel = NumericChannel(local)
        try:
            log = (self.output/'driver-process.log').open('xb'); self.logs.append(log)
            argv = [sys.executable, '-B', str(SOURCE/'numeric_driver_process.py'),
                '--session-dir='+str(self.collector.session), '--spec', str(self.output/'driver-spec.json'),
                '--spec-sha256', hashlib.sha256((self.output/'driver-spec.json').read_bytes()).hexdigest(),
                '--fd', str(remote.fileno())]
            self.check()
            self.driver = subprocess.Popen(argv, cwd=self.root, env=dict(os.environ), pass_fds=(remote.fileno(),),
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            self.processes.append(self.driver); self.register(self.driver)
            self.driver_identity = dict(self.collector.known[self.driver.pid])
        finally: remote.close()
        rpc = NumericRPC(self.channel, self.run_id, driver_spec['nonce'], 'parent', self.record)
        self.backend = NumericParentBackend(self.claim, rpc, self.release, observe=self.poll)
        self.poll()

    def idle(self):
        raw = {u:self.nvml.read(u) for u in self.config['gpu_uuids']}
        self.record('numeric_idle_observation', raw_nvml=raw)
        if any(r['processes'] or r['used_bytes'] > self.config['max_idle_bytes'] for r in raw.values()):
            raise RuntimeError('Actual three CUDA contexts not confirmed idle')
        return raw

    def resolve_pending(self):
        if self.backend is None or self.backend.creating is None: return
        pending = self.backend.creating
        submitted = self.submissions.get(pending['name']); original = self.actor_processes.get(pending['name'])
        if (self.driver is None or self.driver.poll() is None or submitted is None or original is None
                or self.reader is None or self.proc.exists(original['pid'])):
            raise RuntimeError('FAILED_RELEASE_UNCONFIRMED original creation/driver/PID quiescence missing')
        row = self.reader.read(submitted, min(self.claim.deadline, time.monotonic()+.5))
        if row['state'] != 'DEAD' or row['pid'] != original['pid']:
            raise RuntimeError('FAILED_RELEASE_UNCONFIRMED original GCS actor/PID not terminal')
        raw = self.idle()
        self.record('creation_quiescence_confirmed', pending=pending, submitted=submitted, original=original,
                    GCS=row, raw_nvml=raw, original_PID_absent=True, driver_exit=self.driver.returncode)
        self.backend.creating = None

    def cleanup(self):
        self.cleaning = True
        if self.driver_identity is not None:
            terminate(self.driver_identity, self.proc, self.record, self.check, reap=self.reap)
            self.reap()
            if self.proc.exists(self.driver_identity['pid']): raise RuntimeError('Original driver still present')
        if self.channel is not None: self.channel.sock.close()
        self.poll(); self.resolve_pending()
        if self.release.known_identities(): raise RuntimeError('FAILED_RELEASE_UNCONFIRMED numeric actor registry not empty')
        self.idle()
        for name, submitted in self.submissions.items():
            original = self.actor_processes.get(name)
            if original is None: raise RuntimeError('Original submitted actor process never observed; retain head')
            row = self.reader.read(submitted, min(self.claim.deadline,time.monotonic()+.5))
            if row['state'] != 'DEAD' or row['pid'] != original['pid'] or self.proc.exists(original['pid']):
                raise RuntimeError('Original actor not terminal/absent; retain head')
        if any(p.poll() is None and (self.collector is None or p.pid not in self.collector.known) for p in self.processes):
            raise RuntimeError('Unregistered private head Popen; no signal authorized')
        if self.collector is not None:
            rows = list(self.collector.known.values())
            rows.sort(key=lambda row:0 if Path(row['exe']).name == 'raylet' else 1)
            for identity in rows: terminate(identity, self.proc, self.record, self.check, reap=self.reap)
            self.reap()
            if any(self.proc.exists(row['pid']) for row in rows): raise RuntimeError('Registered head PID still present')
        selected = self.scope_inventory()
        self.record('numeric_final_scope_inventory', selected=selected, unknown_signal_authorized=False)
        if selected: raise RuntimeError('Unregistered same-run processes remain; no unknown signal')
        return self.idle()

    def scope_inventory(self):
        selected = []
        for path in Path('/proc').iterdir():
            self.check()
            if not path.name.isdigit() or int(path.name) == os.getpid(): continue
            try:
                if path.stat().st_uid != self.config['uid']: continue
                try: cwd = (path/'cwd').resolve(strict=True)
                except PermissionError:
                    proof = control_service_exception(Path('/proc'), int(path.name))
                    if proof is None: raise RuntimeError('Final numeric candidate cwd unconfirmed')
                    self.record('numeric_verified_control_service_exception', pid=int(path.name), proof=proof,
                        scope='cwd permission only; no signalling or project ownership grant')
                    continue
                if not cwd.is_relative_to(self.root): continue
                if self.proc.environment(int(path.name)) == {'EXP_ROOT':str(self.root),'REPRO_RUN_ID':self.run_id}:
                    selected.append(self.proc.snapshot(int(path.name),self.config['uid']))
            except (FileNotFoundError,ProcessLookupError):
                if self.proc.exists(int(path.name)): raise
        return selected

    def source_snapshot(self, stage):
        manifest = load_bound(self.claim.owner, self.inputs['source_manifest_file'], self.inputs['source_manifest_sha256'])
        rows, errors = [], []
        for item in manifest['files']:
            try:
                path = self.layout.checkout/item['git_path']
                if not path.resolve(strict=True).is_relative_to(self.layout.checkout):
                    raise ValueError('Source census escaped original checkout')
                raw = owned_bytes(path, self.config['uid'], 32*1024**2)
                actual = hashlib.sha256(raw).hexdigest()
                rows.append(dict(path=item['path'], git_path=item['git_path'], bytes=len(raw),
                                 sha256=actual, expected_sha256=item['sha256']))
                if actual != item['sha256']: errors.append('changed:'+item['path'])
            except BaseException as error:
                errors.append(item['path']+':'+repr(error))
        try:
            if verify_checkout(self.config, self.inputs, self.claim.owner) != self.claim.deployed:
                raise ValueError('Final designated deployment identity changed')
        except BaseException as error: errors.append('checkout:'+repr(error))
        publish(self.output/('source-'+stage+'.json'), dict(stage=stage, observed_ms=int(time.time()*1000),
            source_manifest_sha256=self.inputs['source_manifest_sha256'], files=rows, errors=errors))
        if errors: raise ValueError('Actual source closure verification failed: '+repr(errors))

    def run(self):
        environment = {'EXP_ROOT':str(self.root), 'REPRO_RUN_ID':self.run_id,
            'REPRO_SOURCE_COMMIT':self.claim.deployed['commit'], 'REPRO_DEPLOY_SHA256':self.inputs['deploy_sha256'],
            'REPRO_PROFILE_SHA256':self.spec['candidate_config_sha256'], 'REPRO_GPU_UUIDS':json.dumps(self.config['gpu_uuids']),
            'REPRO_IDENTITY':'1', 'REPRO_REQUEST_IDENTITY':'0', 'REPRO_NUMERIC_ONLY':'1',
            'REPRO_ENDPOINT':'gcs://127.0.0.1:'+str(self.parameters['gcs_server_port']),
            'CUDA_VISIBLE_DEVICES':','.join(self.config['gpu_uuids']), 'PYTHONPATH':str(SOURCE),
            'CUDA_IPC_LIB_PATH':str(self.layout.asset('build/libcuda_ipc_utils.so')),
            'HF_HUB_OFFLINE':'1', 'TRANSFORMERS_OFFLINE':'1', 'PYTHONDONTWRITEBYTECODE':'1',
            'RAY_ADDRESS':'127.0.0.1:'+str(self.parameters['gcs_server_port'])}
        saved = {key:os.environ.get(key) for key in environment}
        old = {n:signal.getsignal(n) for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM)}
        failure = None; result = None; raw = {}; released = False
        try:
            os.environ.update(environment)
            for number in old: signal.signal(number, lambda n,f:self.cancelled.set())
            self.source_snapshot('before')
            self.start()
            result = execute(self.claim, self.backend, lambda event,data:self.record(event, **data),
                             self.spec['candidate_config_sha256'])
            self.poll()
        except BaseException as error:
            failure = dict(type=type(error).__name__, error=repr(error))
            try: self.record('numeric_parent_failed', failure=failure)
            except BaseException as journal_error: self.errors.append('failure journal:'+repr(journal_error))
        finally:
            try: raw = self.cleanup(); released = True
            except BaseException as error:
                self.errors.append('cleanup:'+repr(error))
                try: self.record('FAILED_RELEASE_UNCONFIRMED', error=repr(error), head_retained=True)
                except BaseException as journal_error: self.errors.append('cleanup journal:'+repr(journal_error))
            self.stop.set()
            if self.sampler is not None:
                self.sampler.join(timeout=2)
                if self.sampler.is_alive(): self.errors.append('sampler exit unconfirmed')
            self.errors.extend(self.sample_errors)
            try: self.source_snapshot('after')
            except BaseException as error: self.errors.append('final source:'+repr(error))
            if self.reader is not None:
                try: self.reader.close()
                except BaseException as error: self.errors.append('GCS close:'+repr(error))
            for log in self.logs:
                try: log.close()
                except BaseException as error: self.errors.append('process log close:'+repr(error))
            for number, handler in old.items(): signal.signal(number, handler)
            for key, value in saved.items():
                if value is None: os.environ.pop(key,None)
                else: os.environ[key] = value
        report = dict(state='released' if released else 'release_unconfirmed', failure=failure, errors=self.errors,
            result=result, run_id=self.run_id, source_commit=self.claim.deployed['commit'],
            claim=self.claim.reservation_receipt, actual_gpu_release=raw,
            evidence_state='raw_not_independently_reviewed', formal_admission='blocked')
        publish(self.output/'terminal.json', report)
        return report
