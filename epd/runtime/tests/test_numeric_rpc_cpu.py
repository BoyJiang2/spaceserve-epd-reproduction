"""Real local socket RPC with fake worker handler; no actor/Ray/GPU."""
import socket
import threading
import time
import unittest
from unittest.mock import Mock

from numeric_channel import NumericChannel
from numeric_rpc import NumericRPC


class RPCTests(unittest.TestCase):
    def pair(self):
        left,right=socket.socketpair();left.setblocking(False);right.setblocking(False)
        self.addCleanup(left.close);self.addCleanup(right.close)
        return NumericChannel(left),NumericChannel(right)

    def endpoint(self,channel,role,record=None):
        return NumericRPC(channel,'unit','a'*64,role,record or (lambda *args,**kwargs:None))

    def request(self,**changes):
        value=dict(run_id='unit',nonce='a'*64,seq=1,action='create_actor',argument={'uuid':'GPU-A'},deadline=time.monotonic()+1)
        value.update(changes);return value

    def test_two_roundtrips_keep_one_sequence_and_parent_journal(self):
        left,right=self.pair();events=[];parent=self.endpoint(left,'parent',lambda name,**data:events.append(name));driver=self.endpoint(right,'driver');errors=[]
        def serve():
            try:
                for _ in range(2):driver.serve_once(lambda action,arg,deadline,check:dict(action=action,argument=arg),time.monotonic()+3,lambda:None)
            except BaseException as error:errors.append(error)
        thread=threading.Thread(target=serve);thread.start()
        try:
            for action in ('create_actor','call'):
                reply=parent.request(action,{'uuid':'GPU-A'},time.monotonic()+1,lambda:None)
                self.assertEqual(reply['action'],action)
        finally:thread.join(timeout=3)
        self.assertFalse(thread.is_alive());self.assertEqual(errors,[])
        self.assertEqual((parent.sequence,driver.sequence),(2,2));self.assertEqual(events,['driver_request_started','driver_request_finished']*2)

    def test_parent_journal_failure_sends_no_frame(self):
        left,right=self.pair();record=Mock(side_effect=OSError('fsync'));parent=self.endpoint(left,'parent',record)
        with self.assertRaises(OSError):parent.request('call',{},time.monotonic()+1,lambda:None)
        self.assertEqual(right.sock.recv(1),b'');self.assertTrue(parent.failed)

    def test_deadline_after_journal_prevents_send(self):
        left,right=self.pair();parent=self.endpoint(left,'parent',lambda *args,**kwargs:time.sleep(.03))
        with self.assertRaises(TimeoutError):parent.request('call',{},time.monotonic()+.01,lambda:None)
        self.assertEqual(right.sock.recv(1),b'')

    def test_driver_rejects_wrong_scope_sequence_action_and_keys(self):
        for changes in ({'nonce':'b'*64},{'run_id':'foreign'},{'seq':True},{'seq':2},{'action':'shutdown'},{'extra':1}):
            with self.subTest(changes=changes):
                left,right=self.pair();driver=self.endpoint(right,'driver');handler=Mock();left.send(self.request(**changes),time.monotonic()+1,lambda:None)
                with self.assertRaises(ValueError):driver.serve_once(handler,time.monotonic()+2,lambda:None)
                handler.assert_not_called();self.assertTrue(driver.failed)

    def test_driver_cannot_extend_hard_deadline(self):
        left,right=self.pair();driver=self.endpoint(right,'driver');handler=Mock()
        left.send(self.request(deadline=time.monotonic()+10),time.monotonic()+1,lambda:None)
        with self.assertRaises(ValueError):driver.serve_once(handler,time.monotonic()+1,lambda:None)
        handler.assert_not_called()

    def test_parent_rejects_bad_reply_then_never_retries(self):
        for changes in ({'seq':True},{'seq':2},{'ok':1},{'action':'create_actor'},{'nonce':'b'*64}):
            with self.subTest(changes=changes):
                left,right=self.pair();parent=self.endpoint(left,'parent');reply=dict(run_id='unit',nonce='a'*64,seq=1,action='call',ok=True,result={});reply.update(changes)
                right.send(reply,time.monotonic()+1,lambda:None)
                with self.assertRaises(ValueError):parent.request('call',{},time.monotonic()+1,lambda:None)
                with self.assertRaises(RuntimeError):parent.request('call',{},time.monotonic()+1,lambda:None)
                self.assertEqual(parent.sequence,0)

    def test_eof_is_terminal_without_retry(self):
        left,right=self.pair();parent=self.endpoint(left,'parent');right.sock.close()
        with self.assertRaises((EOFError,OSError)):parent.request('call',{},time.monotonic()+1,lambda:None)
        self.assertTrue(parent.failed);self.assertEqual(parent.sequence,0)
        with self.assertRaises(RuntimeError):parent.request('call',{},time.monotonic()+1,lambda:None)

    def test_duplicate_request_does_not_reexecute_handler(self):
        left,right=self.pair();driver=self.endpoint(right,'driver');handler=Mock(return_value={});message=self.request()
        left.send(message,time.monotonic()+1,lambda:None);driver.serve_once(handler,time.monotonic()+2,lambda:None)
        left.send(message,time.monotonic()+1,lambda:None)
        with self.assertRaises(ValueError):driver.serve_once(handler,time.monotonic()+2,lambda:None)
        handler.assert_called_once()

    def test_handler_failure_has_no_success_ack(self):
        left,right=self.pair();driver=self.endpoint(right,'driver');left.send(self.request(),time.monotonic()+1,lambda:None)
        with self.assertRaises(RuntimeError):driver.serve_once(Mock(side_effect=RuntimeError('actor failed')),time.monotonic()+2,lambda:None)
        self.assertEqual(left.sock.recv(1),b'');self.assertEqual(driver.sequence,0)

    def test_concurrent_parent_request_refused_without_blocking(self):
        left,right=self.pair();entered=threading.Event();release=threading.Event();errors=[]
        def record(*args,**kwargs):entered.set();release.wait(timeout=1)
        parent=self.endpoint(left,'parent',record)
        def first():
            try:parent.request('call',{},time.monotonic()+2,lambda:None)
            except BaseException as error:errors.append(error)
        thread=threading.Thread(target=first);thread.start()
        try:
            self.assertTrue(entered.wait(timeout=1))
            with self.assertRaisesRegex(RuntimeError,'Concurrent'):parent.request('call',{},time.monotonic()+1,lambda:None)
        finally:release.set();thread.join(timeout=2)
        self.assertFalse(thread.is_alive());self.assertTrue(errors);self.assertTrue(parent.failed)

    def test_bad_nonce_constructor_refused(self):
        left,right=self.pair()
        with self.assertRaises(ValueError):NumericRPC(left,'unit','short','parent',lambda *a,**k:None)


if __name__=='__main__':unittest.main()
