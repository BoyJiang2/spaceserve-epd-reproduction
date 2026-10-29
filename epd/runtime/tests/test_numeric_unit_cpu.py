"""CPU-MOCK orchestration contracts; no Ray, CUDA or actual transfer evidence."""
import copy
import math
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numeric_cache as native
import numeric_unit as unit
import test_numeric_cache_cpu as fixtures


PROFILE = 'f' * 64
UUIDS = ['CPU-MOCK-A', 'CPU-MOCK-B', 'CPU-MOCK-C']


class ClaimFixture:
    def __init__(self, clock, events):
        self.clock, self.events = clock, events
        self.phase, self.unit, self.requests, self.transfers = 'numeric', 'numeric', 0, 36
        self.deadline = clock.value + 1800
        self.config = dict(host='CPU-MOCK-host', uid=7, root=str(Path(__file__).resolve().parent),
                           gpu_uuids=UUIDS, cleanup_seconds=120, max_idle_bytes=10)
        self.inputs = dict(run_id='CPU-MOCK-unit', deploy_sha256='a' * 64)
        self.deployed = dict(boot_id='CPU-MOCK-boot', commit='b' * 40)
        self.resources = dict(gpus={u: dict(capacity_bytes=1 << 40) for u in UUIDS})
        self.issued_transfers = 0

    def verify_reservation(self): self.check()

    def check(self):
        if self.clock.value >= self.deadline: raise TimeoutError('CPU-MOCK common claim deadline')

    def admit_transfer(self):
        self.verify_reservation()
        if self.issued_transfers >= 36: raise ValueError('CPU-MOCK transfer37 refused')
        self.issued_transfers += 1
        self.events.append(('charge', self.issued_transfers - 1))


class BackendFixture:
    def __init__(self, claim, clock, events):
        self.claim, self.clock, self.events = claim, clock, events
        self.identities, self.allocations, self.timeouts = [], {}, []
        self.group_count, self.copies, self.next_pid = 0, [], 100
        self.fail_copy = self.bad_release = self.bad_identity = None
        self.partial_copy = self.advance_copy = self.bad_geometry = False

    def step(self, timeout):
        if not 0 < timeout <= 1800: raise ValueError('CPU-MOCK unbounded backend call')
        self.timeouts.append(timeout); self.clock.value += .2

    def create_group(self, uuids, *, timeout):
        self.step(timeout); self.group_count += 1; self.allocations = {}
        self.identities = []
        for uuid in reversed(uuids):
            self.next_pid += 1
            self.identities.append(dict(unit.identity_scope(self.claim, PROFILE), gpu_uuid=uuid,
                pid=self.next_pid, proc_start_ticks=self.next_pid * 10,
                cwd=self.claim.config['root'], endpoint='CPU-MOCK-namespace'))
        if self.bad_identity is not None:
            next(r for r in self.identities if r['gpu_uuid'] == self.bad_identity)['uid'] = -1
        self.events.append(('create', self.group_count))
        return copy.deepcopy(self.identities)

    def call(self, uuid, action, argument, *, timeout):
        self.step(timeout)
        identity = next(r for r in self.identities if r['gpu_uuid'] == uuid)
        if action == 'allocate':
            kind = argument
            shape = [3000, 64, 3584] if kind == 've' else [1, 2, 2, 16, 1, 1]
            if self.bad_geometry and uuid == UUIDS[1]: shape[2] += 1
            axis = 2 if kind == 'kv' else 0
            geometry = dict(kind=kind, shape=shape, stride=[math.prod(shape[i + 1:]) for i in range(len(shape))],
                            dtype='torch.float16', block_axis=axis, blocks=shape[axis],
                            elements=math.prod(shape), storage_bytes=math.prod(shape) * 2)
            row = dict(identity=copy.deepcopy(identity), geometry=geometry, handle=[identity['pid'] % 256] * 64,
                model_loaded=False, workload_scope='numeric_native_cache_no_model_weights',
                scratch_reserve_bytes=native.SCRATCH_RESERVE_BYTES, GPU_capacity_bytes=1 << 40,
                model_config_sha256='c' * 64, worker_source_sha256='d' * 64, probe_source_sha256='e' * 64)
            self.allocations[uuid] = row
            return copy.deepcopy(row)
        if action == 'prepare':
            self.events.append(('prepare', argument['ordinal']))
            row = copy.deepcopy(self.allocations[uuid]); row['transfer'] = copy.deepcopy(argument)
            row['source_validation'] = dict(full_equal=True, checked_elements=row['geometry']['elements'], seed=argument['seed'])
            return row
        if action == 'copy':
            transfer = argument['transfer']; self.copies.append(transfer['ordinal'])
            self.events.append(('copy', transfer['ordinal']))
            if transfer['ordinal'] == self.fail_copy: raise RuntimeError('CPU-MOCK native copy failure')
            if self.advance_copy: self.clock.value += 1700
            checked = self.allocations[uuid]['geometry']['elements'] - int(self.partial_copy)
            return dict(transfer=copy.deepcopy(transfer), source_identity=argument['source']['identity'],
                target_identity=copy.deepcopy(identity), geometry=copy.deepcopy(self.allocations[uuid]['geometry']),
                destination_validation=dict(full_equal=True, checked_elements=checked, seed=transfer['seed']),
                requires_importer_context_exit_before_source_release=True)
        if action == 'sync':
            self.events.append(('sync', uuid))
            return dict(identity=copy.deepcopy(identity), synchronized=True)
        raise ValueError('Unknown CPU-MOCK action')

    def close(self, uuid, identity, *, timeout):
        self.step(timeout); self.events.append(('close', uuid))
        return dict(identity=copy.deepcopy(identity), gpu_uuid=uuid,
            proc_observation=dict(path='/proc/' + str(identity['pid']), exists=uuid == self.bad_release,
                                  boot_id=identity['boot_id'], monotonic_s=self.clock.value),
            raw_nvml=dict(capacity_bytes=1 << 40, used_bytes=0, processes=[]))

    def known_identities(self): return copy.deepcopy(self.identities)


