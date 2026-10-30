"""CPU fixtures only; import order and refusal, not actual Ray/NVML behaviour."""
import hashlib
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace, ModuleType
import unittest
from unittest.mock import Mock, patch

import numeric_cpu_ray as cpu


class CPUImportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.events=[]
        self.raw=b'fixture-source\n';(self.root/'__init__.py').write_bytes(self.raw)
        self.pins={'__init__.py':hashlib.sha256(self.raw).hexdigest()}
        self.uid=(self.root/'__init__.py').stat().st_uid
        self.ray=SimpleNamespace(__version__='2.10.0',__file__=str(self.root/'__init__.py'))
        self.utils=SimpleNamespace(check_dashboard_dependencies_installed=Mock(return_value=False))
        self.distribution=SimpleNamespace(version='2.10.0',locate_file=lambda name:self.root)

    def load(self):
        def imported(name):
            self.events.append(name)
            return self.ray if name=='ray' else self.utils
        with patch.dict(os.environ,CUDA_VISIBLE_DEVICES=''),patch.object(cpu,'PINNED_SOURCES',self.pins), \
             patch.object(cpu.os,'getuid',return_value=self.uid,create=True), \
             patch.object(cpu.importlib.metadata,'distribution',return_value=self.distribution), \
             patch.object(cpu.importlib,'import_module',side_effect=imported):
            return cpu.load_cpu_ray(self.root)

    def test_sources_then_actual_minimal_selection_no_startup(self):
        ray,receipt=self.load()
        self.assertIs(ray,self.ray);self.assertEqual(self.events,['ray','ray._private.utils'])
        self.utils.check_dashboard_dependencies_installed.assert_called_once_with()
        self.assertFalse(receipt['head_started']);self.assertFalse(receipt['actor_started'])
        self.assertFalse(receipt['GPU_or_lifecycle_approved'])

    def test_source_mismatch_prevents_any_Ray_import(self):
        (self.root/'__init__.py').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'before import'):self.load()
        self.assertEqual(self.events,[])

    def test_full_dashboard_rejected_before_any_head(self):
        self.utils.check_dashboard_dependencies_installed.return_value=True
        with self.assertRaisesRegex(RuntimeError,'minimal dashboard'):self.load()
        self.assertNotIn('ray._private.node',self.events)

    def test_wrong_distribution_location_or_version_is_not_imported(self):
        self.distribution.version='2.11.0'
        with self.assertRaises(ValueError):self.load()
        self.distribution.version='2.10.0';self.distribution.locate_file=lambda name:self.root.parent
        with self.assertRaises(ValueError):self.load()
        self.assertEqual(self.events,[])

    def test_imported_module_must_be_the_verified_package(self):
        self.ray.__file__=str(self.root.parent/'__init__.py')
        with self.assertRaisesRegex(ValueError,'Imported Ray differs'):self.load()

    def test_preloaded_Ray_or_Torch_refuses_even_pinned_sources(self):
        for name in ('ray','torch','epdserve'):
            with self.subTest(name=name),patch.dict(cpu.sys.modules,{name:ModuleType(name)}):
                with self.assertRaisesRegex(ValueError,'already imported'):self.load()
        self.assertEqual(self.events,[])

    def test_nonempty_or_missing_CUDA_visibility_refused(self):
        for value in ('GPU-other',None):
            with self.subTest(value=value),patch.dict(os.environ,{},clear=True):
                if value is not None:os.environ['CUDA_VISIBLE_DEVICES']=value
                with self.assertRaisesRegex(ValueError,'empty CUDA'):cpu.load_cpu_ray(self.root)

    def test_owner_hash_and_path_escape_checks(self):
        with self.assertRaisesRegex(ValueError,'Owned'):cpu.verify_sources(self.root,self.pins,self.uid+1)
        for name in ('../elsewhere','/absolute','a/../__init__.py','a\\b'):
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,'escapes'):
                cpu.verify_sources(self.root,{name:self.pins['__init__.py']},self.uid)


if __name__=='__main__':unittest.main()
