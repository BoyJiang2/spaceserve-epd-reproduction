import copy
import unittest
from check_mask_sets import EXPECTED_UUID,validate


def fixture():
    sets={'before-existing-mask':[0,1,2,3],'after-existing-mask':[1,2,3],
          'restored-to-zero-mask':[0,1,2,3],'reapplied-existing-mask':[1,2,3],
          'first-encoder-execution':[1,2,3]}
    return [{'label':label,'pid':123,'stream':456,'visible_gpu_uuid':EXPECTED_UUID,
             'sm_ids':values,'mps_active_thread_percentage':'100','mps_pipe':'private',
             'masked_group':True} for label,values in sets.items()]


class MaskTests(unittest.TestCase):
    def test_subset_restore_reapply_and_same_stream(self):
        rows=fixture()
        self.assertTrue(validate(rows,True)['passed'])
        mutations=((1,'sm_ids',[4,5,6]),(2,'sm_ids',[0,1,2]),
                   (3,'sm_ids',[0,1,2]),(4,'stream',999))
        for index,key,value in mutations:
            bad=copy.deepcopy(rows)
            bad[index][key]=value
            with self.subTest(index=index),self.assertRaises(RuntimeError):
                validate(bad,True)


if __name__=='__main__':
    unittest.main()
