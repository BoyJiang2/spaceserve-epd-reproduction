"""Pure derivation fixtures; no processes, files, network or GPU."""
import copy
import json
import unittest
from space_closed_startup import digest,input_core,resolve


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.old=dict(utc='old',verified_epoch=10,passed=True,checked_files=[dict(path='model',sha256='x')],frozen_prompts={'1':'prompt'})
        self.new=dict(self.old,utc='new',verified_epoch=100)
        self.rows=[dict(path='code.py',bytes=1,sha256='stable'),dict(path='evidence/MODEL_INPUTS_VERIFIED-attempt1.json',bytes=1,sha256='old')]
        self.auth=dict(passed=True,scope='closed-startup-1',review_sha256='approved',reviewer='independent',adapter_sha256='adapter')
        self.template=dict(input_core_sha256=input_core(self.old),model_rows=self.rows,
            code_approval=dict(passed=True,allowed_actions=['preflight-models'],model_correctness_approved=False,
                               review_sha256='previous',bound_files=copy.deepcopy(self.rows)))

    def invoke(self,new=None,rows=None,now=101):
        new=self.new if new is None else new
        expected=copy.deepcopy(self.rows)
        raw=json.dumps(new,indent=2).encode();expected[1].update(bytes=len(raw),sha256=digest(raw))
        rows=expected if rows is None else rows
        return resolve(self.template,self.auth,new,rows,json.dumps(rows).encode(),now)

    def test_time_only_refresh_resolves_code_without_model_pass(self):
        value=self.invoke()
        self.assertEqual(value['review_sha256'],'approved')
        self.assertEqual(value['resolved_from_review_sha256'],'previous')
        self.assertEqual(value['model_main_before_epoch'],1000)
        self.assertFalse(value['model_correctness_approved'])
        self.assertEqual(self.template['code_approval']['review_sha256'],'previous')

    def test_input_semantics_changed_rejected(self):
        for field,value in [('passed',False),('checked_files',[]),('frozen_prompts',{'1':'other'}),('extra',True)]:
            new=copy.deepcopy(self.new);new[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.invoke(new=new)

    def test_source_manifest_or_scope_change_rejected(self):
        rows=copy.deepcopy(self.rows);rows[0]['sha256']='changed'
        with self.assertRaises(ValueError):self.invoke(rows=rows)
        self.auth['passed']=False
        with self.assertRaises(ValueError):self.invoke()

    def test_future_expired_and_missing_time_rejected(self):
        for now in (99,1000):
            with self.assertRaises(ValueError):self.invoke(now=now)
        new=dict(self.new);del new['utc']
        with self.assertRaises(KeyError):self.invoke(new=new)


if __name__=='__main__':unittest.main()
