"""Bounded actor metadata from the existing private GCS; never a release assertion."""
import base64
import hashlib
import importlib
import math
import os
from pathlib import Path
import re
import sys
import time

from numeric_cpu_ray import PINNED_SOURCES, verify_sources

STATES={0:'DEPENDENCIES_UNREADY',1:'PENDING_CREATION',2:'ALIVE',3:'RESTARTING',4:'DEAD'}


class GCSActorReader:
    def __init__(self, rpc, request, record, check, *, clock=time.monotonic, close=lambda:None):
        self.rpc,self.request,self.record,self.check,self.clock,self.close=rpc,request,record,check,clock,close

    @classmethod
    def connect(cls,address,package,record,check):
        match=re.fullmatch(r'127\.0\.0\.1:([0-9]{1,5})',address)
        if not match or not 1024<=int(match[1])<=65535:raise ValueError('Exact private loopback GCS required')
        package=Path(package);verify_sources(package,PINNED_SOURCES,os.getuid())
        ray=sys.modules.get('ray')
        if (ray is None or ray.__version__!='2.10.0' or Path(ray.__file__).absolute()!=package/'__init__.py'
                or ray.is_initialized() is not False):
            raise ValueError('GCS reader belongs to verified head parent, never another driver')
        grpc=importlib.import_module('grpc')
        service=importlib.import_module('ray.core.generated.gcs_service_pb2')
        stubs=importlib.import_module('ray.core.generated.gcs_service_pb2_grpc')
        data=importlib.import_module('ray.core.generated.gcs_pb2')
        method=service.DESCRIPTOR.services_by_name['ActorInfoGcsService'].methods_by_name['GetActorInfo']
        if (method.full_name!='ray.rpc.ActorInfoGcsService.GetActorInfo'
                or method.input_type.full_name!='ray.rpc.GetActorInfoRequest'
                or method.output_type.full_name!='ray.rpc.GetActorInfoReply'):
            raise ValueError('Reviewed Ray2.10 GCS method differs')
        if ({x.name:x.number for x in method.input_type.fields}!={'actor_id':1,'name':2}
                or {x.name:x.number for x in method.output_type.fields}!={'status':1,'actor_table_data':2}):
            raise ValueError('Reviewed GCS request/reply fields differ')
        expected={'actor_id':1,'job_id':4,'state':6,'max_restarts':7,'num_restarts':8,
            'is_detached':11,'name':12,'pid':16,'ray_namespace':19,'required_resources':28}
        fields=data.ActorTableData.DESCRIPTOR.fields_by_name
        if any(name not in fields or fields[name].number!=number for name,number in expected.items()):
            raise ValueError('Reviewed GCS actor metadata fields differ')
        channel=grpc.insecure_channel(address,options=(('grpc.enable_retries',0),('grpc.max_receive_message_length',1<<20)))
        try:stub=stubs.ActorInfoGcsServiceStub(channel)
        except BaseException:channel.close();raise
        return cls(stub.GetActorInfo,service.GetActorInfoRequest,record,check,close=channel.close)

    def guard(self,deadline):
        self.check()
        if type(deadline) not in (int,float) or not math.isfinite(deadline) or self.clock()>=deadline:
            raise TimeoutError('GCS observation deadline')

    def read(self,expected,deadline):
        self.guard(deadline)
        if (set(expected)!={'actor_id','job_id','namespace','name','detached'}
                or not isinstance(expected['actor_id'],str) or not re.fullmatch('[0-9a-f]{32}',expected['actor_id'])
                or not isinstance(expected['job_id'],str) or not re.fullmatch('[0-9a-f]{8}',expected['job_id'])
                or type(expected['detached']) is not bool
                or any(not isinstance(expected[k],str) or not re.fullmatch('[A-Za-z0-9_.:-]{1,160}',expected[k]) for k in ('namespace','name'))):
            raise ValueError('Bound actual ActorID/job/namespace required')
        self.record('gcs_actor_query_started',expected=dict(expected))
        self.guard(deadline)
        remaining=deadline-self.clock()
        if remaining<=0:raise TimeoutError('GCS observation deadline before RPC')
        reply=self.rpc(self.request(actor_id=bytes.fromhex(expected['actor_id'])),timeout=min(.25,remaining))
        self.guard(deadline)
        raw=reply.SerializeToString()
        if len(raw)>1<<20 or reply.status.code!=0:raise ValueError('GCS error/oversized response is not empty or released')
        row=reply.actor_table_data
        if (row.actor_id.hex()!=expected['actor_id'] or row.job_id.hex()!=expected['job_id']
                or row.ray_namespace!=expected['namespace'] or row.name!=expected['name']
                or row.is_detached is not expected['detached']):
            raise ValueError('GCS returned an actor outside this exact intent')
        if (type(row.state) is not int or row.state not in STATES or type(row.pid) is not int or row.pid<0
                or row.max_restarts!=0 or row.num_restarts!=0 or row.required_resources.get('GPU',0)!=0):
            raise ValueError('CPU zero-GPU/no-restart actor metadata differs')
        result=dict(actor_id=row.actor_id.hex(),job_id=row.job_id.hex(),namespace=row.ray_namespace,
            name=row.name,detached=row.is_detached,state=STATES[row.state],pid=row.pid,
            protobuf_sha256=hashlib.sha256(raw).hexdigest(),observed_monotonic_s=self.clock(),
            scope='raw_GCS_metadata_not_release_or_quiescence')
        self.record('gcs_actor_query_finished',result=result,protobuf_base64=base64.b64encode(raw).decode())
        self.guard(deadline)
        return result
