import contextlib,copy,io,json,time,tempfile,unittest
import base64,hashlib,signal,sys,types
from pathlib import Path
from unittest.mock import patch
import relocate_epd_assets_cpu as relocation
from relocate_epd_assets_cpu import OLD_ENV,NEW_ENV,rewrite,cpu_permission,known_startup,terminal_report,window_end

class RelocationTests(unittest.TestCase):
    def test_apply_persists_permission_before_dependency_failure(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as name:
            root=Path(name);self.assertTrue(root.resolve().is_relative_to(Path(__file__).resolve().parent))
            site=root/'assets/envs/epd/lib/python3.10/site-packages';site.mkdir(parents=True)
            pth=site/'distutils-precedence.pth';pth.write_bytes(b'standard')
            rows=[]
            for index in range(61):
                path=pth if index==0 else root/f'assets/file{index}'
                if index:path.write_bytes(b'unchanged')
                rows.append(dict(path=path.relative_to(root).as_posix(),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),kind='unchanged'))
            original=root/'assets/build/epd-cuda/libcuda_ipc_utils.so';original.parent.mkdir(parents=True);original.write_bytes(b'fixture')
            (root/'staging').mkdir()
            permission=dict(origin='direct_user_instruction',quote='虽然后面的cpu没有预约 但是你可以随便用',valid_from_ms=1793260800000,valid_until_ms=1793264400000)
            cfg=dict(root=str(root),boot=relocation.BOOT,files=rows,python_links=[],stage='staging/apply-fixture',cpu_permission=permission,original_library=dict(path=original.relative_to(root).as_posix(),bytes=7,sha256=hashlib.sha256(b'fixture').hexdigest()),flat_library='assets/build/libcuda_ipc_utils.so',rpath=[str(root/f'missing{n}') for n in range(3)])
            raw=json.dumps(cfg).encode();now=1793260800000
            proof=dict(origin='gputime_read_only_api',read_only=True,observed_ms=now,resources=[dict(id='h20/qjh003',node='qjh003',active=True)],bookings=[])
            read_text=Path.read_text;iterdir=Path.iterdir
            def read(path,*args,**kwargs):
                if path.as_posix()=='/proc/sys/kernel/random/boot_id':return relocation.BOOT
                if path.as_posix()=='/proc/self/stat':return '42 (fixture) '+' '.join(['0']*20)
                return read_text(path,*args,**kwargs)
            def entries(path):return iter(()) if path.as_posix()=='/proc' else iterdir(path)
            with contextlib.ExitStack() as stack:
                for target,value in (('ROOT',root),('CONFIG_SHA',hashlib.sha256(raw).hexdigest())):stack.enter_context(patch.object(relocation,target,value))
                stack.enter_context(patch.dict(sys.modules,resource=types.SimpleNamespace(RLIMIT_AS=0,setrlimit=lambda *a:None)))
                for target,value in (('SIGALRM',14),('SIG_BLOCK',0),('SIG_SETMASK',2),('ITIMER_REAL',0)):stack.enter_context(patch.object(signal,target,value,create=True))
                for target in ('signal','setitimer','pthread_sigmask'):stack.enter_context(patch.object(signal,target,create=True))
                for target,value in (('getuid',2147),('sched_getaffinity',{50}),('getpriority',10)):stack.enter_context(patch.object(relocation.os,target,return_value=value,create=True))
                stack.enter_context(patch.object(relocation.os,'PRIO_PROCESS',0,create=True))
                stack.enter_context(patch.object(relocation.socket,'gethostname',return_value='qjh003'))
                stack.enter_context(patch.object(relocation.time,'time',return_value=now/1000))
                stack.enter_context(patch.object(Path,'read_text',read));stack.enter_context(patch.object(Path,'iterdir',entries))
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                with self.assertRaisesRegex(ValueError,'Required relocated dependency missing'):
                    relocation.relocate(dict(phase='apply',config=base64.b64encode(raw).decode(),booking=proof))
            claim=json.loads((root/'staging/apply-fixture/claim.json').read_bytes())
            self.assertEqual(claim['cpu_permission'],permission)
            self.assertFalse(claim['reservation_claimed'])
            self.assertFalse((root/'assets/build/libcuda_ipc_utils.so').exists())
    def test_exact_window_start_end_and_old_scope_refused(self):
        permission={'origin':'direct_user_instruction','quote':'虽然后面的cpu没有预约 但是你可以随便用',
                    'valid_from_ms':1793260800000,'valid_until_ms':1793264400000}
        self.assertEqual(window_end(permission,1793260800000),1793264400000)
        for now in (1793260799999,1793264400000,True,'1793260800000'):
            with self.subTest(now=now),self.assertRaises(ValueError):window_end(permission,now)
        for change in ({'valid_until_ms':1793246400000},{'valid_from_ms':True},{'valid_until_ms':1793268000000}):
            with self.subTest(change=change),self.assertRaises(ValueError):window_end(permission|change,1793260800000)
    def test_console_only_first_line_changes(self):
        raw=b'#!'+OLD_ENV+b'/bin/python\nbody='+OLD_ENV+b'\n'
        self.assertEqual(rewrite(raw,'console'),b'#!'+NEW_ENV+b'/bin/python\nbody='+OLD_ENV+b'\n')
    def test_console_preserves_crlf(self):
        self.assertEqual(rewrite(b'#!'+OLD_ENV+b'/bin/python\r\nprint(1)\r\n','console'),b'#!'+NEW_ENV+b'/bin/python\r\nprint(1)\r\n')
    def test_wrong_shebang_and_unknown_kind_rejected(self):
        for raw,kind in [(b'#!/usr/bin/python\n','console'),(b'data','other')]:
            with self.subTest(kind=kind),self.assertRaises(ValueError):rewrite(raw,kind)
    def test_activation_exactly_one_prefix(self):
        raw=b'VIRTUAL_ENV="'+OLD_ENV+b'"\r\n'
        self.assertEqual(rewrite(raw,'activation'),b'VIRTUAL_ENV="'+NEW_ENV+b'"\r\n')
        for raw in (b'none',OLD_ENV+OLD_ENV):
            with self.assertRaises(ValueError):rewrite(raw,'activation')
    def test_terminal_failure_reports_without_overwrite(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as name:
            stage=Path(name);self.assertTrue(stage.resolve().is_relative_to(Path(__file__).resolve().parent))
            marker=stage/'verify-terminal.json';marker.write_text('preserve')
            output=io.StringIO();state=dict(exit_code=0)
            with contextlib.redirect_stdout(output):failure=terminal_report(stage,'verify',state,True)
            self.assertIsInstance(failure,FileExistsError);self.assertEqual(marker.read_text(),'preserve')
            report=json.loads(output.getvalue());self.assertEqual(report['exit_code'],1);self.assertIn('terminal_write_error',report)

    def test_unknown_startup_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as name:
            site=Path(name);self.assertTrue(site.resolve().is_relative_to(Path(__file__).resolve().parent));(site/'distutils-precedence.pth').write_text('standard')
            known_startup(site)
            for filename in ('sitecustomize.py','usercustomize.py','extra.pth'):
                path=site/filename;path.write_text('unknown')
                with self.subTest(filename=filename),self.assertRaises(ValueError):known_startup(site)
                path.unlink()

    def test_cpu_permission_conflict_stale_and_reserve(self):
        now=1000000;proof=dict(origin='gputime_read_only_api',read_only=True,observed_ms=now,resources=[dict(id='h20/qjh003',node='qjh003',active=True)],bookings=[])
        cpu_permission(proof,now,240,now+600000)
        bad=copy.deepcopy(proof);bad['bookings']=[dict(resource_id='h20/qjh003',kind='cpu',user='other',start_ms=now,end_ms=now+600000)]
        with self.assertRaises(ValueError):cpu_permission(bad,now,240,now+600000)
        bad=copy.deepcopy(proof);bad['observed_ms']=now-300001
        with self.assertRaises(ValueError):cpu_permission(bad,now,240,now+600000)
        with self.assertRaises(ValueError):cpu_permission(proof,now,240,now+300000)
        bad=copy.deepcopy(proof);bad['bookings']=[dict(resource_id='h20/qjh003',kind=None,user='other',start_ms=now,end_ms=now+600000)]
        with self.assertRaises(ValueError):cpu_permission(bad,now,240,now+600000)

if __name__=='__main__':unittest.main()
