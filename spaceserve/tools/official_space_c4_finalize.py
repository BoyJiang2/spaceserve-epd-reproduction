"""Reconcile a terminated diagnostic client without inventing HTTP completion."""
import json
import math
from pathlib import Path
import sys
import time

run = Path(sys.argv[1])
client_exit = int(sys.argv[2])
assert run.is_dir()
assert not (run / "client-finalization.json").exists()
references = []
incomplete = []
for index in range(4):
    intent_path = run / ("client-" + str(index) + ".intent.json")
    record_path = run / ("client-" + str(index) + ".record.json")
    valid = False
    parse_error = None
    try:
        record = json.loads(record_path.read_text())
        valid = (isinstance(record, dict) and record.get("index") == index and
                 isinstance(record.get("completed_epoch"), (int, float)) and
                 math.isfinite(record["completed_epoch"]))
    except (OSError, ValueError, TypeError) as error:
        parse_error = repr(error)
    if valid:
        references.append({"index": index, "path": record_path.name, "derived": False})
        continue
    incomplete.append(index)
    try:
        intent = json.loads(intent_path.read_text())
    except (OSError, ValueError) as error:
        intent = None
        parse_error = (parse_error or "") + "; intent: " + repr(error)
    derived_path = run / ("client-" + str(index) + ".recovery-record.json")
    derived = {"index": index, "result_state": "HTTP_OUTCOME_UNKNOWN_CLIENT_ENDED_WITHOUT_VALID_TERMINAL",
               "terminal_source": "runner_reconciliation", "client_process_exit": client_exit,
               "reconciled_epoch": time.time(), "intent": intent, "success": False,
               "metrics_complete": False, "http_code": None, "submitted_perf": None,
               "completed_perf": None, "completed_epoch": None, "client_e2e_s": None,
               "client_ttft_s": None, "server_ttft_s": None, "server_tpot_s": None,
               "raw_response_present": (run / ("client-" + str(index) + ".response.json")).exists(),
               "original_terminal_present": record_path.exists(), "original_terminal_error": parse_error}
    with derived_path.open("x") as stream:
        json.dump(derived, stream, ensure_ascii=False, indent=2)
    references.append({"index": index, "path": derived_path.name, "derived": True})
batch_valid = False
try:
    batch = json.loads((run / "batch-result.json").read_text())
    batch_valid = (len(batch["requests"]) == 4 and batch["successes"] == 4 and
                   batch["observed_peak_inflight"] == 4 and
                   all(record["success"] and record["metrics_complete"] for record in batch["requests"]))
except (OSError, ValueError, KeyError, TypeError):
    pass
summary = {"client_process_exit": client_exit, "reconciled_epoch": time.time(),
           "record_references": references, "incomplete_indices": incomplete,
           "original_batch_present": (run / "batch-result.json").exists(),
           "original_batch_valid": batch_valid,
           "measurement_accepted": client_exit == 0 and not incomplete and batch_valid}
with (run / "client-finalization.json").open("x") as stream:
    json.dump(summary, stream, ensure_ascii=False, indent=2)
print(json.dumps(summary), flush=True)
raise SystemExit(1 if client_exit == 0 and not summary["measurement_accepted"] else 0)
