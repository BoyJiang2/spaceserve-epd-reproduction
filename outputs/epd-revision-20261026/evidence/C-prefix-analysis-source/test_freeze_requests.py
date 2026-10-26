import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image
from freeze_requests import build


class Tokenizer:
    def apply_chat_template(self, messages, *, tokenize, add_generation_prompt):
        if tokenize or not add_generation_prompt:
            raise AssertionError('template options differ from benchmark')
        return 'template:' + messages[0]['content']


class FreezeTests(unittest.TestCase):
    def dataset(self, root):
        folder=root/'dataset'; folder.mkdir()
        for i in range(20):
            Image.new('RGB',(448,448),(i,2*i,3*i)).save(folder/f'{i}.png')
        manifest={'images':[{'file':f'{i}.png'} for i in range(20)],'prompt':'Describe.'}
        (folder/'manifest.json').write_bytes(json.dumps(manifest).encode())

    def test_exact_twenty_image_cycle_template_and_sha(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temporary:
            root=Path(temporary); self.dataset(root)
            result=build(root,Tokenizer())
            self.assertEqual(result['inference_requests'],0)
            self.assertEqual(len(result['loads']),5)
            for load in result['loads'].values():
                self.assertEqual(len(load['requests']),120)
                self.assertEqual(sum(r['warmup'] for r in load['requests']),20)
                self.assertEqual(load['prompt_sha256'],hashlib.sha256(load['prompt'].encode()).hexdigest())
            request=result['loads']['D']['requests'][23]
            self.assertEqual([r['file'] for r in request['images']],[f'{i}.png' for i in [4,5,6,7,8,9,10,11]])
            self.assertEqual(result['images'][0]['sha256'],hashlib.sha256((root/'dataset/0.png').read_bytes()).hexdigest())
            self.assertNotEqual(result['images'][0]['rgb_sha256'],result['images'][1]['rgb_sha256'])

    def test_dimensions_and_path_escape_rejected_before_inference(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temporary:
            root=Path(temporary); self.dataset(root)
            Image.new('RGB',(224,224)).save(root/'dataset/0.png')
            with self.assertRaisesRegex(ValueError,'sizing'):
                build(root,Tokenizer())
            manifest=json.loads((root/'dataset/manifest.json').read_bytes())
            manifest['images'][0]['file']='../outside.png'
            (root/'dataset/manifest.json').write_bytes(json.dumps(manifest).encode())
            with self.assertRaisesRegex(ValueError,'escaped'):
                build(root,Tokenizer())


if __name__=='__main__':
    unittest.main()
