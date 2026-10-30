"""Bounded local byte framing only; no Ray, GPU, retries or admission grants."""
import json
import math
import select
import struct
import time

MAX_FRAME = 1024*1024


def unique_object(pairs):
    result = {}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate JSON key')
        result[key]=value
    return result


def reject_constant(value):raise ValueError('Nonfinite JSON constant: '+value)


def finite_float(value):
    result=float(value)
    if not math.isfinite(result):raise ValueError('Nonfinite JSON number')
    return result


class NumericChannel:
    def __init__(self, sock):
        if sock.getblocking():raise ValueError('Inherited channel must already be nonblocking')
        self.sock, self.failed = sock, False

    def _remaining(self, deadline, check):
        if self.failed:raise RuntimeError('Channel failed; no operation retransmission')
        check()
        if type(deadline) not in (int,float) or not math.isfinite(deadline):
            raise ValueError('Finite monotonic deadline required')
        remaining = deadline-time.monotonic()
        if remaining<=0:raise TimeoutError('Numeric channel deadline')
        return remaining

    def _transfer(self, size, deadline, check, data=None):
        received=bytearray();offset=0
        while offset<size:
            remaining=self._remaining(deadline,check)
            select.select([self.sock] if data is None else [],[self.sock] if data is not None else [],[],min(.05,remaining))
            self._remaining(deadline,check)
            try:
                if data is None:
                    block=self.sock.recv(min(65536,size-offset))
                    if not block:raise EOFError('Incomplete numeric frame')
                    received.extend(block);offset+=len(block)
                else:
                    count=self.sock.send(memoryview(data)[offset:offset+65536])
                    if count==0:raise EOFError('Numeric peer closed during send')
                    offset+=count
            except (BlockingIOError,InterruptedError):continue
        self._remaining(deadline,check)
        return bytes(received)

    def send(self, value, deadline, check):
        try:
            self._remaining(deadline,check)
            if not isinstance(value,dict):raise ValueError('Metadata must be a JSON object')
            raw=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf8')
            if not 0<len(raw)<=MAX_FRAME:raise ValueError('Metadata frame size')
            self._transfer(4+len(raw),deadline,check,struct.pack('!I',len(raw))+raw)
        except BaseException:
            self.failed=True;self.sock.close();raise

    def receive(self, deadline, check):
        try:
            size=struct.unpack('!I',self._transfer(4,deadline,check))[0]
            if not 0<size<=MAX_FRAME:raise ValueError('Metadata frame size')
            raw=self._transfer(size,deadline,check)
            value=json.loads(raw.decode('utf8'),object_pairs_hook=unique_object,parse_constant=reject_constant,parse_float=finite_float)
            if not isinstance(value,dict):raise ValueError('Metadata must be a JSON object')
            self._remaining(deadline,check)
            return value
        except BaseException:
            self.failed=True;self.sock.close();raise
