"""CPU-only regression for Bash conditional function error propagation."""
import os
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


class ShellGuardTests(unittest.TestCase):
    def run_guard(self, name, setup):
        source = Path(__file__).with_name('official_space_first_request.sh').read_text()
        begin = source.index(name + '() {')
        end = source.index('\ncheck_listener() {', begin) if name == 'check_server' else source.index('\nready=0', begin)
        function = source[begin:end]
        with tempfile.TemporaryDirectory(prefix='space-shell-cpu-') as directory:
            for filename in ('server.stdout', 'server.stderr'):
                (Path(directory) / filename).touch()
            script = ('set -euo pipefail\nHELPER=/unused; STATE=/unused; PORT=1; SERVER=$$\n' +
                      setup + '\n' + function + '\n' +
                      'if ' + name + '; then printf "POST_SENTINEL\\n"; else printf "CLEANUP_ONLY\\n"; fi\n')
            result = subprocess.run(['bash', '--noprofile', '--norc', '-c', script],
                                    env=dict(os.environ, RUN=directory, BASH_ENV='/dev/null'),
                                    capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'CLEANUP_ONLY')

    def test_observe_failure_cannot_reach_request(self):
        self.run_guard('check_server', 'CPU_PY=/bin/false')

    def test_socket_inspection_failure_cannot_reach_request(self):
        self.run_guard('check_listener', 'CPU_PY=/bin/true; ss() { return 1; }')


class ResponseFixtureTests(unittest.TestCase):
    def parse_fixture(self, tokens, http_code='200'):
        source = Path(__file__).with_name('official_space_first_request.sh').read_text()
        parser = source[source.rindex("<<'PY'\n") + len("<<'PY'\n"):].split('\nPY\n', 1)[0]
        with tempfile.TemporaryDirectory(prefix='space-parser-cpu-') as directory:
            root = Path(directory)
            (root/'http-code.txt').write_text(http_code)
            fixture = {'choices': [{'message': {'content': 'CPU FIXTURE ONLY'}, 'finish_reason': 'length'}],
                       'usage': {'completion_tokens': tokens, 'prompt_tokens': 1, 'total_tokens': tokens + 1}}
            (root/'response.json').write_text(json.dumps(fixture))
            import sys
            result = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', parser, directory],
                                    capture_output=True, text=True, timeout=5)
            summary = json.loads((root/'response-summary.json').read_text()) if (root/'response-summary.json').exists() else None
        return result, summary

    def test_valid_fixture_retains_unverified_mechanism_status(self):
        result, summary = self.parse_fixture(128)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(summary['actual_output_tokens'], 128)
        self.assertIsNone(summary['client_TTFT'])
        self.assertFalse(summary['mechanisms_verified'])
        self.assertEqual(summary['semantic_correctness'], 'PENDING_IMAGE_AND_OUTPUT_REVIEW')

    def test_short_output_retained_as_failure(self):
        result, summary = self.parse_fixture(127)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(summary['actual_output_tokens'], 127)

    def test_http_failure_does_not_create_success_summary(self):
        result, summary = self.parse_fixture(128, '500')
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(summary)


if __name__ == '__main__':
    unittest.main()
