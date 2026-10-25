"""Verify migrated archives and extract copies for CPU analysis on qjh000."""
import hashlib
from pathlib import Path
import tarfile
import zipfile

ROOT = Path('/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023')
ASSETS = {
    'epd-profile-a-formal.tar.gz': 'b7d40ec9cfe9bfc315ce8fe5a0665efa3438e1bbcd7d7bf124ede60f1fa34b91',
    'reproduction-h20.zip': '3d12536a846208e3202b67650adeee2f424cc4da1bb0a6cc28c67a494941be38',
}


def digest(path):
    sha = hashlib.sha256()
    with path.open('rb') as stream:
        while data := stream.read(8 * 1024**2):
            sha.update(data)
    return sha.hexdigest()


def main():
    analysis = ROOT / 'analysis'
    analysis.mkdir(exist_ok=True)
    for name, expected in ASSETS.items():
        path = ROOT / 'tmp' / name
        if digest(path) != expected:
            raise RuntimeError('archive SHA differs: ' + name)
    target = analysis / 'epd-profile-a'
    target.mkdir(exist_ok=True)
    with tarfile.open(ROOT / 'tmp/epd-profile-a-formal.tar.gz') as archive:
        for item in archive.getmembers():
            if not (target / item.name).resolve().is_relative_to(target) or not (item.isfile() or item.isdir()):
                raise RuntimeError('unexpected formal archive member: ' + item.name)
        archive.extractall(target)
    archive_path = ROOT / 'tmp/reproduction-h20.zip'
    with zipfile.ZipFile(archive_path) as archive:
        for item in archive.infolist():
            if not (analysis / item.filename).resolve().is_relative_to(analysis):
                raise RuntimeError('unsafe frozen member')
        if archive.testzip() is not None:
            raise RuntimeError('frozen archive CRC failed')
        archive.extractall(analysis)
    linked = analysis / 'reproduction-h20.zip'
    if not linked.exists():
        linked.symlink_to(archive_path)
    elif linked.resolve() != archive_path:
        raise RuntimeError('analysis archive link differs')
    print('SHA/CRC verified; qjh003 measurement copies staged on qjh000', flush=True)


if __name__ == '__main__':
    main()
