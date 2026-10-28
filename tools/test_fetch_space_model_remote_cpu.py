"""Offline stream, redirect and exclusive publication contracts; no real network/GPU."""
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.request

sys.path.insert(0,str(Path(__file__).resolve().parent))
import fetch_space_model_remote_cpu as fetch


class Response:
    def __init__(self,body,headers=None,status=200):
        self.body=io.BytesIO(body);self.headers=headers or {};self.status=status;self.timeouts=[]
        self.fp=SimpleNamespace(raw=SimpleNamespace(_sock=SimpleNamespace(settimeout=self.timeouts.append)))
    def __enter__(self):return self
    def __exit__(self,*args):self.body.close()
    def geturl(self):return 'https://cdn.invalid/fixture?temporary=CPU-MOCK'
    def read(self,count):
        block=self.body.read(count)
        if self.body.tell()==len(self.body.getvalue()):self.fp=None
        return block


class Opener:
    def __init__(self,response):self.response=response;self.called=False
    def open(self,*args,**kwargs):self.called=True;return self.response


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name);self.target=self.root/'model.safetensors';self.partial=self.root/'model.safetensors.partial'
        self.body=b'CPU-MOCK model data';self.row={'name':self.target.name,'bytes':len(self.body),
            'sha256':hashlib.sha256(self.body).hexdigest(),'source':{'Revision':'0'*40}}
        self.owner=patch.object(fetch,'OWNER',self.root.stat().st_uid);self.owner.start();self.addCleanup(self.owner.stop)

    def run_transfer(self,body=None,headers=None,status=200,check=lambda:15):
        response=Response(self.body if body is None else body,headers,status);self.opener=Opener(response);self.state={}
        fetch.transfer(self.row,self.target,check,self.state,self.opener)
        return response

    def test_complete_response_publishes_exact_file_and_removes_only_own_temporary_name(self):
        response=self.run_transfer(headers={'Content-Length':str(len(self.body))})
        self.assertEqual(self.target.read_bytes(),self.body);self.assertFalse(self.partial.exists())
        self.assertTrue(self.state['published']);self.assertTrue(self.state['partial_removed'])
        self.assertEqual(self.state['target_sha256'],self.row['sha256'])
        self.assertEqual(response.timeouts,[15]);self.assertNotIn('temporary',json.dumps(self.state['effective_location']))

    def test_non_https_userinfo_and_fourth_redirect_are_refused_without_leaking_query(self):
        trace=[];handler=fetch.SecureRedirect(lambda:5,trace);request=urllib.request.Request('https://source.invalid/fixture')
        for url in ('http://cdn.invalid/fixture','https://userinfo@cdn.invalid/fixture'):
            with self.assertRaises(ValueError):handler.redirect_request(request,None,302,'Found',{},url)
        handler=fetch.SecureRedirect(lambda:5,trace)
        for index in range(3):handler.redirect_request(request,None,302,'Found',{},'https://cdn.invalid/path?temporary=CPU-MOCK')
        self.assertEqual(request.timeout,5);self.assertNotIn('temporary',json.dumps(trace))
        with self.assertRaises(ValueError):handler.redirect_request(request,None,302,'Found',{},'https://cdn.invalid/fourth')

    def test_oversize_truncation_wrong_sha_and_wrong_headers_leave_partial_without_final(self):
        cases=[(self.body+b'excess',{},200),(self.body[:-1],{},200),(b'x'*len(self.body),{},200),
               (self.body,{'Content-Length':'1'},200),(self.body,{},206)]
        for body,headers,status in cases:
            with self.subTest(body=body,headers=headers,status=status):
                with tempfile.TemporaryDirectory(dir=self.root) as folder:
                    target=Path(folder)/self.target.name
                    with self.assertRaises(ValueError):fetch.transfer(self.row,target,lambda:15,{},Opener(Response(body,headers,status)))
                    self.assertFalse(target.exists());self.assertTrue(target.with_name(target.name+'.partial').exists())

    def test_expired_deadline_or_API_proof_prevents_network(self):
        for error in (TimeoutError('CPU-MOCK deadline'),ValueError('CPU-MOCK stale actual booking')):
            def expired():raise error
            opener=Opener(Response(self.body))
            with self.assertRaises(type(error)):fetch.transfer(self.row,self.target,expired,{},opener)
            self.assertFalse(opener.called);self.assertFalse(self.partial.exists())

    def test_existing_final_or_partial_is_never_overwritten(self):
        for path in (self.target,self.partial):
            path.write_bytes(b'untouched');opener=Opener(Response(self.body))
            with self.assertRaises(ValueError):fetch.transfer(self.row,self.target,lambda:15,{},opener)
            self.assertFalse(opener.called);self.assertEqual(path.read_bytes(),b'untouched');path.unlink()

    def test_linked_parent_and_foreign_owner_are_rejected(self):
        with patch.object(Path,'is_symlink',lambda path:path==self.root):
            with self.assertRaises(ValueError):self.run_transfer()
        with patch.object(fetch,'OWNER',self.root.stat().st_uid+1):
            with self.assertRaises(ValueError):self.run_transfer()
        self.assertFalse(self.target.exists())

    def test_inode_replacement_is_preserved_and_never_unlinked(self):
        original=os.link
        def replace(source,target,**kwargs):
            original(source,target,**kwargs);Path(source).unlink();Path(source).write_bytes(b'CPU-MOCK replacement')
        with patch.object(os,'link',side_effect=replace):
            with self.assertRaises(ValueError):self.run_transfer()
        self.assertEqual(self.partial.read_bytes(),b'CPU-MOCK replacement');self.assertEqual(self.target.read_bytes(),self.body)

    def test_cleanup_failure_preserves_both_published_file_and_temporary_name(self):
        with patch.object(Path,'unlink',side_effect=PermissionError('CPU-MOCK cleanup denied')):
            with self.assertRaises(PermissionError):self.run_transfer()
        self.assertEqual(self.target.read_bytes(),self.body);self.assertEqual(self.partial.read_bytes(),self.body)
        self.assertTrue(self.state['published']);self.assertFalse(self.state['partial_removed'])


if __name__=='__main__':unittest.main(verbosity=2)
