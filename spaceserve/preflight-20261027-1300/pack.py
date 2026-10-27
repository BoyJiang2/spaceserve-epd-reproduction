"""One-process, stored ZIP of immutable preflight evidence; no trace parsing."""
import hashlib
import gzip
import json
from pathlib import Path
import re
import time
import zipfile

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[1]
BATCH = ROOT / 'outputs/spaceserve-window-20261027-1300'
GATE_SHA = '4e4460680468007cd67a9fda493098fc32cd4805f645254e5bec18ac53bec444'
NAME = 'spaceserve-preflight-20261027-1300.zip'
DENY = {'.git', '.aws', '.codex', '.venv', 'envs', '__pycache__', 'node_modules', 'cache'}
PATTERNS = {
    'provider-token': (re.compile(rb'(?<![A-Za-z0-9_])(?:gh[pousr]_|github_pat_|hf_|sk-)[A-Za-z0-9_]{20,}'),
                       (b'ghp_', b'gho_', b'ghu_', b'ghs_', b'ghr_', b'github_pat_', b'hf_', b'sk-')),
    'private-key': (re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----'), (b'PRIVATE KEY-----',)),
    'aws-access-key': (re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'), (b'AKIA', b'ASIA')),
    'credential-url': (re.compile(rb'https?://[^\s/:@]{1,80}:[^\s/@]{6,100}@'), (b'http://', b'https://')),
    'password-literal': (re.compile(rb'(?i)(?:password|passwd|api_key|access_token)\s*[=:]\s*["\x27][^"\x27\s]{8,}["\x27]'),
                         (b'password', b'passwd', b'api_key', b'access_token')),
}


def screen(block):
    for kind, (pattern, prefixes) in PATTERNS.items():
        sample = block.lower() if kind == 'password-literal' else block
        if any(prefix in sample for prefix in prefixes) and pattern.search(block):
            raise ValueError('Credential-like content; value and path withheld')
    return block[-65536:]

def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024**2): value.update(block)
    return value.hexdigest()


def run():
    cpu_start, wall_start = time.process_time(), time.monotonic()
    decoded_bytes, scanned_gzip = 0, []
    def bounded():
        if (time.process_time()-cpu_start > 180 or time.monotonic()-wall_start > 300
                or decoded_bytes > 12*1024**3):
            raise TimeoutError('Confidentiality I/O budget exceeded; no proof granted')
    gate_path = BATCH / 'evidence/G3_MODELS_APPROVED.json'
    if sha(gate_path) != GATE_SHA: raise ValueError('Actual frozen G3 differs')
    gate = json.loads(gate_path.read_bytes())
    if (gate['passed'] is not True or gate['formal_allowed'] is not False
            or gate['new_GPU_allowed'] is not False or gate['requests']['total'] != 313):
        raise ValueError('Not the approved 313-only preflight')
    expected = {item['path']: item for item in gate['bound_files']}
    if len(expected) != 496: raise ValueError('G3 membership differs')
    expected['evidence/G3_MODELS_APPROVED.json'] = {'sha256': GATE_SHA, 'bytes': gate_path.stat().st_size}
    outputs = [WORK / name for name in (NAME, NAME+'.partial', 'source-files.json', 'assets-for-upload.json', 'package-check.json')]
    if any(path.exists() for path in outputs): raise FileExistsError('Preserve any existing package or partial state')
    rows, names = [], set()
    files = sorted(BATCH.rglob('*'))
    for path in (BATCH, *files):
        screen(path.relative_to(BATCH).as_posix().encode('utf-8'))
        if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
            raise ValueError('Refuse linked input')
    with zipfile.ZipFile(outputs[1], 'x', compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        for path in files:
            if not path.is_file(): continue
            relative = path.relative_to(BATCH).as_posix()
            if (any(part in DENY for part in path.relative_to(BATCH).parts)
                    or path.suffix.lower() in {'.safetensors', '.bin', '.pt', '.pth', '.ckpt', '.pyc', '.zip'}):
                raise ValueError('Excluded environment/cache/weight input')
            if not path.resolve().is_relative_to(BATCH.resolve()): raise ValueError('Input escaped batch')
            before, digest = path.stat(), hashlib.sha256()
            if path.suffix.lower() in {'.gz', '.so', '.jpg', '.png'} and relative not in expected:
                raise ValueError('Binary member has no exact approved path/SHA')
            member = 'outputs/spaceserve-window-20261027-1300/'+relative
            info = zipfile.ZipInfo(member, (2026, 10, 27, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o100644 << 16
            tail = b''
            with path.open('rb') as source, archive.open(info, 'w', force_zip64=True) as target:
                while block := source.read(1024**2):
                    tail = screen(tail+block); bounded()
                    digest.update(block); target.write(block)
            after, value = path.stat(), digest.hexdigest()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ValueError('Input changed during copy')
            if relative in expected and (value != expected[relative]['sha256'] or before.st_size != expected[relative]['bytes']):
                raise ValueError('Frozen input differs')
            if path.suffix.lower() == '.gz':
                tail, member_bytes = b'', 0
                with gzip.open(path, 'rb') as stream:
                    while block := stream.read(1024**2):
                        member_bytes += len(block); decoded_bytes += len(block)
                        bounded(); tail = screen(tail+block)
                if (before.st_size, before.st_mtime_ns) != (path.stat().st_size, path.stat().st_mtime_ns):
                    raise ValueError('Trace changed during confidentiality scan')
                scanned_gzip.append({'path': relative, 'sha256': value, 'decoded_bytes': member_bytes})
            names.add(relative)
            rows.append({'path': member, 'bytes': before.st_size, 'sha256': value,
                         'git_copy': path.suffix.lower() not in {'.gz', '.so'}})
    if not set(expected).issubset(names): raise ValueError('Frozen members missing')
    if len(scanned_gzip) != 10: raise ValueError('Expected exactly ten frozen compressed traces')
    if {p.relative_to(BATCH).as_posix() for p in BATCH.rglob('*') if p.is_file()} != names:
        raise ValueError('Input membership changed during copy')
    # Read stored member bytes; never inflate the nested .gz traces or analyse them.
    with zipfile.ZipFile(outputs[1]) as archive:
        members = archive.infolist()
        if len(members) != len(rows) or any(item.compress_type != zipfile.ZIP_STORED for item in members):
            raise ValueError('ZIP member count/compression differs')
        if {item.filename: item.file_size for item in members} != {item['path']: item['bytes'] for item in rows}:
            raise ValueError('ZIP directory differs')
        for row in rows:
            digest = hashlib.sha256()
            with archive.open(row['path']) as stream:
                while block := stream.read(1024**2):
                    digest.update(block); bounded()
            if digest.hexdigest() != row['sha256']:
                raise ValueError('Stored ZIP member SHA differs')
    inventory = {'scope': '313 preflight only; formal0/54', 'runtime_commit': gate['source_commit'],
        'collector_commit': gate['collector_commit'], 'G3_gate_sha256': GATE_SHA,
        'compression': 'ZIP_STORED', 'files': rows}
    with outputs[2].open('x', encoding='utf-8') as stream: json.dump(inventory, stream, indent=2)
    outputs[1].rename(outputs[0])
    assets = [{'name': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path)} for path in outputs[:3:2]]
    bounded()
    with outputs[3].open('x', encoding='utf-8') as stream: json.dump(assets, stream, indent=2)
    proof = {'passed': True, 'scope': 'file I/O only, not tests or trace analysis', 'members': len(rows),
        'bytes': sum(item['bytes'] for item in rows), 'G3_bound_members': len(expected),
        'credential_pattern_matches': 0, 'screening_patterns': list(PATTERNS),
        'screened_raw_members': len(rows), 'screened_relative_paths': True,
        'screened_gzip_members': scanned_gzip, 'decoded_bytes': decoded_bytes,
        'cpu_seconds': time.process_time()-cpu_start, 'wall_seconds': time.monotonic()-wall_start,
        'screening_note': 'Strong token/credential patterns only; no trace JSON or performance analysis',
        'assets': assets}
    with outputs[4].open('x', encoding='utf-8') as stream: json.dump(proof, stream, indent=2)
    print(json.dumps(proof), flush=True)


if __name__ == '__main__': run()
