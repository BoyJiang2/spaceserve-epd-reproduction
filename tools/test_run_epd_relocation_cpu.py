"""Controller boundary mocks: no Git, API, SSH or evidence-directory writes."""
from pathlib import Path
import runpy
import subprocess
import sys
import unittest
from unittest.mock import patch


class ControllerTests(unittest.TestCase):
    def test_outside_window_stops_before_api_or_ssh(self):
        root=Path(__file__).resolve().parents[1]
        script=root/'tools/run_epd_relocation_cpu.py'
        commit='a'*40
        responses=[commit+'\n',commit+' refs/heads/main\n',
                   (root/'tools/relocate_epd_assets_cpu.py').read_bytes(),
                   (root/'epd/migration/qjh003-asset-relocation.json').read_bytes(),script.read_bytes()]
        for now in (1793260799.999,1793264040,1793264400):
            with self.subTest(now=now), patch.object(sys,'argv',[str(script),'apply']), patch.object(subprocess,'check_output',side_effect=responses), patch.object(subprocess,'run') as remote, patch('time.time',return_value=now):
                with self.assertRaises(AssertionError):runpy.run_path(str(script),run_name='__main__')
                remote.assert_not_called()


if __name__=='__main__':unittest.main()
