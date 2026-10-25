"""Download a pinned public Hugging Face snapshot without using the home cache."""
import argparse
import concurrent.futures
import hashlib
import json
import pathlib
import subprocess
import time


def fetch_json(url):
    return json.loads(subprocess.check_output([
        "curl", "--fail", "--location", "--silent", "--show-error",
        "--connect-timeout", "15", "--max-time", "90", url]))


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repo")
    parser.add_argument("destination", type=pathlib.Path)
    parser.add_argument("--endpoint", default="https://hf-mirror.com")
    parser.add_argument("--modelscope", action="store_true")
    parser.add_argument("--manifest", type=pathlib.Path)
    args = parser.parse_args()
    recorded = json.loads(args.manifest.read_text()) if args.manifest else None
    if recorded:
        assert recorded["repo"].lower() == args.repo.lower()
        args.endpoint = recorded["endpoint"]
        args.modelscope = "modelscope.cn" in args.endpoint
        revision = recorded["revision"]
        files = {item["name"]: item["source"] for item in recorded["files"]}
    elif args.modelscope:
        args.endpoint = "https://modelscope.cn"
        info = fetch_json(f"{args.endpoint}/api/v1/models/{args.repo}/repo/files?Revision=master&Recursive=true")
        files = {item["Path"]: item for item in info["Data"]["Files"] if item["Type"] == "blob"}
        revision = "per-file revisions recorded below"
    else:
        info = fetch_json(f"{args.endpoint}/api/models/{args.repo}")
        revision = info["sha"]
        files = {item["rfilename"]: item for item in info["siblings"]}
    args.destination.mkdir(parents=True, exist_ok=True)
    names = [name for name in files
             if name.endswith((".json", ".safetensors", ".py", ".txt", ".model", ".tiktoken"))
             and not name.startswith(("onnx/", "openvino/"))]

    def download(name):
        target = args.destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_file():
            if recorded:
                expected = next(item for item in recorded["files"] if item["name"] == name)
                assert target.stat().st_size == expected["bytes"] and sha256(target) == expected["sha256"], f"existing file mismatch: {name}"
            return name
        temporary = target.with_name(target.name + ".partial")
        for attempt in range(4):
            try:
                file_revision = files[name]["Revision"] if args.modelscope else revision
                url = f"{args.endpoint}/{('models/' if args.modelscope else '')}{args.repo}/resolve/{file_revision}/{name}"
                subprocess.run(["curl", "--fail", "--location", "--silent", "--show-error",
                                "--connect-timeout", "15", "--max-time", "1800",
                                "--output", str(temporary), url], check=True)
                temporary.replace(target)
                if args.modelscope:
                    assert target.stat().st_size == files[name]["Size"], f"size mismatch: {name}"
                    assert sha256(target) == files[name]["Sha256"], f"hash mismatch: {name}"
                print(json.dumps({"file": name, "bytes": target.stat().st_size,
                                  "sha256": sha256(target)}), flush=True)
                return name
            except Exception as exc:
                print(f"retry {attempt + 1}: {name}: {exc}", flush=True)
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(download, names))
    manifest = {"repo": args.repo, "revision": revision, "endpoint": args.endpoint,
                "files": [{"name": name, "source": files[name], "bytes": (args.destination / name).stat().st_size,
                           "sha256": sha256(args.destination / name)}
                          for name in names]}
    (args.destination / "download_manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
