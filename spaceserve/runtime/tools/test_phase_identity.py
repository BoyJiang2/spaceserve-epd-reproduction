"""CPU-only fake process metadata; never inspect or signal actual processes."""
import sys
import types
import unittest
from unittest.mock import patch

import phase_identity as identity


class IdentityTests(unittest.TestCase):
    def test_parent_child_reuse_uid_unknown_and_missing(self):
        class Gone(Exception): pass
        class Denied(Exception): pass
        state = {}
        def process(pid):
            value = state.get(pid)
            if value == 'denied': raise Denied()
            if value is None: raise Gone()
            return types.SimpleNamespace(create_time=lambda: value[0],
                uids=lambda: types.SimpleNamespace(real=value[1]),
                is_running=lambda: True, status=lambda: 'running')
        fake = types.SimpleNamespace(Process=process, NoSuchProcess=Gone, AccessDenied=Denied, STATUS_ZOMBIE='zombie')
        started = {'controller_id': 'SYNTHETIC', 'pid': 11, 'process_created': 1., 'started_unix': 1.}
        terminal = {**started, 'exit_code': 1, 'child_pid': 12, 'child_created': 2.}
        with patch.dict(sys.modules, {'psutil': fake}):
            identity.validate_terminal(started, terminal)
            for pid, value, message in [(11,(1.,2147),'controller still live'),
                                         (12,(2.,2147),'child still live'),
                                         (11,(1.,999),'UID'), (11,'denied','cannot confirm')]:
                state.clear();state[pid] = value
                with self.assertRaisesRegex(RuntimeError, message):
                    identity.validate_terminal(started, terminal)
            state.clear();state[11] = (99.,2147)
            identity.validate_terminal(started, terminal)
            with self.assertRaisesRegex(RuntimeError, 'phase exit'):
                identity.validate_terminal(started, {**terminal,'controller_id':'WRONG'})


if __name__ == '__main__':
    unittest.main()
