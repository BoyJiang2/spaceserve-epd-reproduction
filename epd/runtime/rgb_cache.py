"""Describe the actual RGB buffers used by both benchmark adapters."""
import hashlib
import json
import os
import pathlib


def dataset_paths(manifest_path):
    manifest_path = pathlib.Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text())
    paths = [(manifest_path.parent / item['file']).resolve() for item in manifest['images']]
    assert len(paths) == 20 and len({path.name for path in paths}) == 20
    assert all(path.parent == manifest_path.parent for path in paths)
    return paths


def cache_snapshot(manifest_path, images_by_name):
    images = []
    for path in dataset_paths(manifest_path):
        image = images_by_name[path.name]
        assert image.mode == 'RGB' and image.size == (448, 448)
        images.append({'file': path.name, 'mode': image.mode, 'size': list(image.size),
                       'rgb_sha256': hashlib.sha256(image.tobytes()).hexdigest()})
    return {'pid': os.getpid(), 'manifest_sha256': hashlib.sha256(pathlib.Path(manifest_path).read_bytes()).hexdigest(),
            'images': images}
