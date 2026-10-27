import json
import os
from pathlib import Path
import socket
import tempfile
import types
import unittest
from unittest.mock import patch

try:
    import prune_stopped_mps as prune
except ModuleNotFoundError as error:
    if error.name=='psutil': raise unittest.SkipTest('requires target CPU psutil') from error
    raise


class PruneTests(unittest.TestCase):
    @unittest.skipUnless(os.name=='posix','requires actual AF_UNIX endpoint')
    def test_only_owned_stopped_inode_is_unlinked(self):
        for kind in ('owned','wrong-inode','live-MPS','symlink'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
                root=Path(directory).resolve()
                folder=root/'tmp/mps'
                folder.mkdir(parents=True,mode=0o700)
                (root/'evidence').mkdir()
                endpoint=folder/'control'
                with socket.socket(socket.AF_UNIX) as server: server.bind(str(endpoint))
                inode=endpoint.lstat().st_ino
                if kind=='symlink':
                    endpoint.rename(folder/'saved')
                    endpoint.symlink_to('saved')
                state={'state':'stopped','pid':99999999,'pipe':str(folder),'token':str(root)+':fixture',
                       'control_inode':inode+(kind=='wrong-inode')}
                (root/'evidence/mps-owner.json').write_text(json.dumps(state))
                active=[types.SimpleNamespace(info={'name':'nvidia-cuda-mps-control'})] if kind=='live-MPS' else []
                with patch.object(prune.psutil,'pid_exists',return_value=False),patch.object(prune.psutil,'process_iter',return_value=active):
                    if kind=='owned':
                        self.assertTrue(prune.prune(root)['unlink_succeeded'])
                        self.assertFalse(endpoint.exists())
                    else:
                        with self.assertRaises(RuntimeError): prune.prune(root)
                        self.assertTrue(endpoint.exists() or endpoint.is_symlink())


if __name__=='__main__': unittest.main()