class NumericUnitCPU(unittest.TestCase):
    def setUp(self):
        self.clock = NS(value=100.0); self.events = []
        self.claim = ClaimFixture(self.clock, self.events)
        self.backend = BackendFixture(self.claim, self.clock, self.events)
        self.raw = []

    def emit(self, name, row):
        self.events.append(('journal', name, row.get('ordinal')))
        self.raw.append((name, copy.deepcopy(row)))

    def run_vector(self):
        return unit.execute(self.claim, self.backend, self.emit, PROFILE, clock=lambda: self.clock.value)

    def test_complete_vector_charges_journals_and_uses_fresh_lifetimes(self):
        result = self.run_vector()
        self.assertEqual(result['completed_transfers'], 36); self.assertEqual(result['fresh_groups'], 12)
        self.assertEqual(self.backend.copies, list(range(36))); self.assertEqual(self.claim.issued_transfers, 36)
        self.assertEqual(self.backend.group_count, 12)
        self.assertTrue(all(t > 0 for t in self.backend.timeouts))
        self.assertLess(self.backend.timeouts[-1], self.backend.timeouts[0])
        for ordinal in range(36):
            charge = self.events.index(('charge', ordinal))
            submitted = self.events.index(('journal', 'submitted', ordinal))
            prepare = self.events.index(('prepare', ordinal)); copy_event = self.events.index(('copy', ordinal))
            self.assertLess(charge, submitted); self.assertLess(submitted, prepare); self.assertLess(prepare, copy_event)
        with self.assertRaises(ValueError): self.claim.admit_transfer()

    def test_importer_exits_before_source_and_unused_actor(self):
        self.run_vector()
        vector = native.transfer_vector(UUIDS)
        closed = [event[1] for event in self.events if event[0] == 'close']
        expected = []
        for group in vector[::3]:
            source, target = group['source_uuid'], group['target_uuid']
            expected.extend([target, source, next(u for u in UUIDS if u not in (source, target))])
        self.assertEqual(closed, expected)

    def test_copy_failure_stops_without_refund_or_retry(self):
        self.backend.fail_copy = 1
        with self.assertRaisesRegex(RuntimeError, 'copy failure'): self.run_vector()
        self.assertEqual(self.backend.copies, [0, 1]); self.assertEqual(self.claim.issued_transfers, 2)
        self.assertEqual(self.backend.group_count, 1)
        closed = [e[1] for e in self.events if e[0] == 'close']
        self.assertEqual(len(closed), 3); self.assertEqual(closed[0], UUIDS[1])

    def test_partial_numeric_result_not_boolean_success(self):
        self.backend.partial_copy = True
        with self.assertRaisesRegex(ValueError, 'destination'): self.run_vector()
        self.assertEqual(self.backend.copies, [0]); self.assertEqual(self.backend.group_count, 1)

    def test_different_full_geometry_refused_before_copy(self):
        self.backend.bad_geometry = True
        with self.assertRaises(ValueError): self.run_vector()
        self.assertEqual(self.backend.copies, []); self.assertEqual(self.claim.issued_transfers, 0)

    def test_unconfirmed_importer_exit_stops_next_group_and_cleans_siblings(self):
        self.backend.bad_release = UUIDS[1]
        with self.assertRaisesRegex(ValueError, 'context exit'): self.run_vector()
        self.assertEqual(self.backend.group_count, 1)
        closed = [e[1] for e in self.events if e[0] == 'close']
        self.assertEqual(closed.count(UUIDS[1]), 1)
        self.assertEqual(set(closed), {UUIDS[1], UUIDS[2]})
        self.assertNotIn(UUIDS[0], closed)

    def test_failed_native_copy_with_unconfirmed_importer_retains_exporter(self):
        self.backend.fail_copy = 1; self.backend.bad_release = UUIDS[1]
        with self.assertRaisesRegex(RuntimeError, 'copy failure'): self.run_vector()
        closed = [e[1] for e in self.events if e[0] == 'close']
        self.assertEqual(closed, [UUIDS[1], UUIDS[2]])
        self.assertTrue(any(name == 'cleanup_blocked' for name, row in self.raw))
        self.assertEqual(self.backend.group_count, 1)

    def test_unknown_identity_is_not_signalled_known_siblings_are_cleaned(self):
        self.backend.bad_identity = UUIDS[1]
        with self.assertRaises(ValueError): self.run_vector()
        closed = [e[1] for e in self.events if e[0] == 'close']
        self.assertNotIn(UUIDS[1], closed); self.assertEqual(set(closed), {UUIDS[0], UUIDS[2]})

    def test_common_deadline_does_not_restart_per_group(self):
        self.backend.advance_copy = True
        deadline = self.claim.deadline
        with self.assertRaises(TimeoutError): self.run_vector()
        self.assertEqual(self.claim.deadline, deadline); self.assertEqual(self.backend.group_count, 1)
        self.assertEqual(self.backend.copies, [0])


