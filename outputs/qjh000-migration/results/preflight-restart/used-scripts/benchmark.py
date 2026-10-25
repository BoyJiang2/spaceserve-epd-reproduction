"""Fixed-concurrency benchmark for /generate, executed on the server host."""
import argparse
import asyncio
import json
import pathlib
import time
import aiohttp
from transformers import AutoTokenizer


def percentile(values, fraction):
    values = sorted(values)
    if not values:
        return None
    index = (len(values) - 1) * fraction
    low = int(index)
    return values[low] + (values[min(low + 1, len(values) - 1)] - values[low]) * (index - low)


async def run(args):
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((args.dataset / "manifest.json").read_text())
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    marker = "<|vision_start|><|image_pad|><|vision_end|>" if "Qwen2-VL" in args.model else "(<image>./</image>)"
    prompt = tokenizer.apply_chat_template(
        [{"role": "user", "content": marker * args.images + manifest["prompt"]}],
        tokenize=False, add_generation_prompt=True)
    configuration = {**vars(args), "prompt": prompt, "timestamp_clock": "same-host time.perf_counter",
                     "ttft_definition": "first server token timestamp minus client submission; excludes first-token egress",
                     "tpot_definition": "(last token timestamp - first token timestamp)/(output tokens - 1)"}
    (args.output / "config.json").write_text(json.dumps(configuration, default=str, indent=2))
    rows = []
    semaphore = asyncio.Semaphore(args.concurrency)
    timeout = aiohttp.ClientTimeout(total=args.timeout)
    with (args.output / "requests.jsonl").open("a") as raw:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async def one(index, warmup, repetition):
                async with semaphore:
                    paths = [str(args.dataset / manifest["images"][(index * args.images + j) % len(manifest["images"])]["file"])
                             for j in range(args.images)]
                    body = {"input": {"prompt": prompt, "multi_modal_data": {"images_paths": paths}},
                            "stream": False, "max_tokens": args.tokens, "temperature": 0.0, "ignore_eos": True}
                    row = {"index": index, "warmup": warmup, "repetition": repetition,
                           "images": paths, "endpoint": args.urls[index % len(args.urls)]}
                    start = time.perf_counter()
                    try:
                        async with session.post(row["endpoint"] + "/generate", json=body) as response:
                            text = await response.text()
                            end = time.perf_counter()
                            if response.status != 200:
                                raise RuntimeError(f"HTTP {response.status}: {text[:2000]}")
                            result = json.loads(text)
                        stamps = result["timestamps"]
                        assert stamps and start <= stamps[0] <= stamps[-1] <= end, "invalid same-host timestamp domain"
                        token_count = len(result.get("output_token_ids", stamps))
                        assert token_count == len(stamps), "token timestamp count mismatch"
                        assert token_count == args.tokens, "fixed output length was not honored"
                        processed = result.get("processed_prompt_token_ids")
                        if processed is not None:
                            if "Qwen2-VL" in args.model:
                                visual_tokens = processed.count(tokenizer.convert_tokens_to_ids("<|image_pad|>"))
                            else:
                                starts = {getattr(tokenizer, key) for key in ("im_start_id", "slice_start_id") if hasattr(tokenizer, key)}
                                ends = {getattr(tokenizer, key) for key in ("im_end_id", "slice_end_id") if hasattr(tokenizer, key)}
                                inside, visual_tokens = False, 0
                                for token in processed:
                                    if token in starts:
                                        inside = True
                                    elif token in ends:
                                        inside = False
                                    elif inside:
                                        visual_tokens += 1
                            row["visual_tokens"] = visual_tokens
                        row.update(success=True, latency_s=end - start, ttft_s=stamps[0] - start,
                                   tpot_s=(stamps[-1] - stamps[0]) / (token_count - 1) if token_count > 1 else None,
                                   output_tokens=token_count, submission_perf_counter=start, response=result)
                    except Exception as error:
                        row.update(success=False, latency_s=time.perf_counter() - start, error=repr(error))
                    raw.write(json.dumps(row) + "\n")
                    raw.flush()
                    return row

            warm = await asyncio.gather(*(one(i, True, -1) for i in range(args.warmup)))
            if any(not item["success"] for item in warm):
                raise RuntimeError("warmup failed; inspect requests.jsonl")
            for repetition in range(args.repetitions):
                start = time.perf_counter()
                results = await asyncio.gather(*(one(i, False, repetition) for i in range(args.requests)))
                duration = time.perf_counter() - start
                good = [row for row in results if row["success"]]
                summary = {"repetition": repetition, "start_perf_counter": start, "end_perf_counter": start + duration,
                           "requests": len(results), "successes": len(good),
                           "failure_rate": 1 - len(good) / len(results), "duration_s": duration,
                           "requests_per_s": len(good) / duration,
                           "output_tokens_per_s": sum(row["output_tokens"] for row in good) / duration}
                for metric in ("latency_s", "ttft_s", "tpot_s"):
                    values = [row[metric] for row in good if row[metric] is not None]
                    summary[metric] = {"p50": percentile(values, .5), "p95": percentile(values, .95)}
                rows.append(summary)
                (args.output / "summary.json").write_text(json.dumps(rows, indent=2))
                print(json.dumps(summary), flush=True)
                if len(good) != len(results):
                    raise RuntimeError("measured requests failed; stop before increasing load")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--urls", nargs="+", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--images", type=int, choices=(1, 4), default=1)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--tokens", type=int, default=128)
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    assert args.requests > 0 and args.concurrency > 0
    assert not (args.output / "requests.jsonl").exists(), "use a new output directory; never mix runs"
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
