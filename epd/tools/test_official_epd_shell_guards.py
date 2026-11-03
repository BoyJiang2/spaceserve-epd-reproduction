"""CPU-only regression for Bash conditional function error propagation."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class ShellGuardTests(unittest.TestCase):
    def run_guard(self, name, setup):
        source = Path(__file__).with_name('official_epd_first_request.sh').read_text()
        begin = source.index(name + '() {')
        end = source.index('\ncheck_listener() {', begin) if name == 'check_server' else source.index('\nready=0', begin)
        function = source[begin:end]
        with tempfile.TemporaryDirectory(prefix='epd-shell-cpu-') as directory:
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


if __name__ == '__main__':
    unittest.main()
