"""Single in-flight parent/driver metadata RPC; no actor implementation or GPU grant."""
import math
import re
import time
import threading


class NumericRPC:
    def __init__(self, channel, run_id, nonce, role, record):
        if (not isinstance(run_id,str) or not run_id or len(run_id)>128
                or not isinstance(nonce,str) or not re.fullmatch('[a-f0-9]{64}',nonce)
                or role not in ('parent','driver')):
            raise ValueError('Exact private RPC scope required')
        self.channel,self.run_id,self.nonce,self.role,self.record=channel,run_id,nonce,role,record
        self.sequence,self.failed=0,False
        self.inflight=threading.Lock()

    def guard(self, deadline, check):
        if self.failed:raise RuntimeError('RPC failed; no business operation retry')
        check()
        if type(deadline) not in (int,float) or not math.isfinite(deadline) or time.monotonic()>=deadline:
            raise TimeoutError('RPC deadline')

    def abort(self):
        self.failed=True;self.channel.failed=True;self.channel.sock.close()

    def scope(self, message, keys, sequence):
        if (set(message)!=keys or message.get('run_id')!=self.run_id or message.get('nonce')!=self.nonce
                or type(message.get('seq')) is not int or message['seq']!=sequence
                or message.get('action') not in ('create_actor','call')):
            raise ValueError('Unexpected RPC scope, sequence or action')

    def request(self, action, argument, deadline, check):
        acquired=self.inflight.acquire(blocking=False)
        try:
            if not acquired:raise RuntimeError('Concurrent RPC forbidden')
            if self.role!='parent' or action not in ('create_actor','call') or not isinstance(argument,dict):
                raise ValueError('Only parent fixed actor RPC allowed')
            self.guard(deadline,check)
            sequence=self.sequence+1
            message=dict(run_id=self.run_id,nonce=self.nonce,seq=sequence,action=action,argument=argument,deadline=deadline)
            self.record('driver_request_started',request=message)
            self.guard(deadline,check)
            self.channel.send(message,deadline,check)
            reply=self.channel.receive(deadline,check)
            self.scope(reply,{'run_id','nonce','seq','action','ok','result'},sequence)
            if reply['action']!=action or reply['ok'] is not True or not isinstance(reply['result'],dict):
                raise ValueError('Actual driver response differs')
            self.record('driver_request_finished',reply=reply)
            self.guard(deadline,check);self.sequence=sequence
            return reply['result']
        except BaseException:
            self.abort();raise
        finally:
            if acquired:self.inflight.release()

    def serve_once(self, handler, deadline, check):
        acquired=self.inflight.acquire(blocking=False)
        try:
            if not acquired:raise RuntimeError('Concurrent RPC forbidden')
            if self.role!='driver':raise ValueError('Only private driver can serve')
            self.guard(deadline,check)
            message=self.channel.receive(deadline,check);sequence=self.sequence+1
            self.scope(message,{'run_id','nonce','seq','action','argument','deadline'},sequence)
            requested=message['deadline']
            if (type(requested) not in (int,float) or not math.isfinite(requested) or requested>deadline
                    or not isinstance(message['argument'],dict)):
                raise ValueError('Driver request deadline or argument differs')
            self.guard(requested,check)
            result=handler(message['action'],message['argument'],requested,check)
            self.guard(requested,check)
            if not isinstance(result,dict):raise ValueError('Driver returns metadata only')
            reply=dict(run_id=self.run_id,nonce=self.nonce,seq=sequence,action=message['action'],ok=True,result=result)
            self.channel.send(reply,requested,check)
            self.sequence=sequence
        except BaseException:
            self.abort();raise
        finally:
            if acquired:self.inflight.release()
