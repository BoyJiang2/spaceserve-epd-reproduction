"""Single CPU lifecycle driver; parent owns head, observation and all cleanup."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time

from numeric_cpu_ray import PINNED_SOURCES, load_cpu_ray, verify_sources
from numeric_descendants import HeadProc
from numeric_cpu_receipts import publish as durable


CONTEXT_SHA = '3e3c5c9c1ea66ba4edd83c1c6f920102d613d9542fd20ce2f39bdab4f188e730'


def validate(spec):
    if set(spec)!={'root','run_id','session','folder','address','namespace','name','detached','delay_seconds'}:
        raise ValueError('Exact CPU scenario fields required')
    root=Path(spec['root']);folder=Path(spec['folder']);session=Path(spec['session'])
    if (not root.is_absolute() or root.resolve(strict=True)!=root
            or not folder.is_relative_to(root) or folder.resolve(strict=True)!=folder
            or not session.is_relative_to(root) or session.resolve(strict=True)!=session):
        raise ValueError('Canonical owned CPU scenario paths required')
    for path in (root,folder,session):
        for member in (path,*path.parents):
            if member.is_symlink():raise ValueError('Linked CPU scenario path')
            if member.is_relative_to(root) and (not member.is_dir() or member.stat().st_uid!=os.getuid()):
                raise ValueError('CPU scenario directory owner differs')
    if (not re.fullmatch(r'127\.0\.0\.2:[0-9]{4,5}',spec['address'])
            or not 1024<=int(spec['address'].split(':')[1])<=65535
            or type(spec['detached']) is not bool or type(spec['delay_seconds']) is not int or spec['delay_seconds'] not in (0,15)
            or any(not isinstance(spec[key],str) or not re.fullmatch('[A-Za-z0-9_.:-]{1,100}',spec[key])
                   for key in ('run_id','namespace','name'))):
        raise ValueError('Frozen single CPU actor intent required')
    if (os.environ.get('CUDA_VISIBLE_DEVICES')!=''
            or os.environ.get('EXP_ROOT')!=str(root) or os.environ.get('REPRO_RUN_ID')!=spec['run_id']
            or not Path.cwd().is_relative_to(root)):
        raise ValueError('Actual CPU driver scope differs')


class CPUActor:
    def __init__(self,spec,package):
        validate(spec)
        verify_sources(package,dict(PINNED_SOURCES,**{'runtime_context.py':CONTEXT_SHA}),os.getuid())
        import ray
        if any(name=='torch' or name.startswith('torch.') or name=='epdserve' or name.startswith('epdserve.') for name in sys.modules):
            raise ValueError('CPU actor imported model libraries')
        context=ray.get_runtime_context()
        self.facts=dict(process=HeadProc().snapshot(os.getpid(),os.getuid()),
            actor_id=context.get_actor_id(),job_id=context.get_job_id(),namespace=context.namespace,
            name=spec['name'],detached=spec['detached'],gpu_ids=ray.get_gpu_ids(),
            constructor_monotonic_s=time.monotonic(),delay_seconds=spec['delay_seconds'])
        if self.facts['namespace']!=spec['namespace'] or self.facts['gpu_ids']!=[]:
            raise ValueError('Actual CPU actor namespace/GPU allocation differs')
        durable(Path(spec['folder'])/'constructor-entered.json',self.facts)
        time.sleep(spec['delay_seconds'])

    def ready(self):return self.facts


def scenario(ray,spec,record,actor_type=CPUActor):
    """One creation only. Controlled-exit scenarios are terminated by the parent."""
    validate(spec)
    package=str(Path(ray.__file__).parent)
    context=ray.get_runtime_context()
    job_id=context.get_job_id()
    if not re.fullmatch('[0-9a-f]{8}',job_id) or context.namespace!=spec['namespace']:
        raise ValueError('Actual driver context differs')
    record('before_actor_create',intent=spec,job_id=job_id)
    actor=ray.remote(num_cpus=0,num_gpus=0,max_restarts=0,max_task_retries=0)(actor_type)
    actor=actor.options(name=spec['name'],namespace=spec['namespace'],
        lifetime='detached' if spec['detached'] else 'non_detached').remote(spec,package)
    actor_id=actor._actor_id.hex()
    if not re.fullmatch('[0-9a-f]{32}',actor_id):raise ValueError('Actual ActorID differs')
    expected=dict(actor_id=actor_id,job_id=job_id,namespace=spec['namespace'],name=spec['name'],detached=spec['detached'])
    record('actor_submitted',expected=expected)
    durable(Path(spec['folder'])/'actor-submitted.json',expected)
    # Ordinary Ray shutdown hook remains intact; no explicit shutdown/kill/retry.
    facts=ray.get(actor.ready.remote(),timeout=20)
    if any(facts.get(key)!=value for key,value in expected.items()):raise ValueError('Actor response identity differs')
    record('actor_ready',facts=facts)
    return expected,actor


def connect_existing(ray,spec):
    ray.init(address=spec['address'],namespace=spec['namespace'],log_to_driver=False,
        _node_ip_address='127.0.0.2')
    from ray._private import worker
    node=worker._global_node
    if node is None or node.is_head() is not False or node.all_processes or node.address!=spec['address']:
        raise ValueError('CPU driver owns unexpected Ray head/processes or address')
    return node


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--session-dir',required=True,type=Path)
    parser.add_argument('--spec',required=True,type=Path)
    parser.add_argument('--ray-package',required=True,type=Path)
    args=parser.parse_args();spec=json.loads(args.spec.read_bytes());validate(spec)
    if str(args.session_dir)!=spec['session']:raise ValueError('Actual selected private session differs')
    verify_sources(args.ray_package,{'runtime_context.py':CONTEXT_SHA},os.getuid())
    ray,preimport=load_cpu_ray(args.ray_package)
    folder=Path(spec['folder']);events=folder/'driver-events.jsonl'
    with events.open('x',encoding='utf8'):pass
    def record(event,**data):
        with events.open('a',encoding='utf8') as output:
            output.write(json.dumps(dict(event=event,monotonic_s=time.monotonic(),**data))+'\n')
            output.flush();os.fsync(output.fileno())
    record('preimport_verified',facts=preimport)
    node=connect_existing(ray,spec)
    record('connected_existing_head',address=node.address,private_session=str(args.session_dir),owns_processes=False)
    # Keep the handle alive until the parent has observed the live actor.
    expected,actor=scenario(ray,spec,record)
    durable(folder/'driver-ready.json',expected)
    # Let the parent bind the live constructor PID before normal driver exit.
    # This handshake belongs only to this CPU diagnostic, never the GPU backend.
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        marker=folder/'parent-observed.json'
        if marker.exists():
            if marker.is_symlink() or marker.stat().st_uid!=os.getuid() or marker.stat().st_size>4096:
                raise ValueError('Parent observation receipt differs')
            if json.loads(marker.read_bytes())!=expected:raise ValueError('Parent bound another CPU actor')
            record('parent_observed_live_actor',expected=expected)
            return
        time.sleep(.05)
    raise TimeoutError('Parent did not bind live CPU actor before driver exit')


if __name__=='__main__':main()
