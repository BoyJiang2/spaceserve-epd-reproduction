"""Actual controller/assembler integration with injected processes, no GPU or HTTP."""
import hashlib
import itertools
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import preflight_controller as controller
import production_identity as identity


class SelectedEndpointOrderTests(unittest.TestCase):
    def test_actual_controller_manifest_follows_frozen_urls_for_every_registration_order(self):
        parent = Path(os.environ['EPD_CPU_TEST_TMP']).resolve(strict=True)
        with tempfile.TemporaryDirectory(prefix='endpoint-order-cpu-', dir=parent) as folder:
            root = Path(folder).resolve()
            source = root / 'runtime/endpoints'
            source.mkdir(parents=True)
            urls = ['http://127.0.0.1:18312', 'http://127.0.0.1:18310', 'http://127.0.0.1:18311']
            scope = {'host': 'CPU-fixture-host', 'run_id': 'fixture-unit', 'source_commit': 'a' * 40,
                     'deploy_sha256': 'b' * 64, 'candidate_config_sha256': 'c' * 64}
            uid = getattr(os, 'getuid', lambda: 0)()
            apis, paths = {}, []
            for index, url in enumerate(urls):
                pid = 990101 + index
                api = {'pid': pid, 'uid': uid, 'proc_start_ticks': pid * 10, 'cwd': str(root),
                       'boot_id': 'CPU-fixture-boot'}
                apis[pid] = api
                path = source / f'fixture-unit-{pid}-{pid * 10}.json'
                path.write_text(json.dumps({**scope, 'boot_id': 'CPU-fixture-boot', 'services': [{
                    'url': url, 'api_identity': api, 'worker_keys': []}]}))
                paths.append(path)
            original = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
            environment = {'EXP_ROOT': str(root)}
            config = {'root': str(root), 'uid': uid, 'gpu_uuids': ['GPU-fixture'] * 3,
                      'cleanup_seconds': 1, 'max_idle_bytes': 0}
            proc = NS(boot=lambda: 'CPU-fixture-boot', identity=lambda pid, uid: apis[pid])
            backend = NS(read=lambda uuid: {'used_bytes': 0, 'capacity_bytes': 10000, 'processes': []})
            claim = NS(check=Mock(), deadline=time.perf_counter() + 300,
                       owner=root / 'inputs.json', reservation_receipt={'CPU-MOCK': 'no real claim'})
            spec = {'urls': urls, 'servers': [{'argv': ['CPU-MOCK-no-exec']} for _ in urls],
                    'server_environments': [environment] * 3}
            original_glob = Path.glob
            cases = [(order, urls) for order in itertools.permutations(paths)]
            cases += [(tuple(paths), bad) for bad in (urls[:-1], urls + ['http://127.0.0.1:19999'],
                                                      [urls[0], urls[0], urls[2]])]
            for index, (order, expected) in enumerate(cases):
                with self.subTest(order=[path.name for path in order], expected=expected):
                    spec['urls'] = expected
                    output = root / 'runtime' / ('output-' + str(index))
                    output.mkdir()
                    processes = [NS(pid=pid) for pid in apis]
                    def glob(path, pattern):
                        return iter(order) if path == source else original_glob(path, pattern)
                    with patch.object(controller.subprocess, 'Popen', side_effect=processes), \
                         patch.object(controller, 'observe_owned', side_effect=lambda pid, *args: apis[pid]), \
                         patch.object(controller, 'descendants'), \
                         patch.object(controller, 'snapshot', side_effect=RuntimeError('CPU fixture stops after manifest')), \
                         patch.object(controller, 'cleanup_owned', return_value=[{'state': 'gone'}] * 3), \
                         patch.object(controller, 'verify_checkout', return_value={}), \
                         patch.object(identity, 'environment', return_value=environment), \
                         patch.object(identity, 'scope', return_value=scope), \
                         patch.object(identity, 'ProcReader', return_value=proc), \
                         patch.object(os, 'getuid', return_value=uid, create=True), \
                         patch.object(Path, 'glob', glob):
                        report = controller.execute_claimed(config, {'run_id': 'fixture-unit'},
                            {'commit': 'a' * 40}, spec, claim, backend, proc, output, output / 'active.json')
                    if expected == urls:
                        self.assertIn('CPU fixture stops after manifest', report['failure']['error'])
                        manifest = json.loads((output / 'endpoints.json').read_bytes())
                        self.assertEqual([service['url'] for service in manifest['services']], urls)
                    else:
                        self.assertIn('Frozen endpoint set differs', report['failure']['error'])
                        self.assertFalse((output / 'endpoints.json').exists())
                    self.assertEqual({path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}, original)


if __name__ == '__main__':
    unittest.main()
