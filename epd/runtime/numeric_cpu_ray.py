"""Pre-import Ray source checks for the CPU lifecycle Gate; no head or actor startup."""
import hashlib
import importlib
import importlib.metadata
import os
from pathlib import Path, PurePosixPath
import sys

PINNED_SOURCES = {
    "_private/node.py": "923e30633a4d2ea2ccfbe67b5c6211bbcb670738abb866825cbc318398c95b24",
    "_private/services.py": "385604d4ecda5febb280435e1129512c5802c3d520581b6a7470ceeef4c8c60f",
    "_private/parameter.py": "1242f4110da8f8acafeb1a6cd816addc8a8f322aa3f56fad5bf23cdbe3e1a0f2",
    "_private/worker.py": "5e6a29a4f1c17f02c346eed207e5389dbb77b27cf3398fa373ea769ff5895263",
    "actor.py": "7177e5fec52d7b3e0ea0e95bcc79ff75e0d018439e965911e69a26ade75b61df",
    "__init__.py": "a75bc04e3d92750b6344109fabaa71d086d4f119f849fe6f297e6622c6e1daeb",
    "_private/utils.py": "0ad838e1a440b2551a28bd46abe367b666ca03c6849b6c17ff8b348dda0b8d5f",
    "dashboard/optional_deps.py": "a117f55b5dc38ba0f5f77e76598416b0ec2ba152e74ff733964fcc3bff587cd0",
    "dashboard/agent.py": "0bbb4cb5ca1fc6aabc1dfec9a4501158dda76609f1445bd4c229980fbdebb6f0",
    "dashboard/utils.py": "294f0cf6f6bd8035c560a3e71e1bb2795185fc620bfaccc68e096e12733954c0",
    "_private/resource_spec.py": "a66e6b553ab5bc043041026244af982dd8cdfa6dc2cf4cdbb4f73ff67e5a85bf",
    "_private/accelerators/nvidia_gpu.py": "a87c394eeb7b0a93905f0920603214424a03cbf21cad944b9efe66e46657382a",
    "dashboard/modules/reporter/reporter_agent.py": "cb8019582df38adaf5ab6e997bbcd02ed484eb6d3a571b5963ca8869efe1031e",
    "_private/accelerators/__init__.py": "264bc020ff0a1ad12ee1c79d49fcffa25a6dc4974b75edf6164c954f90ea8dac",
    "_private/state.py": "c6cf29a61b46b3b615339502ea1a9175706f7833563d21104ddf75289659a559",
    "_private/gcs_utils.py": "d29c2e8492ee25bd7e67ffa6e61122ab7acd1bc74f2d79a5b0c6ed2528a0d0fe"
}


def verify_sources(package, pins, uid):
    package=Path(package)
    if not package.is_absolute() or package.is_symlink() or package.resolve(strict=True)!=package:
        raise ValueError('Canonical actual Ray package required')
    rows=[]
    for name,expected in pins.items():
        relative=PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or relative.as_posix()!=name or '\\' in name:
            raise ValueError('Ray source member escapes package')
        path=package.joinpath(*relative.parts)
        for ancestor in (path,*path.parents):
            if ancestor.is_symlink():raise ValueError('Linked Ray source refused')
            if ancestor==package:break
        info=path.stat()
        if not path.is_file() or info.st_uid!=uid or info.st_size>2*1024**2:
            raise ValueError('Owned bounded Ray source required')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Ray source differs before import: '+name)
        rows.append(dict(path=name,bytes=len(raw),sha256=expected))
    return rows


def load_cpu_ray(package):
    if os.environ.get('CUDA_VISIBLE_DEVICES')!='':raise ValueError('CPU Gate requires empty CUDA visibility')
    if any(name=='ray' or name.startswith('ray.') or name=='torch' or name.startswith('torch.')
           or name=='epdserve' or name.startswith('epdserve.') for name in sys.modules):
        raise ValueError('Ray/Torch/EPD already imported before CPU source checks')
    package=Path(package)
    distribution=importlib.metadata.distribution('ray')
    if distribution.version!='2.10.0' or Path(distribution.locate_file('ray')).absolute()!=package:
        raise ValueError('Exact installed Ray2.10 package location required')
    rows=verify_sources(package,PINNED_SOURCES,os.getuid())
    ray=importlib.import_module('ray')
    if ray.__version__!='2.10.0' or Path(ray.__file__).absolute()!=package/'__init__.py':
        raise ValueError('Imported Ray differs from verified package')
    utils=importlib.import_module('ray._private.utils')
    if utils.check_dashboard_dependencies_installed() is not False:
        raise RuntimeError('CPU Gate needs the actual minimal dashboard branch; Reporter NVML path not authorized')
    return ray,dict(scope='CPU preimport/minimal-selection facts only',sources=rows,
        dashboard_dependencies_installed=False,head_started=False,actor_started=False,
        GPU_or_lifecycle_approved=False)
