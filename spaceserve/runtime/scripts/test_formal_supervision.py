from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch

try:
    import formal_monitor
    import run_formal
except ModuleNotFoundError as error:
    raise unittest.SkipTest('requires actual target CPU dependencies') from error


class SupervisionTests(unittest.TestCase):
    def test_foreign_sample_causes_monitor_failure(self):
        valid={'foreign_compute_pids':[],'owned_processes':[{'pid':1}],'owned_process_sum_bytes':123}
        formal_monitor.validate_sample([valid])
        with self.assertRaisesRegex(RuntimeError,'foreign target'):
            formal_monitor.validate_sample([{**valid,'foreign_compute_pids':[999]}])
        with self.assertRaisesRegex(RuntimeError,'attribution'):
            formal_monitor.validate_sample([{**valid,'owned_process_sum_bytes':None}])

    def test_monitor_midrun_failure_terminates_only_bound_client(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as directory:
            client=Mock(pid=123)
            client.poll.return_value=None
            client.wait.return_value=-15
            monitor=Mock()
            monitor.poll.side_effect=[None,1]
            bound=Mock()
            bound.create_time.return_value=10
            with patch.object(run_formal.subprocess,'Popen',return_value=client), \
                 patch.object(run_formal.psutil,'Process',return_value=bound), \
                 patch.object(run_formal,'terminate_owned') as terminate,patch.object(run_formal.time,'sleep'):
                with self.assertRaisesRegex(RuntimeError,'immediately stop'):
                    run_formal.supervised_benchmark(['CPU fixture'],{},Path(directory)/'client.log',monitor)
                terminate.assert_called_once_with(client,10)
                client.wait.assert_called_once_with(timeout=15)


if __name__=='__main__': unittest.main()
