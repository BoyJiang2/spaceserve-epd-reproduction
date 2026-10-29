"""Windows TLS transport for read-only draft downloads; retain publisher guards."""
import hashlib
import json
import subprocess
import urllib.parse

import publish_space_release as publisher


def redirect_target(headers):
    statuses = [line.split()[1] for line in headers.splitlines()
                if line.startswith('HTTP/') and len(line.split()) >= 2]
    if not statuses or statuses[-1] != '302':
        raise RuntimeError('asset API final status is not 302')
    locations = [line.partition(':')[2].strip() for line in headers.splitlines()
                 if line.lower().startswith('location:')]
    if len(locations) != 1:
        raise RuntimeError('asset API did not return one download redirect')
    url = urllib.parse.urlsplit(locations[0])
    if (url.scheme != 'https' or url.hostname != 'release-assets.githubusercontent.com'
            or url.username or url.password or url.port not in (None, 443)):
        raise RuntimeError('unexpected asset download host; redirect omitted')
    return locations[0]


def download_digest(asset, output=None):
    if asset['url'] != 'https://api.github.com/repos/' + publisher.REPO + '/releases/assets/' + str(asset['id']):
        raise RuntimeError('unexpected asset API identity')
    # curl config travels only through stdin; authentication and signed URLs never
    # enter process arguments, files, logs, or the unauthenticated CDN request.
    config = '\n'.join([
        'url = ' + json.dumps(asset['url']),
        'header = "Accept: application/octet-stream"',
        'header = "X-GitHub-Api-Version: 2022-11-28"']) + '\n'
    response = subprocess.run(['curl.exe', '--disable', '--silent', '--show-error', '--proto', '=https',
        '--max-redirs', '0', '--connect-timeout', '20', '--max-time', '60',
        '--dump-header', '-', '--output', 'NUL', '--config', '-'],
        input=config.encode(), capture_output=True)
    if response.returncode:
        raise RuntimeError('asset redirect transport failed; sensitive output omitted')
    target = redirect_target(response.stdout.decode('iso-8859-1'))
    config = 'url = ' + json.dumps(target) + '\n'
    process = subprocess.Popen(['curl.exe', '--disable', '--silent', '--show-error', '--fail',
        '--proto', '=https', '--max-redirs', '0', '--connect-timeout', '20',
        '--max-time', '300', '--config', '-'], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    digest, size = hashlib.sha256(), 0
    try:
        process.stdin.write(config.encode())
        process.stdin.close()
        while block := process.stdout.read(1024**2):
            size += len(block)
            digest.update(block)
            if output is not None:
                output.write(block)
        if process.wait(timeout=15):
            raise RuntimeError('asset body transport failed; no proof granted')
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=15)
    return size, digest.hexdigest()


if __name__ == '__main__':
    from pathlib import Path
    b=Path(__file__).resolve().parent
    approval=json.loads((b/'G5-publication-approved.json').read_bytes());state=json.loads((b/'release-published-verified.json').read_bytes());items=json.loads((b/'assets-for-upload.json').read_bytes())
    assert approval['passed'] is True and approval['assets']==items and state['id']==427341677 and state['draft'] is False and state['tag']==approval['tag']=='spaceserve-qjh003-preflight-2026-10-29' and state['commit']==approval['commit']
    proof=dict(passed=False,release_id=state['id'],commit=state['commit'],transport='anonymous public asset API Accept octet-stream then HTTPS CDN; no Authorization in either request',assets=[])
    for item in items:
        actual=next(a for a in state['assets'] if a['name']==item['name']);asset=dict(id=actual['id'],url='https://api.github.com/repos/'+publisher.REPO+'/releases/assets/'+str(actual['id']))
        size,value=download_digest(asset);assert size==item['bytes'] and value==item['sha256']
        proof['assets'].append(dict(name=item['name'],bytes=size,sha256=value,public_browser_url=actual['browser_download_url']));print('anonymous public API/CDN verified',item['name'],size,flush=True)
    proof['passed']=True
    with (b/'public-api-download-verified.json').open('x',encoding='utf8') as f:json.dump(proof,f,indent=2)
