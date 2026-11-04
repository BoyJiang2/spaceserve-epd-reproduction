import json, os, sys
import torch
from vllm.v1 import smcontroller as controller
torch.cuda.init()
assert controller.libsmctrl_path == "/local/boyjiang/spaceserve/assets/build/libsmctrl.so"
properties = torch.cuda.get_device_properties(0)
result = {"executable": sys.executable, "library_path": controller.libsmctrl_path, "visible_devices": os.environ["CUDA_VISIBLE_DEVICES"], "logical_device": torch.cuda.current_device(), "name": properties.name, "sm_count": properties.multi_processor_count, "capability": torch.cuda.get_device_capability(0)}
result.update(smctrl_tpc_estimate=controller.get_tpc_info_cuda(0), mask_effect_verified=False, note="Library source warns Hopper TPC estimate is untested; this probe does not set a mask")
print(json.dumps(result), flush=True)
