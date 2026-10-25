"""Validate the delivered experiment data and mechanism evidence offline."""
import argparse
import hashlib
import json
import pathlib
import tarfile
from audit_matrix import audit


parser = argparse.ArgumentParser()
parser.add_argument("root", type=pathlib.Path)
args = parser.parse_args()
root = args.root.resolve()
with tarfile.open(root / "data/dataset.tar.gz", "r:gz") as bundle:
    dataset = json.load(bundle.extractfile("dataset/manifest.json"))
    assert len(dataset["images"]) == 20
    for item in dataset["images"]:
        assert hashlib.sha256(bundle.extractfile("dataset/" + item["file"]).read()).hexdigest() == item["sha256"]
summary = json.loads((root / "report/summary.json").read_text())
assert len(summary) == 30 and sum(row["requests"] for row in summary) == 9000
matrices = []
for host in ("sapphire1", "sapphire3"):
    for directory in sorted((root / "data/raw" / host).iterdir()):
        if directory.is_dir() and (directory / "COMPLETED").exists():
            matrices.append(audit(directory, "space" in directory.name and "l20" in directory.name))
assert len(matrices) == 7 and sum(item["measured_requests"] for item in matrices) == 9000

cases, reference_quality_limits = 0, 0
for host, filenames in {
    "sapphire1": ["space-v072-mps-correctness.json", "space-concurrency8-correctness.json"],
    "sapphire3": ["epd-correctness-fixed.json", "space-v072-mps-correctness.json", "space-mask-v072-mps-correctness.json",
                  "space-mask-concurrency8-correctness.json"],
}.items():
    for filename in filenames:
        records = json.loads((root / "evidence" / host / filename).read_text())
        assert len(records) == (8 if "concurrency8" in filename else 7)
        assert all(row.get("engine_check_passed", row.get("routing_passed", True))
                   and row["exact_token_ids_equal"] for row in records), filename
        reference_quality_limits += sum(row.get("reference_quality_limit", False) for row in records)
        assert len({row["reference"]["output"] for row in records[:4]}) == 4
        cases += len(records)
assert cases == 44
epd_c8 = root / "evidence/sapphire3/epd-concurrency8-correctness.json"
if epd_c8.exists():
    records = json.loads(epd_c8.read_text())
    assert len(records) == 8 and all(row["engine_check_passed"] and row["exact_token_ids_equal"] for row in records)
    cases += 8
else:
    failure = json.loads((root / "evidence/sapphire3/epd-warm-c8-failure.json").read_text())
    assert failure["client_timeout_s"] == 120 and failure["concurrency"] == 8
    assert "TimeoutError" in (root / "evidence/sapphire3/logs/epd-warm-c8-check.log").read_text()
ipc1 = json.loads((root / "evidence/sapphire1/cuda-ipc.json").read_text())
ipc3 = json.loads((root / "evidence/sapphire3/cuda-ipc.json").read_text())
assert ipc1["child_returncode"] != 0 and "217" in ipc1["stderr"]
assert ipc3["child_returncode"] == 0 and json.loads(ipc3["stdout"])["data_equal"]
for host, filename in [("sapphire1", "space-mps-overlap.json"), ("sapphire3", "space-mps-overlap.json"),
                       ("sapphire3", "space-mask-mps-overlap.json")]:
    analysis = json.loads((root / "evidence" / host / filename).read_text())
    assert analysis["kernel_overlap_us"] > 0 and analysis["kernel_overlap_observed"]
assert '"mask_effect_observed":true' in (root / "evidence/sapphire3/sm-mask-with-mps.jsonl").read_text()
assert "unsupported" in (root / "evidence/sapphire1/sm-mask.jsonl").read_text().lower()
native = [json.loads((root / "evidence" / host / "native-extensions-manifest.json").read_text()) for host in ("sapphire1", "sapphire3")]
assert {row["source"]: row["sha256"] for row in native[0]} == {row["source"]: row["sha256"] for row in native[1]}
comparisons = json.loads((root / "report/output-comparison.json").read_text())
assert len(comparisons) == 16 and sum(row["processed_inputs_equal"] for row in comparisons) == 4800
status = json.loads((root / "report/experiment-status.json").read_text())
assert not status["goal_complete"] and status["diagnostic_only_requests"] == 1800
assert all(row["result_validity"] == ("diagnostic_only" if row["role"] == "epd-l20" else "measurement_valid") for row in summary)
platform = json.loads((root / "evidence/sapphire3/iommu-platform.json").read_text())
assert platform["unsupported_bare_metal_dma_iommu"] and len(platform["devices"]) == 8
for pair in ("0-to-1", "1-to-2"):
    peer = json.loads((root / "evidence/sapphire3" / f"cuda-runtime-peer-{pair}.json").read_text())
    assert peer["source_validated"] and peer["peer_capability"] and not peer["data_equal"]
    assert peer["source_sha256"] != peer["destination_sha256"]
native = json.loads((root / "evidence/sapphire3/native-kv-large-validated-source.json").read_text())
assert native["source_validation"]["source_validated"] and not native["records"][0]["data_equal"]
small_native = json.loads((root / "evidence/sapphire3/native-kv-2048-1-to-2.json").read_text())
assert small_native["source_validation"]["source_validated"] and not small_native["records"][0]["data_equal"]
guard = json.loads((root / "evidence/sapphire3/iommu-start-guard-test.json").read_text())
assert guard["passed"] and guard["exit_code"] == 1 and not guard["gpu_processes_after"]
for name in ("epd-l20.png", "spaceserve-4090.png", "spaceserve-l20.png", "kernel-overlap-l20-mask.png"):
    assert (root / "report" / name).stat().st_size > 10000
result = {"passed": True, "formal_configurations": 30, "formal_requests": 9000, "warmup_requests": 600,
          "correctness_cases": cases, "paired_formal_requests": 4800, "matrices": matrices,
          "model_semantic_reference_limit_cases": reference_quality_limits,
          "audit_scope": "Delivery data integrity; does not mean all experiment acceptance checks passed",
          "experiment_acceptance": "partial; EPD peer-copy data consistency failed",
          "diagnostic_only_requests": 1800, "measurement_valid_requests": 7200,
          "unresolved": ["sapphire3 CUDA P2P copies corrupt data", "unsupported bare-metal DMA IOMMU configuration"],
          "unavailable": ["RTX 4090 cross-device CUDA IPC", "RTX 4090 libsmctrl SM mask on Driver API 13.0"]}
(root / "report/delivery-audit.json").write_text(json.dumps(result, indent=2))
print(json.dumps({key: value for key, value in result.items() if key != "matrices"}, indent=2))
