"""Parent-owned native36 adapter; actual Ray driver/creation quiescence still required."""
import math
import time

from numeric_cache import transfer_vector


class NumericParentBackend:
    def __init__(self, claim, rpc, release, *, clock=time.perf_counter):
        self.claim,self.rpc,self.release,self.clock=claim,rpc,release,clock
        self.uuids=list(claim.config['gpu_uuids']);self.vector=transfer_vector(self.uuids)
        self.group,self.identities,self.creating=0,{},None
        self.failed=False

    def deadline(self, timeout, cleanup=False):
        if type(timeout) not in (int,float) or not math.isfinite(timeout) or timeout<=0:
            raise ValueError('Finite positive backend timeout required')
        if not cleanup:
            if self.failed:raise RuntimeError('Driver backend failed; no new work')
            self.claim.check()
        now=self.clock();end=self.claim.deadline-(0 if cleanup else self.claim.config['cleanup_seconds'])
        if now>=end:raise TimeoutError('Native backend phase boundary')
        return min(now+timeout,end)

    def before_send(self, deadline):
        self.claim.check()
        if self.clock()>=deadline:raise TimeoutError('Parent WAL consumed remaining work budget')

    def create_group(self, uuids, *, timeout):
        try:
            deadline=self.deadline(timeout)
            if list(uuids)!=self.uuids or self.group>=12 or self.creating is not None or self.release.known_identities():
                raise ValueError('Fresh exact group after confirmed prior release required')
            self.identities={}
            for index in range(len(self.uuids)):
                intent=dict(namespace=self.claim.inputs['run_id'],name='native-g'+str(self.group)+'-n'+str(index),
                    group=self.group,slot=index,allowed_gpu_uuids=list(self.uuids),scope=self.release.scope)
                self.release.record('actor_creating',intent=intent)
                self.creating=intent
                self.before_send(deadline)
                identity=self.rpc.request('create_actor',intent,deadline,self.claim.check)
                self.creating=dict(intent,returned_identity=identity)
                uuid=identity.get('gpu_uuid')
                if uuid not in self.uuids or uuid in self.identities:raise ValueError('Created worker assigned foreign or duplicate GPU')
                self.release.register(identity)
                self.identities[uuid]=identity
                self.creating=None
            if set(self.identities)!=set(self.uuids):raise ValueError('Actual worker GPU set differs')
            self.group+=1
            return [dict(self.identities[uuid]) for uuid in self.uuids]
        except BaseException as error:
            self.failed=True
            # A pending creation is never converted to a made-up release/identity.
            self.release.record('actor_creation_failed',pending=self.creating,error=repr(error),requires_quiescence=self.creating is not None)
            raise

    def call(self, uuid, operation, argument, *, timeout):
        try:
            deadline=self.deadline(timeout)
            if uuid not in self.identities or operation not in ('allocate','prepare','copy','sync'):
                raise ValueError('Exact registered worker and numeric operation required')
            if self.identities[uuid] not in self.release.known_identities():raise ValueError('Worker no longer registered live')
            if operation=='copy':
                transfer=argument['transfer'];ordinal=transfer['ordinal']
                if type(ordinal) is not int or not 0<=ordinal<len(self.vector) or transfer!=self.vector[ordinal]:
                    raise ValueError('Original finite transfer vector required')
                source_uuid=transfer['source_uuid']
                if (transfer['target_uuid']!=uuid or source_uuid not in self.identities
                        or argument['source']['identity']!=self.identities[source_uuid]):
                    raise ValueError('Actual source/importer identity differs')
                self.release.mapping_possible(self.identities[source_uuid],self.identities[uuid])
            self.before_send(deadline)
            return self.rpc.request('call',dict(gpu_uuid=uuid,operation=operation,argument=argument),deadline,self.claim.check)
        except BaseException:
            self.failed=True;raise

    def close(self, uuid, identity, *, timeout):
        end=self.deadline(timeout,cleanup=True)
        return self.release.close(uuid,identity,timeout=max(0,end-self.clock()))

    def known_identities(self):
        return self.release.known_identities()

    def assert_no_unresolved_creation(self):
        if self.creating is not None:
            raise RuntimeError('FAILED_RELEASE_UNCONFIRMED: actual pending creation must be resolved; no head shutdown')
