import contextlib,copy,io,json,time,tempfile,unittest
from pathlib import Path
from relocate_epd_assets_cpu import OLD_ENV,NEW_ENV,rewrite,cpu_permission,known_startup,terminal_report

class RelocationTests(unittest.TestCase):
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
