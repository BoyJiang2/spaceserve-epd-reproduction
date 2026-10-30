"""One conditional-code-approved startup; original inference program stays frozen."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

RUNTIME='edcaa1bd25934591a21dc2e99a51cf07a6ec39c6'
ROOT=Path('/local/boyjiang/spaceserve/runs/space-20261031-0000')
REPO=Path('/local/boyjiang/spaceserve/repo')
STAGE=Path('/local/boyjiang/spaceserve/staging/space-20261031-0000')


def digest(raw):return hashlib.sha256(raw).hexdigest()


def input_core(value):
    value=dict(value)
    del value['utc'];del value['verified_epoch']
    return digest(json.dumps(value,sort_keys=True,separators=(',',':')).encode())


def resolve(template,authorization,new_input,new_rows,new_manifest,now):
    if not authorization['passed'] or authorization['scope']!='closed-startup-1':
        raise ValueError('Independent conditional code approval required')
    if input_core(new_input)!=template['input_core_sha256']:
        raise ValueError('Input semantics changed')
    if not 0<=now-new_input['verified_epoch']<900:
        raise ValueError('Fresh real verification required')
    expected=copy.deepcopy(template['model_rows'])
    input_bytes=(json.dumps(new_input,indent=2)).encode()
    for row in expected:
        if row['path']=='evidence/MODEL_INPUTS_VERIFIED-attempt1.json':
            row.update(bytes=len(input_bytes),sha256=digest(input_bytes))
    if expected!=new_rows or json.loads(new_manifest)!=new_rows:raise ValueError('Non-input model manifest member changed')
    value=copy.deepcopy(template['code_approval'])
    if value['allowed_actions']!=['preflight-models'] or value['model_correctness_approved'] is not False:
        raise ValueError('Approval scope changed')
    value.update(code_manifest_sha256=digest(new_manifest),input_receipt_sha256=digest(input_bytes),
        input_verified_epoch=new_input['verified_epoch'],model_main_before_epoch=new_input['verified_epoch']+900,
        resolved_from_review_sha256=value['review_sha256'],review_sha256=authorization['review_sha256'],
        reviewer=authorization['reviewer'],derivation_rule='same-input-core-time-only',
        conditional_adapter_sha256=authorization['adapter_sha256'])
    replacements={'configs/model-code-manifest.json':new_manifest,
                  'evidence/MODEL_INPUTS_VERIFIED-attempt1.json':input_bytes}
    for row in value['bound_files']:
        if row['path'] in replacements:
            raw=replacements[row['path']];row.update(bytes=len(raw),sha256=digest(raw))
    return value


def main(payload):
    auth=payload['authorization'];template=payload['template']
    assert digest(Path(__file__).read_bytes())==auth['adapter_sha256']
    assert digest(json.dumps(template,sort_keys=True,separators=(',',':')).encode())==auth['template_sha256']
    assert digest(payload['review'].encode())==auth['review_sha256']
    assert auth['passed'] is True and auth['scope']=='closed-startup-1'
    assert auth['runtime_commit']==RUNTIME and auth['model_requests']==313 and auth['work_seconds']==1800
    expected=dict(passed=True,phase='model',source_commit=RUNTIME,run_id=ROOT.name,
        boot_id=auth['boot_id'],proposed_config_sha256='f367fb4ee3040162d9c4fc027e4ba2aed15a0e2cee25d3fe9328dc2408c29043',
        booking_id='bk-20261030T0301-bd62e6dd',review_sha256=auth['review_sha256'])
    assert all(payload['execution_approval'].get(k)==v for k,v in expected.items())
    assert os.uname().nodename=='qjh003' and os.getuid()==2147 and os.sched_getaffinity(0)=={50}
    assert os.getpriority(os.PRIO_PROCESS,0)==10 and os.environ.get('CUDA_VISIBLE_DEVICES')==''
    assert Path(sys.prefix).resolve()==Path('/local/boyjiang/spaceserve/assets/envs/space').resolve()
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==auth['boot_id']=='65f52a67-afe4-4919-8646-4694255b48ee'
    assert time.time()+2160<=1793415600
    for part in (ROOT,STAGE,REPO):
        for path in (part,*part.parents):
            assert not path.is_symlink()
            if path.is_relative_to(Path('/local/boyjiang/spaceserve')):assert path.stat().st_uid==2147
    git=['git','--no-optional-locks','-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-C',str(REPO)]
    def source(path):return subprocess.check_output(git+['show',RUNTIME+':'+path],timeout=15)
    assert subprocess.check_output(git+['rev-parse','HEAD'],text=True).strip()==RUNTIME
    assert not subprocess.check_output(git+['status','--porcelain','--untracked-files=all']).strip()
    previous=json.loads((STAGE/'model.exit.json').read_bytes());assert previous['exit_code']==1
    records=json.loads((STAGE/'model.log').read_text().splitlines()[-1])
    assert records['exit_code']==1 and not records['remaining'] and not records['unknown_marked']
    for row in records['registered']:assert not Path('/proc',str(row['pid'])).exists()
    assert 'G2_MODEL_CODE_APPROVED.json' in (ROOT/'evidence/models-attempt1-controller.log').read_text()
    assert not subprocess.check_output(['nvidia-smi','--id=2','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    assert not (ROOT/'results/preflight-models-attempt1').exists()
    for name in ['evidence/G2_MODEL_CODE_APPROVED.json','evidence/MODEL_INPUTS_VERIFIED-closed-previous.json',
                 'configs/model-code-manifest-closed-previous.json']:
        assert not os.path.lexists(ROOT/name)
    for name in ['closed-startup1.intent.json','model-closed-startup1.claim.json','model-closed-startup1-launcher.py']:
        assert not os.path.lexists(STAGE/name)
    old_manifest=ROOT/'configs/model-code-manifest.json'
    cfg=json.loads((ROOT/'configs/project.json').read_bytes())
    receipt=json.loads((ROOT/'evidence/GIT_DEPLOYED.json').read_bytes())
    assert receipt['commit']==cfg['source_commit']==RUNTIME
    assert receipt['source_manifest_sha256']==cfg['source_manifest_sha256']=='027467633286b8d976f60b0bc4897efe067fa784886a1f54150ae39edc2ad6af'
    assert digest(old_manifest.read_bytes())==template['previous_model_manifest_sha256']
    for row in template['model_rows']:
        path=ROOT/row['path'];assert not path.is_symlink() and path.resolve().is_relative_to(ROOT.resolve())
        assert path.stat().st_size==row['bytes'] and digest(path.read_bytes())==row['sha256']
    with (STAGE/'closed-startup1.intent.json').open('x') as out:
        json.dump(dict(runtime_commit=RUNTIME,authorization=auth,started_epoch=time.time(),prior_requests=0),out,indent=2)
    os.environ.update(SPACESERVE_CONFIG=str(ROOT/'configs/project.json'),HF_HUB_OFFLINE='1',
        TRANSFORMERS_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tools')]
    old_input=ROOT/'evidence/MODEL_INPUTS_VERIFIED-attempt1.json'
    old_input.rename(ROOT/'evidence/MODEL_INPUTS_VERIFIED-closed-previous.json')
    import verify_model_inputs
    verify_model_inputs.main()
    new_input=json.loads(old_input.read_bytes())
    assert input_core(new_input)==template['input_core_sha256']
    old_manifest.rename(ROOT/'configs/model-code-manifest-closed-previous.json')
    import prepare_manifest
    prepare_manifest.freeze('model')
    manifest=old_manifest.read_bytes();rows=json.loads(manifest)
    assert old_input.read_bytes()==json.dumps(new_input,indent=2).encode()
    approval=resolve(template,auth,new_input,rows,manifest,time.time())
    for row in approval['bound_files']:assert digest((ROOT/row['path']).read_bytes())==row['sha256']
    with (ROOT/'evidence/G2_MODEL_CODE_APPROVED.json').open('x') as out:json.dump(approval,out,indent=2)
    prefix='import sys;sys.path[:0]='+repr([str(ROOT/'scripts'),str(ROOT/'tools')])+'\n'
    prefix+="from runtime_config import context\nfrom cpu_placement import apply\nc=context();c.require_scope('model');apply(c.config,'model')\n"
    launcher=source('spaceserve/runtime/scripts/model_launcher.py').decode()
    for old,new in [('MODELS_ATTEMPT1_STARTED.json','MODELS_ATTEMPT1_CLOSED1_STARTED.json'),
                    ('models-attempt1-controller.log','models-attempt1-closed1-controller.log'),
                    ('models-attempt1-exit.json','models-attempt1-closed1-exit.json')]:
        assert launcher.count(old)==1;launcher=launcher.replace(old,new)
    launcher_path=STAGE/'model-closed-startup1-launcher.py'
    with launcher_path.open('x') as out:out.write(prefix+launcher)
    controller=source('tools/run_space_window_20261030.py').decode()
    for suffix in ('.claim.json','.log','.exit.json'):
        old='stage/(args.phase+'+repr(suffix)+')';assert controller.count(old)==1
        controller=controller.replace(old,'stage/(args.phase+'+repr('-closed-startup1'+suffix)+')')
    namespace={'__name__':'closed_model_controller','__file__':str(REPO/'tools/run_space_window_20261030.py')}
    exec(compile(controller,'<record-renamed-original-model-controller>','exec'),namespace)
    def command(phase,config,commit):
        assert phase=='model' and commit==RUNTIME
        return [str(Path('/local/boyjiang/spaceserve/assets/envs/space/bin/python')),'-B',str(launcher_path)]
    namespace['command']=command
    policy={};exec(compile(source('tools/space_window_20261030.py'),'<original-window-policy>','exec'),policy)
    cfg=json.loads(source('spaceserve/runtime/configs/qjh003-20261030-0400.proposed.json'))
    proof=policy['human_confirmation'](cfg,int(time.time()*1000))
    for name,value in [('closed-startup1-approval.json',payload['execution_approval']),('closed-startup1-snapshot.json',proof)]:
        with (STAGE/name).open('x') as out:json.dump(value,out,indent=2)
    sys.argv=['closed-model','model','--commit',RUNTIME,'--approval',str(STAGE/'closed-startup1-approval.json'),
              '--snapshot',str(STAGE/'closed-startup1-snapshot.json')]
    namespace['main']()


if __name__=='__main__':main(json.load(sys.stdin))
