"""CPU-only safety fixtures; never touch the real MPS endpoint."""
import json
import os
from pathlib import Path
import runpy
import socket
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

root = Path('/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023')
original_path = type(root)
production_inode = (root / 'tmp/mps/control').lstat().st_ino

for kind in ['owned-stopped', 'wrong-inode', 'live-mps', 'symlink']:
    with tempfile.TemporaryDirectory(dir=root / 'tmp') as temporary:
        fixture = Path(temporary)
        pipe = fixture / 'tmp/mps'
        pipe.mkdir(parents=True, mode=0o700)
        (fixture / 'evidence').mkdir()
        endpoint = pipe / 'control'
        with socket.socket(socket.AF_UNIX) as fake:
            fake.bind(str(endpoint))
        inode = endpoint.lstat().st_ino
        if kind == 'symlink':
            endpoint.rename(pipe / 'original')
            endpoint.symlink_to(pipe / 'original')
        owner = {'state': 'stopped', 'pid': 999999999, 'pipe': str(pipe), 'token': str(fixture) + ':fixture',
                 'control_inode': inode + (kind == 'wrong-inode')}
        (fixture / 'evidence/mps-owner.json').write_text(json.dumps(owner))
        def mapped(value, *args, **kwargs):
            return fixture if str(value) == str(root) else original_path(value, *args, **kwargs)
        active = [SimpleNamespace(info={'name': 'nvidia-cuda-mps-control'})] if kind == 'live-mps' else []
        rejected = False
        with patch('pathlib.Path', side_effect=mapped), patch.dict(os.environ, EXP_ROOT=str(fixture), REPRO_HOST_LOCK_HELD='1'), patch('psutil.pid_exists', return_value=False), patch('psutil.process_iter', return_value=active):
            try:
                runpy.run_path(str(root / 'scripts/prune_stopped_mps.py'))
            except RuntimeError:
                rejected = True
        assert rejected == (kind != 'owned-stopped')
        assert (endpoint.exists() or endpoint.is_symlink()) == rejected
assert (root / 'tmp/mps/control').lstat().st_ino == production_inode
print('CPU MPS prune: owned stopped socket only; wrong inode/live daemon/symlink preserved; production inode unchanged; PASS')
