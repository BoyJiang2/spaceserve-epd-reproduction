"""Exercise the production shared client with a CPU-only fake HTTP transport."""
import asyncio
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fixed_unit
import selected_client
from preflight_guard import digest
import test_selected_unit


class Buffer(io.StringIO):
    def close(self):
        pass


class SelectedClientTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        fixture = test_selected_unit.SelectedUnitTests()
        fixture.setUp()
        self.spec = fixture.spec
        self.calls, self.files = [], {}
        outer = self

        class Reply:
            status = 200

            def __init__(self, body, index):
                self.body, self.index = body, index

            async def __aenter__(self):
                await asyncio.sleep(0)
                return self

            async def __aexit__(self, *args):
                pass

            async def read(self):
                await asyncio.sleep(.001)
                count = self.body['max_tokens']
                return json.dumps({'timestamps': [time.perf_counter()] * count,
                    'processed_prompt_token_ids': [1, 2], 'output_token_ids': list(range(count)),
                    'repro_api_identity': {'fixture': 'API'}, 'repro_worker_route': [{'fixture': 'worker'}],
                    'repro_request_id': f'fixture-{self.index}'}).encode()

        class Session:
            _retry_connection = True

            def __init__(self, **kwargs):
                assert kwargs['trust_env'] is False

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            def post(self, endpoint, json, allow_redirects):
                assert not allow_redirects and self._retry_connection is False
                outer.calls.append((endpoint, json))
                return Reply(json, len(outer.calls))

        self.http = types.SimpleNamespace(ClientSession=Session,
            TCPConnector=lambda **kwargs: object(), ClientTimeout=lambda **kwargs: object())

    def claim(self, spec):
        return json.dumps({'execution': spec, 'execution_sha256': digest(spec),
                           'timing': {'deadline_monotonic': time.perf_counter() + 1600}}).encode()

    async def run_session(self, name, spec=None, claim=None, claim_sha=None):
        spec = self.spec if spec is None else spec
        claim = self.claim(spec) if claim is None else claim
        runtime = {'claim': {'path': 'fixture-claim.json',
                            'sha256': claim_sha or hashlib.sha256(claim).hexdigest()},
                   'selected_session': name, 'unit_id': 'selected_g3/replicas',
                   'run_id': 'fixture-unit', 'uid': 0, 'stop_file': 'fixture-STOP',
                   'clock_scope': {'host': 'fixture-host', 'boot_id': 'fixture-boot', 'run_id': 'fixture-unit'},
                   'rgb_by_path': {image['path']: image['rgb_sha256'] for batch in spec['batches']
                                   for row in batch['requests'] for image in row['input']['images']}}

        def opened(path, *args, **kwargs):
            return self.files.setdefault(str(path), Buffer())

        with patch.dict(sys.modules, {'aiohttp': self.http}), \
             patch.object(Path, 'read_bytes', return_value=claim), \
             patch.object(Path, 'open', opened), patch.object(Path, 'exists', return_value=False):
            windows = await fixed_unit._run_client(spec, runtime, Path('fixture-output') / name)
        rows = [json.loads(line) for line in self.files[str(Path('fixture-output') / name / 'requests.jsonl')].getvalue().splitlines()]
        return windows, rows

    async def test_full_claim_runs_two_sixty_request_sessions(self):
        claim = self.claim(self.spec)
        first_windows, cold = await self.run_session('cold', claim=claim)
        second_windows, restart = await self.run_session('restart', claim=claim)
        self.assertEqual((len(first_windows), len(second_windows)), (12, 12))
        self.assertEqual((len(cold), len(restart), len(self.calls)), (60, 60, 120))
        self.assertEqual({row['session'] for row in cold}, {'cold'})
        self.assertEqual({row['session'] for row in restart}, {'restart'})
        self.assertEqual(len({row['fixture_id'] for row in cold + restart}), 120)
        for rows in (cold, restart):
            self.assertEqual([row['dispatch_index'] for row in rows], list(range(60)))
            self.assertTrue(all(row['success'] for row in rows))
            self.assertEqual([sum(row['endpoint'] == url for row in rows) for url in self.spec['urls']], [20] * 3)

    async def test_partial_execution_cannot_replace_the_full_claim(self):
        claim = self.claim(self.spec)
        cropped = {**self.spec, 'batches': self.spec['sessions']['cold']}
        with self.assertRaises(ValueError): await self.run_session('cold', spec=cropped, claim=claim)
        self.assertEqual(self.calls, [])

    async def test_unknown_session_rejected_before_http(self):
        with self.assertRaises(ValueError): await self.run_session('third')
        self.assertEqual(self.calls, [])

    async def test_claim_bytes_must_match(self):
        with self.assertRaises(ValueError): await self.run_session('cold', claim_sha='0' * 64)
        self.assertEqual(self.calls, [])


class SelectedClientPathTests(unittest.TestCase):
    def setUp(self):
        fixture = test_selected_unit.SelectedUnitTests()
        fixture.setUp()
        self.spec = fixture.spec
        self.root = Path.cwd().resolve()
        self.unit = self.root / 'runtime' / 'fixture-unit'
        self.output = self.unit / 'cold'
        self.execution = self.unit / 'execution.json'
        self.runtime = self.output / 'client-runtime.json'

    def load(self, session='cold', execution=None):
        original_resolve = Path.resolve
        def resolved(path, strict=False):
            return original_resolve(path, strict=False)
        def read(path):
            return json.dumps(self.spec if path == self.execution else {'run_id': 'fixture-unit'}).encode()
        with patch.object(Path, 'resolve', resolved), patch.object(Path, 'is_symlink', return_value=False), \
             patch.object(Path, 'read_bytes', read):
            return selected_client.load_session(execution or self.execution, self.runtime, self.output, session)

    def test_correct_session_paths(self):
        _, runtime, output = self.load()
        self.assertEqual(runtime['selected_session'], 'cold')
        self.assertEqual(output, self.output)

    def test_restart_cannot_write_cold_output(self):
        with self.assertRaises(ValueError): self.load('restart')

    def test_outside_execution_rejected(self):
        with self.assertRaises(ValueError): self.load(execution=self.root / 'outside.json')


if __name__ == '__main__':
    unittest.main()
