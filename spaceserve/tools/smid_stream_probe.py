"""Finite SMID samples; no model, MPS, global mask or completeness assertion."""
import hashlib
import json
import os
from pathlib import Path
import sys
import torch
import triton
import triton.language as tl
from vllm.v1 import smcontroller as controller

@triton.jit
def sample_smids(output):
    index = tl.program_id(0)
    smid = tl.inline_asm_elementwise("mov.u32 $0, %smid;", constraints="=r",
                                   args=[], dtype=tl.int32, is_pure=True, pack=1)
    tl.store(output + index, smid)

def words(mask):
    return [(mask >> shift) & 0xffffffff for shift in (96, 64, 32, 0)]

def main():
    output = Path(sys.argv[1])
    assert output.parent.is_dir()
    assert not output.exists()
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "3"
    library = Path("/local/boyjiang/spaceserve/assets/build/libsmctrl.so")
    assert controller.libsmctrl_path == str(library)
    assert hashlib.sha256(library.read_bytes()).hexdigest() == "529e2502f633b0d7ef07db2848c64e42154cea73992a794c27a31d0361e5e7c5"
    properties = torch.cuda.get_device_properties(0)
    sm_count = properties.multi_processor_count
    tpc_estimate = controller.get_tpc_info_cuda(0)
    record = {"sm_count": sm_count, "library_tpc_estimate": tpc_estimate,
              "mapping_assumption": "linear SMIDs and library SMs-per-TPC estimate; unverified on Hopper",
              "complete_SM_coverage_required": False, "stages": [],
              "model_stream_or_overlap_verified": False,
              "observed_constraints_satisfied": False}
    def save():
        output.write_text(json.dumps(record, indent=2) + "\n")
    save()
    try:
        assert 12 < tpc_estimate <= 128 and sm_count % tpc_estimate == 0, "Unsupported assumed mapping"
        ratio = sm_count // tpc_estimate
        lower = set(range(12 * ratio))
        upper = set(range(12 * ratio, sm_count))
        all_ids = set(range(sm_count))
        configurations = [("unmasked", None, all_ids),
                          ("encoder_default", 0xfff, upper),
                          ("complement", ((1 << 128) - 1) ^ 0xfff, lower)]
        baseline = set()
        buffer = torch.empty(sm_count * 64, dtype=torch.int32, device="cuda")
        for name, mask, allowed in configurations:
            stage = {"name": name, "mask_words": None if mask is None else words(mask),
                     "allowed_under_mapping_assumption": sorted(allowed), "rounds": []}
            record["stages"].append(stage)
            save()
            stream = torch.cuda.Stream()
            if mask is not None:
                controller.stream_lzc_mask(stream, words(mask))
            for repeat in range(5):
                with torch.cuda.stream(stream):
                    sample_smids[(sm_count * 64,)](buffer, num_warps=4)
                stream.synchronize()
                samples = buffer.cpu().tolist()
                observed = set(samples)
                stage["rounds"].append({"repeat": repeat, "observed": sorted(observed), "raw_smids": samples})
                save()
                assert observed and observed <= allowed, "Observed IDs outside hypothesized allowed set"
                if mask is None:
                    baseline.update(observed)
            if mask is None:
                assert baseline & lower and baseline & upper, "Baseline sampling power insufficient"
        record["observed_constraints_satisfied"] = True
        save()
        print(json.dumps({k: v for k, v in record.items() if k != "stages"}), flush=True)
    except BaseException as error:
        record["error"] = repr(error)
        save()
        raise

if __name__ == "__main__":
    main()
