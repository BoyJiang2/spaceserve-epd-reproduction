import argparse
import json
import pathlib


parser = argparse.ArgumentParser()
parser.add_argument("annotations", type=pathlib.Path)
parser.add_argument("dataset", type=pathlib.Path)
args = parser.parse_args()
manifest = json.loads((args.dataset / "manifest.json").read_text())
annotations = json.loads(args.annotations.read_text())
by_id = {}
for item in annotations["annotations"]:
    by_id.setdefault(item["image_id"], []).append(item["caption"])
captions = {item["file"]: by_id[int(item["file"].split("_")[-1].split(".")[0])] for item in manifest["images"]}
(args.dataset / "captions.json").write_text(json.dumps(captions, indent=2))
for name, values in captions.items():
    print(name, values[0])