class NumericIdentityCPU(unittest.TestCase):
    def setUp(self):
        fixtures.NativeCacheContracts.setUp(self)
        self.torch.cuda.synchronize = Mock()

    def test_identity_is_captured_once_then_reused_by_allocate_and_sync(self):
        identity = native.probe(self.worker, 'identity', None, self.torch)
        allocated = native.probe(self.worker, 'allocate', 'kv', self.torch)
        synced = native.probe(self.worker, 'sync', None, self.torch)
        self.assertEqual(allocated['identity'], identity)
        self.assertEqual(synced, dict(identity=identity, synchronized=True))
        self.worker.qualification_identity.assert_called_once()
        self.torch.cuda.synchronize.assert_called_once_with(self.worker.device)

    def test_external_identity_rejected_before_capture(self):
        with self.assertRaises(ValueError): native.probe(self.worker, 'identity', {'pid': 1}, self.torch)
        self.worker.qualification_identity.assert_not_called()

    def test_repeated_identity_is_not_retried(self):
        native.probe(self.worker, 'identity', None, self.torch)
        with self.assertRaises(ValueError): native.probe(self.worker, 'identity', None, self.torch)
        with self.assertRaises(ValueError): native.probe(self.worker, 'allocate', 'kv', self.torch)
        self.worker.qualification_identity.assert_called_once()

    def test_sync_requires_registered_identity(self):
        with self.assertRaises(ValueError): native.probe(self.worker, 'sync', None, self.torch)
        self.torch.cuda.synchronize.assert_not_called()

    def test_real_model_path_not_given_numeric_identity(self):
        self.worker.model_runner = object()
        with self.assertRaises(ValueError): native.probe(self.worker, 'identity', None, self.torch)
        self.worker.qualification_identity.assert_not_called()


if __name__ == '__main__': unittest.main()
