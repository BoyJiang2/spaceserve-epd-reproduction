"""Create a fixed COCO subset and independent image-routing checks."""
import argparse
import hashlib
import json
import pathlib
from PIL import Image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("destination", type=pathlib.Path)
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)
    sources = sorted(args.source.glob("COCO_val2014_*.jpg"))[:20]
    assert len(sources) == 20, "need 20 COCO validation images"
    images = []
    for source in sources:
        target = args.destination / source.name
        with Image.open(source) as image:
            image.convert("RGB").resize((448, 448), Image.Resampling.LANCZOS).save(target, quality=95)
        images.append({"file": source.name, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                       "sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "width": 448, "height": 448})
    for color in ("red", "green", "blue", "yellow"):
        Image.new("RGB", (448, 448), color).save(args.destination / f"routing_{color}.png")
    manifest = {"dataset": "COCO val2014, first 20 available filenames in sorted order",
                "preprocessing": "RGB, resize to 448x448 LANCZOS, JPEG quality 95",
                "prompt": "Describe the visible objects and scene in these images in detail.",
                "images": images}
    (args.destination / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
