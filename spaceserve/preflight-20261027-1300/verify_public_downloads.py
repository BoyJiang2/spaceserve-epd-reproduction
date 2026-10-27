"""Read the actual public download links without repository credentials."""
import hashlib
import json
from pathlib import Path
import subprocess

WORK = Path(__file__).resolve().parent
BASE = 'https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/download/spaceserve-preflight-2026-10-27-1300/'


def run():
    output = WORK / 'public-download-verified.json'
    if output.exists(): raise FileExistsError('Preserve existing public download proof')
    state = json.loads((WORK/'release-state.json').read_bytes())
    approval = json.loads((WORK/'G5-publication-approved.json').read_bytes())
    assets = json.loads((WORK/'assets-for-upload.json').read_bytes())
    if (state['id'] != 425359214 or state['draft'] is not False
            or state['tag_name'] != 'spaceserve-preflight-2026-10-27-1300'
            or state['target_commitish'] != 'fc5ab91a440b3663a14d747fa421a4265744453b'
            or approval['passed'] is not True or approval['assets'] != assets
            or approval['repo'] != 'BoyJiang2/spaceserve-epd-reproduction'
            or approval['scope'] != 'Space-preflight-publication'
            or approval['tag'] != state['tag_name'] or approval['commit'] != state['target_commitish']
            or {item['name'] for item in assets} != {'spaceserve-preflight-20261027-1300.zip', 'source-files.json'}):
        raise ValueError('Not the approved published preflight assets')
    proof = {'passed': False, 'release_id': state['id'], 'tag': state['tag_name'],
             'commit': state['target_commitish'], 'transport': 'anonymous public browser_download_url GET',
             'G5_sha256': hashlib.sha256((WORK/'G5-publication-approved.json').read_bytes()).hexdigest(), 'assets': []}
    for asset in assets:
        url = BASE+asset['name']
        process = subprocess.Popen(['curl.exe', '--disable', '--silent', '--show-error', '--fail',
            '--location', '--proto', '=https', '--proto-redir', '=https', '--max-redirs', '3',
            '--connect-timeout', '20', '--max-time', '600', url],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        value, size = hashlib.sha256(), 0
        try:
            while block := process.stdout.read(1024**2):
                value.update(block); size += len(block)
            if process.wait(timeout=15): raise RuntimeError('Public transfer failed; no proof granted')
        finally:
            process.stdout.close()
            if process.poll() is None:
                process.terminate(); process.wait(timeout=15)
        if size != asset['bytes'] or value.hexdigest() != asset['sha256']:
            raise ValueError('Public downloaded bytes/SHA differ')
        proof['assets'].append({**asset, 'url': url})
        print(json.dumps({'public_download_verified': asset['name'], 'bytes': size}), flush=True)
    proof['passed'] = True
    with output.open('x', encoding='utf-8') as stream: json.dump(proof, stream, indent=2)


if __name__ == '__main__': run()
