"""Run one frozen sixty-request session under the original full selected Claim."""
import argparse
import asyncio
import json
from pathlib import Path

from fixed_unit import run_client
from selected_unit import session_batches


def load_session(execution, runtime_file, output, name):
    root = Path.cwd().resolve()
    runtime_root = root / 'runtime'
    paths = [Path(value) for value in (execution, runtime_file, output)]
    if any(path.is_symlink() or not path.resolve().is_relative_to(runtime_root) for path in paths):
        raise ValueError('Selected client artifacts must stay inside this runtime root')
    execution, runtime_file, output = [path.resolve(strict=True) for path in paths]
    runtime = json.loads(runtime_file.read_bytes())
    unit = (runtime_root / runtime['run_id']).resolve()
    if (not unit.is_relative_to(runtime_root) or output != unit / name
            or execution != unit / 'execution.json' or runtime_file != output / 'client-runtime.json'):
        raise ValueError('Selected session argv/output/RUNID differs')
    spec = json.loads(execution.read_bytes())
    session_batches(spec, name)
    return spec, {**runtime, 'selected_session': name}, output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution', type=Path, required=True)
    parser.add_argument('--unit-runtime', type=Path, required=True)
    parser.add_argument('--unit-output', type=Path, required=True)
    parser.add_argument('--session', choices=('cold', 'restart'), required=True)
    args = parser.parse_args()
    spec, runtime, output = load_session(args.execution, args.unit_runtime, args.unit_output, args.session)
    asyncio.run(run_client(spec, runtime, output))


if __name__ == '__main__':
    main()
