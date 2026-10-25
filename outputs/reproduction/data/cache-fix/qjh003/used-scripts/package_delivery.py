"""Create a checksum manifest and verified ZIP of the finished deliverables."""
import argparse
import hashlib
import pathlib
import zipfile


parser = argparse.ArgumentParser()
parser.add_argument("root", type=pathlib.Path)
parser.add_argument("archive", type=pathlib.Path)
args = parser.parse_args()
root, archive = args.root.resolve(), args.archive.resolve()
assert not archive.is_relative_to(root), "archive must be outside the delivery directory"
assert (root / "report/delivery-audit.json").exists()
files = [path for path in sorted(root.rglob("*")) if path.is_file()
         and "__pycache__" not in path.parts and path.name != "SHA256SUMS"]
checksums = []
for path in files:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    checksums.append(f"{digest.hexdigest()}  {path.relative_to(root).as_posix()}")
manifest = root / "SHA256SUMS"
manifest.write_text("\n".join(checksums) + "\n", encoding="utf-8")
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
    for path in files + [manifest]:
        bundle.write(path, root.name + "/" + path.relative_to(root).as_posix())
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
print(f"Verified {len(files)} files; ZIP {archive.stat().st_size / 2**20:.1f} MiB: {archive}")
