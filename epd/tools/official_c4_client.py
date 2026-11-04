"""Four distinct-image requests at concurrency four; diagnostic, never formal results."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import json
import math
from pathlib import Path
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--deadline-epoch", type=float, required=True)
    args = parser.parse_args()
    url = urllib.parse.urlparse(args.endpoint)
    assert url.scheme == "http" and url.hostname == "127.0.0.1"
    assert 1024 <= url.port <= 65535 and url.path == "/generate"
    assert args.run.is_dir()
    template = json.loads(args.template.read_text())
    images = json.loads(args.images.read_text())
    assert len(images) == 4 and len({Path(x["path"]).name for x in images}) == 4
    assert template["max_tokens"] == 128 and template["stream"] is False
    assert len(template["input"]["multi_modal_data"]["images_paths"]) == 1
    for item in images:
        assert hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest() == item["sha256"]
    assert not (args.run / "batch-result.json").exists()
    prepared = []
    for index, image in enumerate(images):
        payload = copy.deepcopy(template)
        payload["input"]["multi_modal_data"]["images_paths"] = [image["path"]]
        encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()
        prefix = args.run / ("client-" + str(index))
        with Path(str(prefix) + ".request.json").open("xb") as stream:
            stream.write(encoded)
        record = {"index": index, "image": image, "endpoint": args.endpoint,
                  "request_sha256": hashlib.sha256(encoded).hexdigest(),
                  "intent_epoch": time.time(), "success": False, "metrics_complete": False,
                  "client_ttft_s": None, "actual_visual_tokens": None}
        with Path(str(prefix) + ".intent.json").open("x") as stream:
            json.dump(record, stream, ensure_ascii=False, indent=2)
        prepared.append((prefix, encoded, record))
    barrier = threading.Barrier(4, timeout=10)
    def request(index):
        prefix, encoded, record = prepared[index]
        try:
            barrier.wait()
            remaining = args.deadline_epoch - time.time() - 5
            if remaining <= 0:
                raise TimeoutError("Common request deadline expired")
            record["submitted_perf"] = time.perf_counter()
            record["submitted_epoch"] = time.time()
            req = urllib.request.Request(args.endpoint, data=encoded,
                                         headers={"Content-Type": "application/json"})
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            try:
                with opener.open(req, timeout=min(120, remaining)) as response:
                    body = response.read()
                    record["completed_perf"] = time.perf_counter()
                    record["http_code"] = response.status
                    record["response_headers"] = dict(response.headers.items())
            except urllib.error.HTTPError as error:
                body = error.read()
                record["completed_perf"] = time.perf_counter()
                record["http_code"] = error.code
                raise RuntimeError("HTTP " + str(error.code))
            finally:
                if "body" in locals():
                    with Path(str(prefix) + ".response.json").open("xb") as stream:
                        stream.write(body)
            record.setdefault("completed_perf", time.perf_counter())
            record["client_e2e_s"] = record["completed_perf"] - record["submitted_perf"]
            data = json.loads(body)
            tokens = data["timestamps"]
            assert record["http_code"] == 200 and isinstance(data["output"], str) and data["output"].strip()
            assert isinstance(tokens, list) and len(tokens) == 128
            record.update(actual_output_events=len(tokens), output=data["output"],
                          prompt_token_len=data["prompt_token_len"],
                          processed_prompt_token_len=data["processed_prompt_token_len"], success=True)
            try:
                assert all(isinstance(t, (int, float)) and math.isfinite(t) for t in tokens)
                assert all(a <= b for a, b in zip(tokens, tokens[1:]))
                issued = [x["timestamp"] for x in data["lifetime_events"] if x["event_type"] == "issued"]
                assert len(issued) == 1 and math.isfinite(issued[0])
                assert record["submitted_perf"] <= issued[0] <= tokens[0] <= tokens[-1] <= record["completed_perf"]
                record.update(server_ttft_s=tokens[0] - issued[0],
                              server_tpot_s=(tokens[-1] - tokens[0]) / (len(tokens) - 1),
                              metrics_complete=True)
            except Exception as error:
                record.update(metric_error=repr(error), server_ttft_s=None, server_tpot_s=None)
        except Exception as error:
            record["error"] = repr(error)
        finally:
            record.setdefault("completed_perf", time.perf_counter())
            if "submitted_perf" in record:
                record.setdefault("client_e2e_s", record["completed_perf"] - record["submitted_perf"])
            record["completed_epoch"] = time.time()
            with Path(str(prefix) + ".record.json").open("x") as stream:
                json.dump(record, stream, ensure_ascii=False, indent=2)
        return record
    started = time.time()
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(request, range(4)))
    events = sorted((r[key], delta) for r in records if "submitted_perf" in r
                    for key, delta in [("submitted_perf", 1), ("completed_perf", -1)])
    inflight = peak = 0
    for _, delta in events:
        inflight += delta
        peak = max(peak, inflight)
    result = {"diagnostic_not_formal": True, "started_epoch": started, "ended_epoch": time.time(),
              "concurrency_target": 4, "observed_peak_inflight": peak,
              "successes": sum(r["success"] for r in records), "requests": records,
              "metric_definitions": {
                  "server_ttft_s": "first generation event minus issued; excludes API image loading; not client streaming TTFT",
                  "server_tpot_s": "last minus first generation event / (event count - 1)",
                  "client_e2e_s": "HTTP submit through reading complete JSON response",
                  "actual_visual_tokens": "not measured; processed prompt delta is not substituted",
                  "semantic_correctness": "pending full-model comparison and image review",
                  "observed_peak_inflight": "client submitted and not completed HTTP requests, not server execution or GPU overlap",
                  "clock": "same-host Python perf_counter; incompatible event clocks are rejected"}}
    with (args.run / "batch-result.json").open("x") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"successes": result["successes"], "observed_peak_inflight": peak}), flush=True)
    return 0 if result["successes"] == 4 and peak == 4 and all(r["metrics_complete"] for r in records) else 1

if __name__ == "__main__":
    raise SystemExit(main())
