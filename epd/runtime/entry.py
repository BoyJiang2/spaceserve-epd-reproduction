"""Single EPD project entry. Incomplete adapters remain blocked before hardware access."""
import argparse
import json
import os
from pathlib import Path
import sys
from project_config import context


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=('plan','cpu','numeric','qualification','calibration','selected_g3','analyze'))
    parser.add_argument('--config',type=Path,default=Path(__file__).with_name('project-scope.json'))
    parser.add_argument('--permit',type=Path)
    parser.add_argument('--inputs',type=Path)
    parser.add_argument('--unit-template',type=Path)
    parser.add_argument('--select',type=Path)
    args=parser.parse_args()
    os.environ['EPD_CONFIG']=str(args.config.resolve(strict=True))
    layout=context()
    if args.action=='plan':
        print(json.dumps({**layout.describe(),'baseline':'three full replicas / tuned PD ablation / EPD',
            'model':'MiniCPM-V-2_6','dtype':'float16','TP':1,'GPU_budget':3,
            'numeric_transfers':36,'qualification_requests':120,'calibration_requests':960,
            'selected_g3_requests':360,'GPU_adapters_incomplete':['numeric','selected_g3'],
            'new_GPU_requests':0},indent=2))
        return 0
    if args.action in ('numeric','selected_g3'):
        raise NotImplementedError('Native36 / selected360 controller adapters are not complete; no GPU/claim/retry')
    source=Path(__file__).resolve().parent
    if args.action=='analyze':
        if not args.select:parser.error('analyze requires --select with actual bound calibration evidence')
        os.execv(sys.executable,[sys.executable,'-B',str(source/'experiment_plan.py'),'--select',str(args.select.resolve())])
    if args.action=='cpu':
        if not args.permit:parser.error('cpu requires a new independently reviewed exact --permit')
        if not layout.config.get('run_id'):raise ValueError('A real independent CPU cohort is required')
        os.chdir(layout.run_root)
        environment={**os.environ,'CUDA_VISIBLE_DEVICES':'','NVIDIA_VISIBLE_DEVICES':'void','PYTHONDONTWRITEBYTECODE':'1'}
        os.execve(sys.executable,[sys.executable,'-I','-S','-B',str(source/'cpu_target_runner.py'),'--permit',str(args.permit.resolve())],environment)
    layout.require_scope(args.action)
    if not args.inputs or not args.unit_template:parser.error('GPU unit requires --inputs and --unit-template')
    template=args.unit_template.resolve(strict=True)
    if json.loads(template.read_bytes())['phase']!=args.action:raise ValueError('Requested phase differs from the pinned template')
    os.chdir(layout.run_root)
    from preflight_controller import run
    config=json.loads((source/'preflight-static.json').read_bytes())
    report=run(config,json.loads(args.inputs.read_bytes()),args.inputs.resolve(),template)
    return 0 if report['state']=='released' and report['failure'] is None and not report['errors'] else 1


if __name__=='__main__':raise SystemExit(main())
