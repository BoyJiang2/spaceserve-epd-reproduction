"""CPU-only small temporary files and fake curl; no network, server, model or GPU."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import fetch_space_model_cpu as fetch


class ModelFetchTests(unittest.TestCase):
    def fixture(self):
        rows=[{'name':str(i)+'.json','bytes':3,'sha256':hashlib.sha256(b'abc').hexdigest(),
               'source':{'Revision':'a'*40}} for i in range(15)]
        manifest={'repo':'Qwen/Qwen2-VL-7B-Instruct','endpoint':'https://modelscope.cn','files':rows}
        pins=[{'path':fetch.PREFIX+row['name'],'bytes':row['bytes'],'sha256':row['sha256']} for row in rows]
        return manifest,pins

    def test_exact_names_revisions_and_existing_pins_required(self):
        manifest,pins=self.fixture();self.assertEqual(len(fetch.source_files(manifest,pins)),15)
        for mode in ('revision','hash','name','duplicate','endpoint'):
            changed=copy.deepcopy(manifest)
            if mode=='revision':changed['files'][0]['source']['Revision']='latest'
            elif mode=='hash':changed['files'][0]['sha256']='b'*64
            elif mode=='name':changed['files'][0]['name']='../outside'
            elif mode=='duplicate':changed['files'][1]=copy.deepcopy(changed['files'][0])
            else:changed['endpoint']='https://OTHER'
            with self.assertRaises(ValueError):fetch.source_files(changed,pins)

    def attempt(self,body,exit_code):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();destination=root/'models';logs=root/'logs';destination.mkdir();logs.mkdir()
            row=self.fixture()[0]['files'][0];calls=[]
            def run(argv,**kwargs):
                calls.append(argv);Path(argv[argv.index('--output')+1]).write_bytes(body)
                kwargs['stderr'].write(b'CPU-MOCK original curl diagnostic')
                return types.SimpleNamespace(returncode=exit_code)
            with patch.object(fetch.subprocess,'run',side_effect=run):
                if exit_code or body!=b'abc':
                    with self.assertRaises((RuntimeError,ValueError)):
                        fetch.fetch(row,destination,logs,time.monotonic()+10,'CPU-MOCK-curl')
                    self.assertFalse((destination/row['name']).exists())
                    self.assertEqual((destination/(row['name']+'.partial')).read_bytes(),body)
                else:
                    result=fetch.fetch(row,destination,logs,time.monotonic()+10,'CPU-MOCK-curl')
                    self.assertEqual(result['state'],'downloaded_and_verified')
                    self.assertEqual((destination/row['name']).read_bytes(),body)
                    self.assertFalse((destination/(row['name']+'.partial')).exists())
                self.assertEqual(len(calls),1)
                self.assertEqual(calls[0][calls[0].index('--retry')+1],'0')
                self.assertEqual(calls[0][calls[0].index('--max-filesize')+1],'3')
                self.assertIn(b'CPU-MOCK original curl diagnostic',(logs/(row['name']+'.stderr.log')).read_bytes())
                self.assertEqual(json.loads((logs/(row['name']+'.command.json')).read_text())['exit_code'],exit_code)

    def test_near_deadline_both_timeouts_keep_the_cleanup_reserve(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();destination=root/'models';logs=root/'logs';destination.mkdir();logs.mkdir()
            row=self.fixture()[0]['files'][0]
            def run(argv,**kwargs):
                self.assertEqual(kwargs['timeout'],3)
                self.assertEqual(argv[argv.index('--max-time')+1],'2')
                self.assertLessEqual(100+kwargs['timeout'],108.5-5)
                Path(argv[argv.index('--output')+1]).write_bytes(b'abc')
                return types.SimpleNamespace(returncode=0)
            with patch.object(fetch.time,'monotonic',return_value=100),patch.object(fetch.subprocess,'run',side_effect=run):
                fetch.fetch(row,destination,logs,108.5,'CPU-MOCK-curl')
            with patch.object(fetch.time,'monotonic',return_value=107),patch.object(fetch.subprocess,'run') as process:
                # A different unused filename reaches admission rather than existing-file hashing.
                with self.assertRaises(TimeoutError):
                    fetch.fetch({**row,'name':'late.json'},destination,logs,108.5,'CPU-MOCK-curl')
                process.assert_not_called()

    def test_success_is_hashed_before_final_rename(self):self.attempt(b'abc',0)
    def test_failed_curl_keeps_partial_and_original_diagnostic(self):self.attempt(b'ab',7)
    def test_wrong_actual_bytes_are_preserved_without_success(self):self.attempt(b'BAD',0)


if __name__=='__main__':unittest.main()
