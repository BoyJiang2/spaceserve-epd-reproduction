"""Real local nonblocking sockets; no Ray/Torch/NVML/GPU or remote requests."""
import socket
import struct
import threading
import time
import unittest

from numeric_channel import NumericChannel, MAX_FRAME


class ShortSocket:
    def __init__(self,sock):self.sock=sock
    def fileno(self):return self.sock.fileno()
    def getblocking(self):return self.sock.getblocking()
    def close(self):return self.sock.close()
    def send(self,data):return self.sock.send(data[:3])
    def recv(self,count):return self.sock.recv(min(count,2))


class ChannelTests(unittest.TestCase):
    def pair(self):
        left,right=socket.socketpair();left.setblocking(False);right.setblocking(False)
        self.addCleanup(left.close);self.addCleanup(right.close)
        return left,right

    def test_roundtrip_real_short_reads_and_writes(self):
        left,right=self.pair();sender=NumericChannel(ShortSocket(left));receiver=NumericChannel(ShortSocket(right))
        value={'seq':1,'run_id':'unit','action':'copy','text':'中文'}
        sender.send(value,time.monotonic()+1,lambda:None)
        self.assertEqual(receiver.receive(time.monotonic()+1,lambda:None),value)

    def test_header_and_body_arrive_as_real_fragments(self):
        left,right=self.pair();body=b'{"phase":"numeric"}';errors=[]
        def writer():
            try:
                for byte in struct.pack('!I',len(body))+body:
                    right.send(bytes([byte]));time.sleep(.001)
            except BaseException as error:errors.append(error)
        thread=threading.Thread(target=writer);thread.start()
        try:self.assertEqual(NumericChannel(left).receive(time.monotonic()+2,lambda:None),{'phase':'numeric'})
        finally:thread.join(timeout=2)
        self.assertFalse(thread.is_alive());self.assertEqual(errors,[])

    def test_backpressure_send_hits_deadline_without_reader(self):
        left,right=self.pair();left.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,4096)
        channel=NumericChannel(left);start=time.monotonic()
        with self.assertRaises(TimeoutError):channel.send({'data':'x'*(MAX_FRAME-100)},start+.05,lambda:None)
        self.assertTrue(channel.failed)
        with self.assertRaises(RuntimeError):channel.send({},time.monotonic()+1,lambda:None)

    def test_partial_header_eof_is_terminal(self):
        left,right=self.pair();right.send(b'\0\0');right.close();channel=NumericChannel(left)
        with self.assertRaises(EOFError):channel.receive(time.monotonic()+1,lambda:None)
        self.assertTrue(channel.failed)

    def test_partial_body_eof_is_terminal(self):
        left,right=self.pair();right.send(struct.pack('!I',20)+b'{}');right.close();channel=NumericChannel(left)
        with self.assertRaises(EOFError):channel.receive(time.monotonic()+1,lambda:None)
        self.assertTrue(channel.failed)

    def test_zero_and_oversize_headers_refused_without_body(self):
        for size in (0,MAX_FRAME+1):
            with self.subTest(size=size):
                left,right=self.pair();right.send(struct.pack('!I',size));channel=NumericChannel(left)
                with self.assertRaises(ValueError):channel.receive(time.monotonic()+1,lambda:None)
                self.assertTrue(channel.failed)

    def test_strict_json_rejects_duplicate_nan_array_utf8_and_suffix(self):
        for body in (b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":1e999}',b'[]',b'\xff',b'{}{}'):
            with self.subTest(body=body):
                left,right=self.pair();right.send(struct.pack('!I',len(body))+body);channel=NumericChannel(left)
                with self.assertRaises((ValueError,UnicodeError)):channel.receive(time.monotonic()+1,lambda:None)
                self.assertTrue(channel.failed)

    def test_cancellation_during_partial_frame(self):
        left,right=self.pair();right.send(b'\0');channel=NumericChannel(left);calls=[]
        def check():
            calls.append(1)
            if len(calls)>=4:raise RuntimeError('cancelled')
        with self.assertRaisesRegex(RuntimeError,'cancelled'):channel.receive(time.monotonic()+1,check)
        self.assertTrue(channel.failed)

    def test_bad_send_values_and_deadlines_are_terminal(self):
        for value,deadline,error in [([],time.monotonic()+1,ValueError),({'a':float('nan')},time.monotonic()+1,ValueError),
                                     ({},float('inf'),ValueError),({},time.monotonic()-1,TimeoutError)]:
            with self.subTest(value=value):
                left,right=self.pair();channel=NumericChannel(left)
                with self.assertRaises(error):channel.send(value,deadline,lambda:None)
                self.assertTrue(channel.failed)

    def test_blocking_socket_rejected(self):
        left,right=self.pair();left.setblocking(True)
        with self.assertRaises(ValueError):NumericChannel(left)


if __name__=='__main__':unittest.main()
