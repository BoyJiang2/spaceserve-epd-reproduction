"""CPU-only check: first-execution hook samples the actual caller stream once."""
from types import SimpleNamespace
from unittest.mock import Mock, patch
import service_sm_probe

calls = []
worker = SimpleNamespace(execute_vision_encoder=lambda value: calls.append(value))
original = worker.execute_vision_encoder
stream = object()
sample = Mock()
with patch.object(service_sm_probe, 'measure', sample), patch.object(service_sm_probe.torch.cuda, 'current_stream', return_value=stream):
    service_sm_probe.arm_first_execution(worker)
    worker.execute_vision_encoder('first')
    worker.execute_vision_encoder('second')
sample.assert_called_once_with(stream, 'first-encoder-execution')
assert calls == ['first', 'second'] and worker.execute_vision_encoder is original
print('CPU first-execution hook PASS; no CUDA operations called')
