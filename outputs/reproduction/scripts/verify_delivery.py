"""Validate the delivered experiment data and mechanism evidence offline."""
import argparse
import hashlib
import json
import pathlib
import tarfile
from audit_matrix import audit
from audit_h20 import audit_host
from audit_cache_fix import audit_host as audit_cache_host


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
assert len(summary) == 46 and sum(row["requests"] for row in summary) == 13800
matrices = []
for host in ("sapphire1", "sapphire3", "qjh003", "qjh005"):
    for directory in sorted((root / "data/raw" / host).iterdir()):
        if directory.is_dir() and (directory / "COMPLETED").exists():
            matrices.append(audit(directory, host == "qjh005" or ("space" in directory.name and "l20" in directory.name)))
assert len(matrices) == 11 and sum(item["measured_requests"] for item in matrices) == 13800
cache_fix = [audit_cache_host(root, host) for host in ('qjh003', 'qjh005')]
assert all(item['passed'] for item in cache_fix) and sum(item['formal_requests'] for item in cache_fix) == 1200
for item in cache_fix:
    matrices.extend(item['matrices'])
assert len(matrices) == 15 and sum(item['measured_requests'] for item in matrices) == 15000
continuity = json.loads((root / 'report/h20-cache-continuity.json').read_text())
assert len(continuity['results']) == 4 and all(item['passed'] for item in continuity['results'])
assert all(all(count == 20 for count in case['rgb_coverage_before_case'].values()) for item in continuity['results'] for case in item['cases'][1:])
for row in summary:
    if row['role'].startswith(('epd-h20', 'baseline-epd-h20')) and (row['images'], row['concurrency']) == (1, 1):
        assert row['source_kind'] == 'cache-fix' and row['source_case'].startswith('data/cache-fix/')
        host = 'qjh005' if row['role'].endswith('-qjh005') else 'qjh003'
        original_validity = json.loads((root / 'data/raw' / host / row['role'] / 'validity.json').read_text())
        assert original_validity['case_overrides']['images1-c1'] == 'superseded_for_cache_fairness'

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
assert len(comparisons) == 24 and sum(row["processed_inputs_equal"] for row in comparisons) == 7200
assert sum(row['requests'] for row in comparisons if row['source_kind'] == 'cache-fix') == 600
assert {(row['target'], row['case']) for row in comparisons if row['source_kind'] == 'cache-fix'} == {('epd-h20', 'images1-c1'), ('epd-h20-qjh005', 'images1-c1')}
status = json.loads((root / "report/experiment-status.json").read_text())
assert status["diagnostic_only_requests"] == 1800 and status["measurement_valid_requests"] == 12000
assert status['superseded_requests'] == 1200 and status['formal_http_requests'] == 15000
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
for name in ("epd-l20.png", "spaceserve-4090.png", "spaceserve-l20.png", "kernel-overlap-l20-mask.png", "epd-h20.png", "epd-h20-qjh005.png"):
    assert (root / "report" / name).stat().st_size > 10000
h20 = [audit_host(root, host) for host in ("qjh003", "qjh005")]
assert all(item["passed"] for item in h20) and sum(item["formal_requests"] for item in h20) == 4800
cases += sum(item["correctness_cases"] for item in h20)
cases += sum(item['correctness_cases'] for item in cache_fix)
assert cases == 194
result = {"passed": True, "formal_configurations": 50, "formal_requests": 15000, "warmup_requests": 1000,
          "selected_configurations": 46, "selected_formal_requests": 13800, "selected_warmup_requests": 920,
          "superseded_requests": 1200,
          "correctness_cases": cases, "paired_formal_requests": 7200, "matrices": matrices,
          "h20_acceptance": h20,
          "cache_fix_acceptance": cache_fix,
          "model_semantic_reference_limit_cases": reference_quality_limits,
          "audit_scope": "Raw measurement integrity, fixed-case service parity, H20 native transfer and restart acceptance; not universal semantic quality or paper-scale equivalence",
          "experiment_acceptance": "Complete" if status['goal_complete'] else "Technical data checks passed; independent review and G5 govern final acceptance",
          "goal_complete": status["goal_complete"],
          "independent_review": status["independent_review"],
          "diagnostic_only_requests": 1800, "measurement_valid_requests": 12000,
          "unresolved": status["required_remaining"],
          "historical_failure": ["sapphire3 CUDA P2P data corruption; retained as diagnostic evidence, replaced by validated H20 hosts"],
          "unavailable": ["RTX 4090 cross-device CUDA IPC", "RTX 4090 libsmctrl SM mask on Driver API 13.0"]}
(root / "report/delivery-audit.json").write_text(json.dumps(result, indent=2))
print(json.dumps({key: value for key, value in result.items() if key != "matrices"}, indent=2))
