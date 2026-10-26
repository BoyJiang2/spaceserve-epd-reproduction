"""CPU regression checks for the observed driver-535 idle MPS response."""
import unittest
from capture_mps_clients import parse_clients


class StatusTests(unittest.TestCase):
    def test_exact_idle_no_server(self):
        self.assertEqual(parse_clients('Server not found\n', allow_no_server=True), [])

    def test_loaded_model_cannot_use_idle_response(self):
        with self.assertRaises(RuntimeError):
            parse_clients('Server not found\n')

    def test_existing_server_without_clients_idle_only(self):
        self.assertEqual(parse_clients('3671035\n', allow_no_server=True), [])
        with self.assertRaises(RuntimeError):
            parse_clients('3671035\n')

    def test_unknown_or_mixed_response_rejected(self):
        for value in ['connection failed', '21\nServer not found', 'PID ID SERVER DEVICE NAMESPACE\nServer not found']:
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                parse_clients(value, allow_no_server=True)

    def test_actual_client_columns(self):
        value = '90\nPID ID SERVER DEVICE NAMESPACE COMMAND\n92 1 90 GPU-d1b595ce 92 python model.py\n'
        self.assertEqual(parse_clients(value), [{'pid': 92, 'server_pid': 90, 'device_partial_uuid': 'GPU-d1b595ce'}])

    def test_bad_client_columns_rejected(self):
        value = 'PID ID SERVER DEVICE NAMESPACE COMMAND\n92 1 90 0 92 python\n'
        with self.assertRaises(RuntimeError):
            parse_clients(value)


if __name__ == '__main__':
    unittest.main()
