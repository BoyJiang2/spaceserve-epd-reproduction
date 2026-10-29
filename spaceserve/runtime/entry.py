"""Stable SpaceServe entry; code is frozen once per real run, assets are shared."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from reproduction_paths import ProjectLayout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('plan','prepare','cpu','numeric','model','formal','analyze'))
    parser.add_argument('--config', type=Path, default=Path(__file__).parent/'configs/project.candidate.json')
    parser.add_argument('--commit')
    args, analysis_args = parser.parse_known_args()
    if analysis_args and args.action != 'analyze': parser.error('Unexpected arguments')
    config_file = args.config.resolve(strict=True)
    layout = ProjectLayout.read(config_file, 'spaceserve')
    if args.action == 'plan':
        print(json.dumps({**layout.describe(), 'model':'Qwen2-VL-7B-Instruct','dtype':'float16','TP':1,
            'formal_cells':54,'formal_requests':5400,'formal_warmups':1080,'model_preflight_max':313,
            'formal_admission_seconds':201*60,'cleanup_seconds':120}, indent=2))
        return 0
    os.environ['SPACESERVE_CONFIG'] = str(config_file)
    if args.action == 'prepare':
        if not args.commit:
            parser.error('prepare requires the already-pushed exact --commit')
        sys.path.insert(0, str(Path(__file__).parent/'scripts'))
        from stage_cpu import prepare
        prepare(layout, args.commit, config_file)
        return 0
    if args.action == 'analyze':
        os.execv(sys.executable, [sys.executable, '-B', str(Path(__file__).parent/'scripts/analyze_trace.py'),
                                 *analysis_args])
    if args.action != 'cpu': layout.require_scope(args.action)
    receipt = json.loads((layout.run_root/'evidence/GIT_DEPLOYED.json').read_text())
    frozen_config = layout.run_root/'configs/project.json'
    if frozen_config.is_symlink() or json.loads(frozen_config.read_text()) != layout.config:
        raise ValueError('Use the exact frozen run configuration')
    if (receipt['commit'] != layout.config['source_commit']
            or receipt['source_manifest_sha256'] != layout.config['source_manifest_sha256']):
        raise ValueError('This run is not bound to its designated deployed source')
    if args.action in ('numeric', 'model', 'formal') and any(
            name in layout.config for name in ('workload_cpu_affinity', 'workload_numa_node')):
        manifest = layout.run_root/'configs/runtime-extension-source-manifest.json'
        helper = layout.run_root/'scripts/cpu_placement.py'
        if manifest.is_symlink() or helper.is_symlink():
            raise ValueError('Linked CPU profile source refused')
        if hashlib.sha256(manifest.read_bytes()).hexdigest() != receipt['source_manifest_sha256']:
            raise ValueError('Frozen CPU profile manifest differs')
        rows = [row for row in json.loads(manifest.read_text()) if row['path'] == 'scripts/cpu_placement.py']
        if len(rows) != 1 or hashlib.sha256(helper.read_bytes()).hexdigest() != rows[0]['sha256']:
            raise ValueError('Frozen CPU profile implementation differs')
        spec = importlib.util.spec_from_file_location('frozen_cpu_placement', helper)
        placement = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(placement)
        placement.apply(layout.config, args.action)
    scripts = {'numeric':'numeric_launcher.py','model':'model_launcher.py','formal':'formal_launcher.py',
               'cpu':'../tools/verify_deployment_cpu.py'}
    python = str(layout.asset('envs/space/bin/python'))
    environment = {**os.environ,'EXP_ROOT':str(layout.run_root),'REPRO_PHASE':args.action,
                   'SPACESERVE_CONFIG':str(frozen_config),
                   'PYTHONDONTWRITEBYTECODE':'1'}
    os.chdir(layout.run_root)
    os.execve(python, [python,'-B',str(layout.run_root/'scripts'/scripts[args.action])], environment)


if __name__ == '__main__': raise SystemExit(main())
