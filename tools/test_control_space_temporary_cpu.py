"""No-network tests for exact public source verification and early controller refusal."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch,Mock

import control_space_temporary_cpu as control
import prepare_space_temporary as prepare


class ControllerTests(unittest.TestCase):
    def test_transfer_bootstrap_refuses_wrong_executor_before_gpu_or_write(self):
        root=Path(__file__).resolve().parents[1]
        source=(root/'tools/prepare_space_temporary.py').read_bytes()
        config=(root/'spaceserve/validation/temporary-idle-gpu2-20261029/deploy-failure/original-config.json').read_bytes()
        code=control.transfer_code(source,config,(prepare.QUOTE+'\n').encode(),{},'9754419d570c97c08d40b7a7f674cead8707618b')
        with patch('socket.gethostname',return_value='CPU-MOCK wrong executor'),patch.object(control.subprocess,'check_output') as query:
            with self.assertRaises(AssertionError):exec(compile(code,'<CPU-MOCK-transfer>','exec'),{'__name__':'CPU_MOCK_TEST'})
            query.assert_not_called()
    def test_api_refuses_other_repository_without_network(self):
        with patch.object(control.subprocess,'check_output') as network:
            with self.assertRaises(ValueError):control.api('repos/another/repository')
            network.assert_not_called()

    def test_git_and_api_source_bytes_and_blob_must_match(self):
        raw=b'CPU-MOCK source\n';blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        response={'content':base64.b64encode(raw).decode(),'sha':blob}
        with patch.object(control,'git',return_value=raw),patch.object(control,'api',return_value=response):
            self.assertEqual(control.verified_file('a'*40,'tools/source.py'),raw)
        for change in ({'sha':'wrong'},{'content':base64.b64encode(b'changed').decode()}):
            with self.subTest(change=change),patch.object(control,'git',return_value=raw),patch.object(control,'api',return_value=response|change):
                with self.assertRaises(ValueError):control.verified_file('a'*40,'tools/source.py')

    def test_controller_source_mismatch_stops_before_ssh(self):
        commit='a'*40
        with patch.object(sys,'argv',['controller','deploy']),patch.object(control,'git',side_effect=[(commit+'\n').encode(),(commit+' refs/heads/main\n').encode()]),patch.object(control,'api',side_effect=[{'id':1433331669,'private':False},{'object':{'sha':commit}}]),patch.object(control,'verified_file',return_value=b'changed'),patch.object(control.subprocess,'Popen') as remote:
            with self.assertRaises(ValueError):control.main()
            remote.assert_not_called()

    def test_file_stdin_bytes_and_wait_timeout_never_kills_or_restarts(self):
        for timeout in (False,True):
            with self.subTest(timeout=timeout),tempfile.TemporaryDirectory(prefix='temporary-controller-test-',dir=Path(__file__).resolve().parent) as name:
                root=Path(name);raw=b'CPU-MOCK payload\n'+b'x'*131072;(root/'input.json').write_bytes(raw)
                process=SimpleNamespace(pid=123,returncode=None if timeout else 0,
                    wait=Mock(side_effect=subprocess.TimeoutExpired('CPU-MOCK SSH',390)) if timeout else Mock(return_value=0),kill=Mock(),terminate=Mock())
                received=[]
                def popen(argv,**kwargs):
                    self.assertEqual(argv,['CPU-MOCK SSH'])
                    self.assertEqual(kwargs['stdin'].read(),raw);kwargs['stdin'].seek(0)
                    received.append(kwargs['stdin']);return process
                with patch.object(control.subprocess,'Popen',side_effect=popen) as launch,patch.object(control,'process_identity',return_value={'pid':123,'creation_filetime':42}):
                    if timeout:
                        with self.assertRaises(subprocess.TimeoutExpired):control.launch_cpu(['CPU-MOCK SSH'],root,hashlib.sha256(raw).hexdigest())
                        self.assertTrue(json.loads((root/'UNKNOWN.json').read_bytes())['do_not_restart'])
                    else:self.assertIs(control.launch_cpu(['CPU-MOCK SSH'],root,hashlib.sha256(raw).hexdigest()),process)
                    launch.assert_called_once();process.wait.assert_called_once_with(timeout=390)
                self.assertTrue(received[0].closed);process.kill.assert_not_called();process.terminate.assert_not_called()
                self.assertEqual((root/'input.json').read_bytes(),raw)
                self.assertEqual(json.loads((root/'input-file.json').read_bytes())['sha256'],hashlib.sha256(raw).hexdigest())

    def test_changed_payload_stops_before_popen(self):
        with tempfile.TemporaryDirectory(prefix='temporary-controller-test-',dir=Path(__file__).resolve().parent) as name:
            root=Path(name);(root/'input.json').write_bytes(b'changed')
            with patch.object(control.subprocess,'Popen') as remote:
                with self.assertRaises(ValueError):control.launch_cpu(['CPU-MOCK SSH'],root,hashlib.sha256(b'original').hexdigest())
                remote.assert_not_called()


if __name__=='__main__':unittest.main()
