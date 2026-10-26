"""Verify the approved outer digest, inner data manifest and every bound payload."""
import hashlib
from pathlib import Path


def verify(root):
    outer = root / 'points-manifest.sha256'
    if (root / 'G4_POINTS_APPROVED').read_bytes() != outer.read_bytes():
        raise RuntimeError('G4 approval does not match outer manifest')
    expected, filename = outer.read_text().strip().split('  ', 1)
    inner = root / 'points.sha256'
    if Path(filename).resolve() != inner.resolve() or hashlib.sha256(inner.read_bytes()).hexdigest() != expected:
        raise RuntimeError('inner points manifest differs from G4-approved digest')
    for line in inner.read_text().splitlines():
        expected, filename = line.split('  ', 1)
        path = Path(filename).resolve()
        if not path.is_relative_to((root / 'points').resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError('point payload differs from approved manifest: ' + str(path))
    return {'passed': True}


if __name__ == '__main__':
    import json
    import sys
    print(json.dumps(verify(Path(sys.argv[1]).resolve())))
