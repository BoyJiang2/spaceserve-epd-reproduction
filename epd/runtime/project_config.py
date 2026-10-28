"""One EPD project configuration; no booking or GPU action is implied."""
import os
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from reproduction_paths import ProjectLayout


def context():
    return ProjectLayout.read(os.environ.get('EPD_CONFIG', Path(__file__).with_name('project-scope.json')), 'epd')


def static_scope(layout):
    # Deployment digests are bound by actual deployment/G2, never self-referential Git content.
    data = layout if isinstance(layout,dict) else layout.config
    return {key:value for key,value in data.items()
            if key not in ('source_commit','source_manifest_sha256','asset_manifest_sha256')}


def paths_for(config):
    layout = context()
    if (not layout.config.get('run_id') or config.get('root') != str(layout.run_root)
            or config.get('host') != layout.config['host'] or config.get('uid') != layout.config['uid']
            or Path(__file__).resolve().parent != layout.code_root):
        raise ValueError('EPD cohort, executor and fixed Git source must match the project configuration')
    frozen = layout.run_root/'project.json'
    if frozen.is_symlink() or json.loads(frozen.read_bytes()) != layout.config:
        raise ValueError('Actual project configuration differs from the frozen cohort configuration')
    for managed in (layout.run_root,layout.assets_root,layout.code_root):
        for path in (managed,*managed.parents):
            if path.is_symlink(): raise ValueError('Linked EPD managed ancestry refused')
            if path.exists() and path.is_relative_to(layout.project_root):
                if not path.is_dir() or path.stat().st_uid != layout.config['uid']:
                    raise ValueError('EPD managed directory owner/type differs')
    return layout
