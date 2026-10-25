"""Record the actual wheel extensions linked into the fixed SpaceServe fork."""
import hashlib
import importlib.metadata
import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1]).resolve()
source = root / "src/SpaceServe/vllm"
assert importlib.metadata.version("vllm") == "0.7.2"
rows = []
for path in sorted(source.rglob("*")):
    if path.is_symlink() and path.is_file():
        target = path.resolve()
        digest = hashlib.sha256()
        with target.open("rb") as content:
            for chunk in iter(lambda: content.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
        rows.append({"source": str(path.relative_to(source)), "wheel_file": str(target),
                     "bytes": target.stat().st_size,
                     "sha256": digest.hexdigest()})
assert any(row["source"].startswith("_C.") for row in rows)
(root / "results/native-extensions-manifest.json").write_text(json.dumps(rows, indent=2))
print(json.dumps({"linked_files": len(rows), "vllm": "0.7.2"}))
