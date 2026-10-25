"""Local benchmark adapter using vLLM's unmodified inference engine.

Matches EPD's JSON /generate response so both use server token timestamps.
Each timestamp is in this host's time.perf_counter() domain.
"""
import argparse
import inspect
import json
import pathlib
import time
import uuid
from PIL import Image
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn
from vllm import AsyncEngineArgs, AsyncLLMEngine, SamplingParams


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", type=pathlib.Path, required=True)
    parser.add_argument("--port", type=int, default=17778)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.65)
    args = parser.parse_args()
    dataset = args.dataset.resolve()
    options = dict(
        model=args.model, dtype="float16", tensor_parallel_size=1,
        enforce_eager=True, trust_remote_code=True, seed=0,
        max_model_len=4096, max_num_seqs=8, max_num_batched_tokens=4096,
        enable_prefix_caching=False, disable_mm_preprocessor_cache=True,
        gpu_memory_utilization=args.gpu_memory_utilization,
        limit_mm_per_prompt={"image": 4},
        mm_processor_kwargs={"min_pixels": 200704, "max_pixels": 200704}
        if "Qwen2-VL" in args.model else None)
    supported = inspect.signature(AsyncEngineArgs).parameters
    # vLLM 0.6.1 has no multimodal preprocessing cache or processor-kwargs flag.
    for optional in ("disable_mm_preprocessor_cache", "mm_processor_kwargs"):
        if optional not in supported:
            options.pop(optional)
    engine_args = AsyncEngineArgs(**options)
    engine = AsyncLLMEngine.from_engine_args(engine_args)
    app = FastAPI()
    image_cache = {}

    @app.get("/health")
    async def health():
        return {"status": "ready", "model": args.model}

    @app.post("/profile/start")
    async def start_profile():
        await engine.start_profile()
        return {"profiling": True}

    @app.post("/profile/stop")
    async def stop_profile():
        await engine.stop_profile()
        return {"profiling": False}

    @app.post("/generate")
    async def generate(request: Request):
        data = await request.json()
        inputs = data.pop("input")
        data.pop("stream", None)
        paths = inputs["multi_modal_data"]["images_paths"]
        images = []
        for name in paths:
            path = pathlib.Path(name).resolve()
            if path.parent != dataset:
                raise HTTPException(400, "image must be in the experiment dataset")
            if path not in image_cache:
                with Image.open(path) as image:
                    image_cache[path] = image.convert("RGB")
            images.append(image_cache[path])
        sampling = SamplingParams(**data)
        prompt = {"prompt": inputs["prompt"], "multi_modal_data": {"image": images}}
        timestamps, previous_count, final = [], 0, None
        async for output in engine.generate(prompt, sampling, uuid.uuid4().hex):
            final = output
            token_count = len(output.outputs[0].token_ids)
            timestamps.extend([time.perf_counter()] * (token_count - previous_count))
            previous_count = token_count
        assert final is not None
        return JSONResponse({"output": final.outputs[0].text,
                             "output_token_ids": list(final.outputs[0].token_ids),
                             "processed_prompt_token_ids": list(final.prompt_token_ids),
                             "prompt_token_len": len(final.prompt_token_ids),
                             "processed_prompt_token_len": len(final.prompt_token_ids),
                             "timestamps": timestamps,
                             "timestamp_clock": "time.perf_counter on server host"})

    print(json.dumps(vars(args), default=str), flush=True)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
