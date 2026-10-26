"""Reproduce the H20 FP16 linear failure without vLLM or model weights."""
import argparse
import importlib.metadata
import json
import os
import pathlib
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--device', default='0')
args = parser.parse_args()
assert not subprocess.check_output(['nvidia-smi', '--id=' + args.device, '--query-compute-apps=pid', '--format=csv,noheader'], text=True).strip()
os.environ['CUDA_VISIBLE_DEVICES'] = args.device
import torch

print(json.dumps({'torch': torch.__version__, 'cublas': importlib.metadata.version('nvidia-cublas-cu12'),
                  'gpu': str(torch.cuda.get_device_properties(0))}), flush=True)
for m, k, n in [(1, 3584, 151680), (4, 3584, 151680), (8, 3584, 151680), (64, 14688, 1536)]:
    print(json.dumps({'starting_shape_mkn': [m, k, n]}), flush=True)
    x = torch.ones((m, k), dtype=torch.float16, device='cuda')
    weight = torch.ones((n, k), dtype=torch.float16, device='cuda')
    result = torch.nn.functional.linear(x, weight)
    torch.cuda.synchronize()
    assert bool(torch.all(result == k).item())
    print(json.dumps({'shape_mkn': [m, k, n], 'data_equal': True}), flush=True)
    del x, weight, result
print(json.dumps({'loaded_cublas_libraries': sorted({line.split()[-1] for line in pathlib.Path('/proc/self/maps').read_text().splitlines() if 'libcublas' in line})}), flush=True)
