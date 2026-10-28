"""Side-effect-free paths for the two reproduction projects; never grants a GPU Gate."""
from dataclasses import dataclass
import json
import os
from pathlib import Path, PurePosixPath
import re
import socket

PROJECTS = {'spaceserve': 1, 'epd': 3}
UUID = re.compile(r'GPU-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}')
RUN_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,31}')


@dataclass(frozen=True)
class ProjectLayout:
    config: dict

    def __post_init__(self):
        data = self.config
        if data.get('schema') != 'reproduction-project-v1' or data.get('project') not in PROJECTS:
            raise ValueError('Unknown project configuration schema')
        expected = '/local/boyjiang/' + data['project']
        if data.get('project_root') != expected:
            raise ValueError('Project root must be the approved stable qjh003 directory')
        if data.get('state') not in ('candidate', 'approved_scope'):
            raise ValueError('Unknown configuration state')
        run_id = data.get('run_id')
        if run_id is not None and (not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id)
                                   or run_id in ('.', '..', 'UNCONFIGURED')):
            raise ValueError('Run ID must be one safe path component')
        devices, uuids = data.get('gpu_devices'), data.get('gpu_uuids')
        if (not isinstance(devices, list) or not isinstance(uuids, list) or len(devices) != len(uuids)
                or len(set(devices)) != len(devices) or len(set(uuids)) != len(uuids)
                or any(type(device) is not int or device < 0 for device in devices)
                or any(not isinstance(uuid, str) or not UUID.fullmatch(uuid) for uuid in uuids)):
            raise ValueError('Physical devices and full UUIDs must be distinct matching lists')
        if data.get('host') != 'qjh003' or data.get('uid') != 2147 or type(data.get('uid')) is not int:
            raise ValueError('This migration targets qjh003 UID2147 only')

    @classmethod
    def read(cls, path, project):
        data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        if data.get('project') != project:
            raise ValueError('Configuration belongs to the other project')
        return cls(data)

    @property
    def project(self): return self.config['project']

    @property
    def project_root(self): return Path(self.config['project_root'])

    @property
    def checkout(self): return self.project_root/'repo'

    @property
    def code_root(self): return self.checkout/self.project/'runtime'

    @property
    def assets_root(self): return self.project_root/'assets'

    @property
    def run_root(self): return self.project_root/'runs'/(self.config.get('run_id') or 'UNCONFIGURED')

    @property
    def gpu_devices(self): return tuple(self.config['gpu_devices'])

    @property
    def gpu_uuids(self): return tuple(self.config['gpu_uuids'])

    @property
    def single_uuid(self): return self.gpu_uuids[0] if len(self.gpu_uuids) == 1 else None

    @property
    def ray_tmp(self): return self.project_root/'tmp/ray'

    @property
    def host_lock(self): return self.project_root.parent/'.spaceserve-epd-host.lock'

    def asset(self, relative):
        part = PurePosixPath(relative)
        if (not relative or part.is_absolute() or re.match(r'^[A-Za-z]:', relative)
                or '..' in part.parts or '\\' in relative
                or part.as_posix() != relative or relative == '.'):
            raise ValueError('Asset path must remain inside this project assets')
        return self.assets_root/relative

    def require_scope(self, phase):
        # These fields are prerequisites, not proof of booking ownership or independent approval.
        data = self.config
        allowed = ('numeric', 'model', 'formal') if self.project == 'spaceserve' else (
            'numeric', 'qualification', 'calibration', 'selected_g3')
        if (data['state'] != 'approved_scope' or not data.get('run_id') or phase not in allowed
                or phase not in data.get('allowed_actions', [])
                or len(self.gpu_devices) != PROJECTS[self.project]):
            raise ValueError('Candidate/missing/wrong phase scope cannot execute')
        if (socket.gethostname() != data['host'] or not hasattr(os, 'getuid')
                or os.getuid() != data['uid']):
            raise ValueError('Actual executor host/UID differs')
        for managed in (self.run_root, self.assets_root, self.project_root/'cache', self.ray_tmp,
                        self.run_root/'tmp/mps', self.run_root/'logs/mps'):
            for path in (managed,*managed.parents):
                if path.is_symlink(): raise ValueError('Managed directory ancestry contains a link')
                if path.exists() and path.is_relative_to(self.project_root):
                    if not path.is_dir() or path.stat().st_uid != data['uid']:
                        raise ValueError('Managed directory is not an owned real directory')
        for key, size in (('source_commit',40), ('source_manifest_sha256',64)):
            if not isinstance(data.get(key), str) or not re.fullmatch('[0-9a-f]{%d}' % size, data[key]):
                raise ValueError('Exact source version/manifest required')
        if not isinstance(data.get('booking'), dict) or not data['booking']:
            raise ValueError('Explicit booking scope required; no old-host fallback')
        # Existing fresh booking, source/deploy, phase G2/G3 and cleanup guards must still run.

    def describe(self):
        root = PurePosixPath(self.config['project_root'])
        return {'project': self.project, 'state': self.config['state'], 'project_root': str(root),
            'code_root': str(root/'repo'/self.project/'runtime'), 'assets_root': str(root/'assets'),
            'run_root': str(root/'runs'/(self.config.get('run_id') or 'UNCONFIGURED')),
            'ray_tmp': str(root/'tmp/ray'), 'creates_files': False, 'grants_GPU_or_Gates': False}
