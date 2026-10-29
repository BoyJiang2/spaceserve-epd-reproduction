"""CPU bootstrap construction only; no SSH, credentials or network calls."""
import ast
import tempfile
import hashlib
import json
import os
from pathlib import Path
import unittest
import control_space_window_20261030 as controller


class BootstrapTests(unittest.TestCase):
    def test_all_phases_compile_without_execution(self):
        for phase in controller.BUDGETS:
            source=controller.bootstrap('a'*40,phase)
            ast.parse(source)
            self.assertIn("commit='"+'a'*40+"'",source)
            self.assertIn("phase='"+phase+"'",source)

    def test_shell_revision_and_unknown_phase_rejected(self):
        for commit,phase in [('main','cpu'),("a'*40;exit",'cpu'),('a'*40,'retry')]:
            with self.assertRaises(ValueError):controller.bootstrap(commit,phase)

    def test_generated_dispatch_calls_only_one_named_phase(self):
        source=controller.bootstrap('b'*40,'numeric')
        self.assertIn("folder.mkdir(mode=0o700,exist_ok=False)",source)
        self.assertIn("p['approval']['review_sha256']",source)
        self.assertIn("sys.argv=['run_space_window_20261030.py',phase",source)


class PayloadTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=controller.CHECKOUT.parents[2]/'outputs')
        self.addCleanup(self.temp.cleanup);self.folder=Path(self.temp.name)
        self.path=self.folder/'input.json';self.path.write_bytes(b'{"phase":"cpu"}')

    def test_actual_regular_fd_is_hashed_and_rewound(self):
        expected=hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.path.open('rb') as payload:
            controller.verify_payload(payload,expected,self.folder)
            self.assertEqual(payload.tell(),0)
            info=os.fstat(payload.fileno())
        saved=json.loads((self.folder/'input-file.json').read_bytes())
        self.assertEqual(saved['sha256'],expected);self.assertEqual(saved['inode'],info.st_ino)

    def test_changed_payload_refuses_before_dispatch(self):
        with self.path.open('rb') as payload:
            with self.assertRaises(ValueError):controller.verify_payload(payload,'0'*64,self.folder)
        self.assertFalse((self.folder/'input-file.json').exists())

    def test_nonregular_fd_refuses_without_reading(self):
        read,write=os.pipe()
        try:
            with os.fdopen(read,'rb') as payload:
                with self.assertRaises(ValueError):controller.verify_payload(payload,'0'*64,self.folder)
        finally:os.close(write)
        self.assertFalse((self.folder/'input-file.json').exists())


if __name__=='__main__':unittest.main()
