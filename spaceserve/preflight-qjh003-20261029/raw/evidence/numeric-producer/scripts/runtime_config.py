"""One SpaceServe project configuration; reading it has no runtime side effects."""
import os
from pathlib import Path
import sys
import shlex
import json

# A frozen run contains this small shared module beside its scripts, not another repo or assets copy.
shared = Path(__file__).with_name('reproduction_paths.py')
sys.path.insert(0, str(shared.parent if shared.exists() else Path(__file__).resolve().parents[3]))
from reproduction_paths import ProjectLayout


def context():
    default = Path(__file__).resolve().parents[1]/'configs/project.candidate.json'
    supplied = Path(os.environ.get('SPACESERVE_CONFIG', default))
    frozen = Path(__file__).resolve().parents[1]/'configs/project.json'
    if frozen.exists():
        if frozen.is_symlink() or json.loads(supplied.read_text()) != json.loads(frozen.read_text()):
            raise ValueError('External configuration differs from the frozen run configuration')
        supplied = frozen
        os.environ['SPACESERVE_CONFIG'] = str(frozen)
    return ProjectLayout.read(supplied, 'spaceserve')


def device_argument(config):
    if len(config.gpu_devices) != 1:
        raise ValueError('SpaceServe requires exactly one configured physical device')
    return str(config.gpu_devices[0])


def shell(phase):
    config = context()
    config.require_scope(phase)
    cuda = config.config.get('cuda_home')
    if not isinstance(cuda, str) or not cuda.startswith('/'):
        raise ValueError('An explicitly verified CUDA toolkit path is required')
    values = {'EXP_ROOT':config.run_root, 'PROJECT_ROOT':config.project_root,
        'SPACE_PYTHON':config.asset('envs/space/bin/python'), 'SPACE_SOURCE':config.asset('src/SpaceServe'),
        'SPACE_MODEL':config.asset('models/Qwen2-VL-7B-Instruct'), 'SPACE_DATASET':config.asset('dataset'),
        'SPACE_SMCTRL':config.run_root/'build/libsmctrl.so', 'RAY_TMPDIR':config.ray_tmp,
        'SPACE_GPU_INDEX':config.gpu_devices[0], 'SPACE_GPU_UUID':config.single_uuid, 'CUDA_HOME':cuda}
    return '\n'.join('export '+name+'='+shlex.quote(str(value)) for name,value in values.items())


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--shell', choices=('numeric','model','formal'), required=True)
    print(shell(parser.parse_args().shell))
