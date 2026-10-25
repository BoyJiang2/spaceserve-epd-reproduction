"""Prepare an exact-byte, traceable publication checkout; never mutate sealed inputs."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'work/repository-upload'
DEST = WORK / 'checkout'
TAG = 'experiments-2026-10-25'
URL = 'https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/download/' + TAG + '/'
BATCHES = {
    'qjh000-migration': ('spaceserve-7b-h20.zip', 'qjh000-migration/'),
    'epd-profile-a': ('epd-profile-a.zip', ''),
    'reproduction': ('reproduction-h20.zip', 'reproduction/'),
    'epd-followup': ('epd-followup.zip', 'epd-followup/'),
}
SEALS = {
    'spaceserve-7b-h20.zip': '27101c16596d1db7e4d3f08eaf86b0456264fa370876ee813cbaace251c43eee',
    'epd-profile-a.zip': 'f7a35baf1c7e0e13ea1b1df65d4436efff199c5b21c876198289fbbfb2a1c094',
    'reproduction-h20.zip': '3d12536a846208e3202b67650adeee2f424cc4da1bb0a6cc28c67a494941be38',
    'epd-followup.zip': 'd155537944ea9095f2b1eecbd3780f57a611100aa9701b5e5617f4137d38a3f9',
    'reproduction.zip': '4ca04873975832309377feaea281b71b214b9badfbae488be80eda6a43474c7d',
    'reproduction-review-pending.zip': 'a661a300df154bcd0767c2dfd9a111e082e9d3f5b27b48047e4a60bfb7e4bba4',
    'reproduction-peer-diagnostic.zip': 'b4b950ce36918b2a46f536f7725861cf592aa3665b0d43bc77a045909e606c25',
}
PATTERNS = {
    'provider-token': re.compile(rb'(?<![A-Za-z0-9_])(?:gh[pousr]_|github_pat_|hf_)[A-Za-z0-9_]{20,}'),
    'private-key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----'),
    'aws-access-key': re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'credential-url': re.compile(rb'https?://[^\s/:@]{1,80}:[^\s/@]{6,100}@'),
    'password-literal': re.compile(rb'(?i)(?:password|passwd|api_key|access_token)\s*[=:]\s*["\x27][^"\x27\s]{8,}["\x27]'),
}
SCAN = {'streams': 0, 'bytes': 0, 'findings': []}
PREFIXES = {
    'provider-token': (b'ghp_', b'gho_', b'ghu_', b'ghs_', b'ghr_', b'github_pat_', b'hf_'),
    'private-key': (b'PRIVATE KEY-----',),
    'aws-access-key': (b'AKIA', b'ASIA'),
    'credential-url': (b'http://', b'https://'),
    'password-literal': (b'password', b'passwd', b'api_key', b'access_token'),
}


def matches(chunk):
    for kind, pattern in PATTERNS.items():
        sample = chunk.lower() if kind == 'password-literal' else chunk
        if any(prefix in sample for prefix in PREFIXES[kind]) and pattern.search(chunk):
            yield kind


def check_stream(stream, label):
    digest = hashlib.sha256()
    tail = b''
    while block := stream.read(1024**2):
        digest.update(block)
        SCAN['bytes'] += len(block)
        for kind in matches(tail + block):
            SCAN['findings'].append({'file': label, 'kind': kind})
        tail = block[-512:]
    SCAN['streams'] += 1
    return digest.hexdigest()


def sha(path):
    with path.open('rb') as stream:
        digest = hashlib.sha256()
        while block := stream.read(1024**2):
            digest.update(block)
        return digest.hexdigest()


def write(relative, text):
    target = DEST / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8', newline='\n')


def json_file(relative, value):
    write(relative, json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def verify_checkout():
    count = 0
    for path in DEST.rglob('*'):
        if path.is_file() and '.git' not in path.relative_to(DEST).parts:
            assert not path.is_symlink() and path.resolve().is_relative_to(DEST.resolve())
            assert path.stat().st_size < 100 * 1024**2
            assert path.suffix.lower() not in {'.safetensors', '.bin', '.whl', '.pem', '.key', '.pyc'}
            with path.open('rb') as stream:
                check_stream(stream, path.relative_to(DEST).as_posix())
            count += 1
    assert not SCAN['findings'], json.dumps(SCAN['findings'])
    return count


def is_release(path):
    return (path.stat().st_size >= 16 * 1024**2
            or path.suffix.lower() in {'.zip', '.gz', '.nsys-rep', '.sqlite', '.so', '.tgz'})


def run():
    assert DEST.is_dir() and (DEST / '.git').is_dir()
    assert not (DEST / 'publication/source-files.json').exists(), 'refuse a second preparation over the candidate'
    records, assets = [], []
    assert all(sha(ROOT / 'outputs' / name) == value for name, value in SEALS.items()), 'original seal SHA differs'
    for name, (archive_name, prefix) in BATCHES.items():
        folder = ROOT / 'outputs' / name
        with zipfile.ZipFile(ROOT / 'outputs' / archive_name) as archive:
            names = archive.namelist()
            assert len(names) == len(set(names)) and all(not x.is_dir() for x in archive.infolist())
            files = sorted(p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
            expected = {prefix + p.relative_to(folder).as_posix() for p in files}
            assert set(names) == expected, name
            for path in files:
                assert not path.is_symlink()
                assert path.suffix.lower() not in {'.safetensors', '.bin', '.whl', '.pem', '.key'}
                relative = path.relative_to(ROOT).as_posix()
                member = prefix + path.relative_to(folder).as_posix()
                with path.open('rb') as stream:
                    value = check_stream(stream, relative)
                with archive.open(member) as stream:
                    assert check_stream(stream, archive_name + '::' + member) == value
                if path.suffix == '.gz':
                    with gzip.open(path, 'rb') as stream:
                        check_stream(stream, relative + '::gunzip')
                placement = 'release' if is_release(path) else 'git'
                records.append({'path': relative, 'bytes': path.stat().st_size, 'sha256': value,
                                'placement': placement, 'asset': archive_name, 'member': member})
                if placement == 'git':
                    target = DEST / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, target)
        print('verified/copied ' + name, flush=True)
    for path in [ROOT / 'outputs' / name for name in sorted(SEALS)]:
        # Seven existing final/historical seals; never include work candidates.
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            assert len(names) == len(set(names))
            if path.name not in {x[0] for x in BATCHES.values()}:
                for item in archive.infolist():
                    if not item.is_dir():
                        with archive.open(item) as stream:
                            check_stream(stream, path.name + '::' + item.filename)
                        if item.filename.endswith('.gz'):
                            with archive.open(item) as stream, gzip.GzipFile(fileobj=stream) as decoded:
                                check_stream(decoded, path.name + '::' + item.filename + '::gunzip')
        assert path.stat().st_size < 2 * 1024**3
        assets.append({'name': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path), 'url': URL + path.name,
                       'purpose': 'current sealed batch' if path.name in {x[0] for x in BATCHES.values()} else 'historical/diagnostic;not a replacement for final selected data'})
    assert not SCAN['findings'], json.dumps(SCAN['findings'])  # Never print matching secret values.
    for path in (ROOT / 'outputs').iterdir():
        if path.is_file() and path.suffix in {'.json', '.sha256', '.md'} and path.name != 'qjh003-goal.md':
            target = DEST / 'outputs' / path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    json_file('publication/source-files.json', records)
    json_file('publication/assets.json', assets)
    json_file('publication/security-scan.json', {**SCAN, 'passed': True,
        'scope': 'all four source payloads and canonical ZIP members;gunzipped trace/tar streams;all other historical ZIP members;no secret values logged'})
    write('publication/ASSETS.sha256', ''.join(x['sha256'] + '  ' + x['name'] + '\n' for x in assets))
    write('.gitattributes', '* -text\n')
    write('.gitignore', '.env\n.env.*\n*.pem\n*.key\n__pycache__/\n*.pyc\n.venv/\nenvs/\nnode_modules/\n.cache/\nrelease-downloads/\nrestore/\n*.safetensors\n*.bin\n*.whl\n*.nsys-rep\n*.sqlite\n*.pt.trace.json.gz\n*.zip\n')
    lookup = {x['path']: x for x in records}
    link_records = []
    def fix(match, source, target):
        label, raw = match.group(1), match.group(2)
        link = raw.strip('<>')
        if re.match(r'^(https?://|mailto:|#)', link):
            return match.group(0)
        destination = Path(link.split('#', 1)[0])
        if not destination.is_absolute():
            destination = source.parent / destination
        try:
            relative = destination.resolve().relative_to(ROOT.resolve()).as_posix()
        except ValueError:
            relative = ''
        if relative in lookup:
            record = lookup[relative]
            if record['placement'] == 'release':
                link_records.append({'source': source.relative_to(ROOT).as_posix(), 'original': raw, 'asset': record['asset'], 'member': record['member']})
                return label + '(' + URL + record['asset'] + ')（完整包内：' + record['member'] + '）'
            resolved = DEST / ('docs/reading/' + relative if relative.endswith('.md') else relative)
            return label + '(' + Path(os.path.relpath(resolved, target.parent)).as_posix() + (('#' + link.split('#', 1)[1]) if '#' in link else '') + ')'
        if relative and (DEST / relative).is_file():
            return label + '(' + Path(os.path.relpath(DEST / relative, target.parent)).as_posix() + ')'
        link_records.append({'source': source.relative_to(ROOT).as_posix(), 'original': raw, 'reason': 'historical local reference;not present in selected four batches'})
        return label.lstrip('!').replace('[', '').replace(']', '') + '（历史本地引用：' + raw + '）'
    for record in records:
        if record['path'].endswith('.md'):
            source = ROOT / record['path']
            target = DEST / 'docs/reading' / record['path']
            original = Path(os.path.relpath(DEST / record['path'], target.parent)).as_posix()
            header = '> GitHub阅读副本：仅修正链接；[封存原文](' + original + ') SHA256 ' + record['sha256'] + '。原数字及解释不变。\n\n'
            content = re.sub(r'(!?\[[^\]\n]*\])\(([^)\n]+)\)', lambda match: fix(match, source, target), source.read_text(encoding='utf-8-sig'))
            write(target.relative_to(DEST), header + content)
    json_file('publication/reading-link-transforms.json', link_records)
    write('AGENTS.md', '# 仓库执行规则\n\n本仓库为已完成实验的发布副本。outputs中的封存原文/数据不得改写；阅读链接修正仅在docs/reading。禁止提交权重、环境、缓存或凭据，禁止自动重跑GPU。沿用[项目完整指令](docs/publication/project-instructions-at-upload.md)的独立G1–G5流程，Claude限额时独立subagent只读接替。发布变更与真实验收记入publication/，不得将候选URL称为已验收。\n')
    target = DEST / 'docs/publication/project-instructions-at-upload.md'
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile('D:/Documents/codex/AGENTS.md', target)
    verify_checkout()
    json_file('publication/security-scan.json', {**SCAN, 'passed': True,
        'scope': 'all source/ZIP/gunzipped streams plus every final checkout file excluding .git;recheck required after later editorial/review additions'})
    (WORK / 'assets-for-upload.json').write_text(json.dumps(assets, indent=2), encoding='utf-8')
    print(json.dumps({'source_files': len(records), 'git_source_files': sum(x['placement']=='git' for x in records), 'release_source_files': sum(x['placement']=='release' for x in records), 'assets': len(assets), 'scan_bytes': SCAN['bytes'], 'passed': True}), flush=True)


if __name__ == '__main__':
    if not __debug__:
        raise RuntimeError('verification requires Python without -O')
    run()
