import ast
import difflib
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
path = root / "src/epdserve/epdserve/worker.py"
before = path.read_text()
(root / "tmp/worker-before-profile.py").write_text(before)
start = before.index("    def step_llm(")
end = before.index("    def unregister_kvcache_mem_handles_context(", start)
body = before[start:end]
old = "        start = time.perf_counter()\n"
new = '''        import os
        profile_dir = os.getenv("EPD_REPRO_PROFILE_DIR")
        if profile_dir and self.stage == EngineStage.DECODING and not hasattr(self, "_repro_trace_steps"):
            self._repro_trace_steps = 4
            self._repro_profiler = torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU, torch.profiler.ProfilerActivity.CUDA])
            self._repro_profiler.start()
        start = time.perf_counter()
'''
assert body.count(old) == 1
body = body.replace(old, new)
old = "        except Exception as e:\n            raise e\n"
new = old + '''        finally:
            if profile_dir and self.stage == EngineStage.DECODING and self._repro_trace_steps > 0:
                self._repro_trace_steps -= 1
                if self._repro_trace_steps == 0:
                    self._repro_profiler.stop()
                    Path(profile_dir).mkdir(parents=True, exist_ok=True)
                    self._repro_profiler.export_chrome_trace(str(Path(profile_dir) / (str(os.getpid()) + ".json")))
'''
assert body.count(old) == 1
body = body.replace(old, new)
after = before[:start] + body + before[end:]
ast.parse(after)
path.write_text(after)
(root / "results/patches/epd-diagnostic-profile.patch").write_text("".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile="a/epdserve/worker.py", tofile="b/epdserve/worker.py")))
