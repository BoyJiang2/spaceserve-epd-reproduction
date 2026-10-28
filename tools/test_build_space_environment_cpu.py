"""Small CPU-only contracts; never execute uv, Git, package imports or remote actions."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_space_environment_cpu as build


class BuildTests(unittest.TestCase):
    def test_fixed_batches_preserve_exact_original_freeze(self):
        root=Path(__file__).resolve().parents[1]
        raw=(root/'spaceserve/migration/asset-recovery/environment/space-freeze.txt').read_bytes()
        parts=build.dependency_parts(raw)
        self.assertEqual([len(build.versions(part.decode())) for part in parts],[16]*9+[10])
        self.assertEqual(b''.join(parts),raw)
        self.assertEqual({name:version for part in parts for name,version in build.versions(part.decode()).items()},
                         build.versions(raw.decode()))
        for changed in (raw+b'\n',raw.splitlines(keepends=True)[0]+raw,raw.replace(b'==',b'>=',1)):
            with self.assertRaises(ValueError):build.dependency_parts(changed)

    def test_exact_versions_reject_floating_urls_and_duplicates(self):
        self.assertEqual(build.versions('CPU_mock==1.0\n'),{'cpu-mock':'1.0'})
        for text in ('package>=1','-e ./source','package @ https://outside.invalid/file','a_b==1\na-b==1'):
            with self.assertRaises(ValueError):build.versions(text)

    def test_hash_lock_requires_full_original_version_and_hashes(self):
        text='# CPU-MOCK\ncpu-mock==1.0 \\\n    --hash=sha256:'+'0'*64+' \\\n    --hash=sha256:'+'1'*64+'\n'
        result=build.verify_lock(text,{'cpu-mock':'1.0'})
        self.assertEqual(len(result['cpu-mock']['hashes']),2)
        for changed in (text.replace('==1.0','==2.0'),text.split(' \\')[0],text+'other==1\n',
                        text+'cpu-mock==1.0\n',text+'--index-url https://outside.invalid/simple\n'):
            with self.assertRaises(ValueError):build.verify_lock(changed,{'cpu-mock':'1.0'})

    def test_install_never_drops_hash_binary_or_fixed_python_flags(self):
        argv=build.install_arguments('/project/uv','/project/env/bin/python','/project/lock')
        for option in ('--no-deps','--require-hashes','--only-binary','--no-config'):self.assertIn(option,argv)
        self.assertEqual(argv[argv.index('--python')+1],'/project/env/bin/python')
        self.assertEqual(argv[argv.index('--index-url')+1],'https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple')
        for option in ('--extra-index-url','--trusted-host','--allow-insecure-host'):self.assertNotIn(option,argv)
        self.assertNotIn('--no-verify-hashes',argv);self.assertNotIn('--torch-backend',argv)

    def test_controlled_environment_does_not_inherit_index_credentials_or_GPU_injection(self):
        with patch.dict(os.environ,{'UV_INDEX_URL':'https://outside.invalid','PIP_EXTRA_INDEX_URL':'https://outside.invalid',
                                    'VIRTUAL_ENV':'/other','PYTHONPATH':'/other','CUDA_VISIBLE_DEVICES':'OTHER'}):
            env=build.controlled_environment(Path('/project'))
        for key in ('UV_INDEX_URL','PIP_EXTRA_INDEX_URL','VIRTUAL_ENV','PYTHONPATH','CUDA_VISIBLE_DEVICES'):
            self.assertNotIn(key,env)
        self.assertEqual(env['UV_HTTP_RETRIES'],'2');self.assertEqual(env['UV_CONCURRENT_DOWNLOADS'],'4')
        self.assertTrue(Path(env['UV_CACHE_DIR']).is_relative_to(Path('/project')))
        self.assertEqual(env['UV_PYTHON_DOWNLOADS'],'never')

if __name__=='__main__':unittest.main(verbosity=2)
