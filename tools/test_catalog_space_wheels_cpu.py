"""Pure HTTP-mock catalog validation; no network, package installation or GPU."""
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
import catalog_space_wheels_cpu as catalog


class CatalogTests(unittest.TestCase):
    def response(self,raw,headers=None):
        body=io.BytesIO(raw);response=SimpleNamespace(headers=headers or {},timeouts=[])
        response.fp=SimpleNamespace(raw=SimpleNamespace(_sock=SimpleNamespace(settimeout=response.timeouts.append)))
        def read(count):
            value=body.read(count)
            if body.tell()==len(raw):response.fp=None
            return value
        response.read=read;return response

    def fixture(self):
        return {'info':{'name':'CPU_Mock','version':'1.0'},'urls':[
            {'filename':'cpu_mock-1.0-cp310-cp310-manylinux2014_x86_64.whl','packagetype':'bdist_wheel',
             'url':'https://files.pythonhosted.org/packages/fixture.whl','size':123,'digests':{'sha256':'0'*64},
             'requires_python':'>=3.10','yanked':False,'python_version':'cp310'}]}

    def test_exact_freeze_normalizes_names_and_rejects_floating_direct_or_duplicate(self):
        self.assertEqual(catalog.packages(b'CPU_Mock==1.0\n'),[('cpu-mock','1.0')])
        for raw in (b'package>=1',b'https://outside.invalid/package.whl',b'-e ./source',b'a_b==1\na-b==2'):
            with self.assertRaises(ValueError):catalog.packages(raw)

    def test_identity_version_and_artifact_hash_are_required(self):
        data=self.fixture();result=catalog.describe(json.dumps(data).encode(),'cpu-mock','1.0')
        self.assertEqual(result['artifacts'][0]['wheel_tags']['python'],'cp310')
        for name,version in (('other','1.0'),('cpu-mock','2.0')):
            with self.assertRaises(ValueError):catalog.describe(json.dumps(data).encode(),name,version)
        data['urls'][0]['digests']['sha256']='wrong'
        with self.assertRaises(ValueError):catalog.describe(json.dumps(data).encode(),'cpu-mock','1.0')

    def test_unapproved_hosts_schemes_userinfo_or_signed_queries_are_refused(self):
        for url in ('http://files.pythonhosted.org/fixture.whl','https://outside.invalid/fixture.whl',
                    'https://userinfo@files.pythonhosted.org/fixture.whl','https://files.pythonhosted.org/fixture.whl?signature=CPU-MOCK'):
            data=self.fixture();data['urls'][0]['url']=url
            with self.assertRaises(ValueError):catalog.describe(json.dumps(data).encode(),'cpu-mock','1.0')

    def test_all_redirects_are_rejected(self):
        with self.assertRaises(ValueError):catalog.NoRedirect().redirect_request(None,None,302,'Found',{},'https://pypi.org/other')

    def test_bounded_read_preserves_EOF_and_rejects_declared_or_actual_oversize(self):
        response=self.response(b'CPU-MOCK')
        self.assertEqual(catalog.read_metadata(response,lambda:2),b'CPU-MOCK');self.assertEqual(response.timeouts,[2])
        with patch.object(catalog,'LIMIT',3):
            for headers in ({'Content-Length':'4'},{'Content-Length':'-1'},{}):
                with self.assertRaises(ValueError):catalog.read_metadata(self.response(b'long',headers),lambda:2)

    def test_expired_budget_prevents_read(self):
        def expired():raise TimeoutError('CPU-MOCK deadline')
        response=self.response(b'CPU-MOCK')
        with self.assertRaises(TimeoutError):catalog.read_metadata(response,expired)
        self.assertEqual(response.timeouts,[])

    def test_remaining_scope_requires_original89_prefix_and_exact_incomplete_state(self):
        rows=[('package-'+str(i),'1.0') for i in range(154)]
        rows[89]=('opentelemetry-semantic-conventions','0.66b1')
        old=[{'name':name,'version':version} for name,version in rows[:89]]
        terminal={'complete':False,'completed_packages':89,'requests':154,
                  'failure':{'type':'URLError','package':{'name':rows[89][0],'version':rows[89][1]},'http_status':None}}
        self.assertEqual(catalog.remaining_rows(rows,old,terminal),rows[89:])
        for changed in (old[:-1],old+[old[0]],list(reversed(old)),[{**old[0],'name':'unknown'},*old[1:]]):
            with self.assertRaises(ValueError):catalog.remaining_rows(rows,changed,terminal)
        for key,value in (('complete',True),('completed_packages',90),('requests',65),('failure',None)):
            with self.assertRaises(ValueError):catalog.remaining_rows(rows,old,{**terminal,key:value})


if __name__=='__main__':unittest.main(verbosity=2)
