"""Publish only the explicitly enumerated, scanned seals to the authorized private repo."""
import hashlib
import http.client
import json
from pathlib import Path
import sys
import time
import urllib.parse
import urllib.request
from github_api import REPO, api, token

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[1]
TAG = 'experiments-2026-10-25'
STATE = WORK / 'release-state.json'
UPLOAD_CONNECTION = http.client.HTTPSConnection


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024**2):
            digest.update(block)
    return digest.hexdigest()


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, *args):
        next_request = super().redirect_request(request, *args)
        if next_request is not None:
            if urllib.parse.urlparse(next_request.full_url).scheme != 'https':
                raise RuntimeError('refuse non-HTTPS download redirect')
            if urllib.parse.urlparse(next_request.full_url).hostname != urllib.parse.urlparse(request.full_url).hostname:
                next_request.remove_header('Authorization')
        return next_request


def download_digest(asset, output=None):
    assert asset['url'] == 'https://api.github.com/repos/' + REPO + '/releases/assets/' + str(asset['id'])
    request = urllib.request.Request(asset['url'],
        headers={'Authorization': 'Bearer ' + token(), 'Accept': 'application/octet-stream',
                 'User-Agent': 'spaceserve-epd-reproduction', 'X-GitHub-Api-Version': '2022-11-28'})
    digest, size = hashlib.sha256(), 0
    with urllib.request.build_opener(SafeRedirect()).open(request, timeout=300) as response:
        while block := response.read(1024**2):
            digest.update(block)
            size += len(block)
            if output is not None:
                output.write(block)
    return size, digest.hexdigest()


def run(action, commit=None):
    repository = api('repos/' + REPO)
    assert repository['full_name'] == REPO and repository['private']
    manifests = json.loads((WORK / 'assets-for-upload.json').read_text())
    assert all(Path(x['name']).name == x['name'] and x['bytes'] < 2*1024**3 for x in manifests)
    if action == 'create':
        assert not STATE.exists() and not (WORK / 'download-verified.json').exists(), 'refuse stale release/verification state'
        assert commit and len(commit) == 40 and all(x in '0123456789abcdef' for x in commit)
        releases = api('repos/' + REPO + '/releases')
        assert not any(x['tag_name'] == TAG for x in releases), 'never overwrite an existing release'
        refs = api('repos/' + REPO + '/git/matching-refs/tags/' + TAG)
        assert not any(x['ref'] == 'refs/tags/' + TAG for x in refs), 'never overwrite an existing tag'
        release = api('repos/' + REPO + '/releases', 'POST', {
            'tag_name': TAG, 'target_commitish': commit, 'name': 'SpaceServe / EPD 封存实验 2026-10-25',
            'body': '四批代码、可读报告和逐请求数据见main。原完整结果包及历史/诊断包按原bytes保存，校验与恢复索引见publication/ASSETS.md。历史包不替代最终选用数据。无模型权重、环境或缓存；未重新运行GPU。', 'draft': True})
        assert release['target_commitish'] == commit and release['tag_name'] == TAG and release['draft']
        for ref in api('repos/' + REPO + '/git/matching-refs/tags/' + TAG):
            if ref['ref'] == 'refs/tags/' + TAG:
                assert ref['object']['type'] == 'commit' and ref['object']['sha'] == commit
        STATE.write_text(json.dumps(release, indent=2), encoding='utf-8')
        print(json.dumps({'id': release['id'], 'tag': TAG, 'draft': True}), flush=True)
        return
    state = json.loads(STATE.read_text())
    release = api('repos/' + REPO + '/releases/' + str(state['id']))
    assert release['tag_name'] == TAG and release['id'] == state['id']
    assert release['target_commitish'] == state['target_commitish']
    if action == 'upload':
        assert release['draft'], 'assets are uploaded before publication'
        observed = []
        for item in manifests:
            path = ROOT / 'outputs' / item['name']
            assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256']
            current = api('repos/' + REPO + '/releases/' + str(release['id']) + '/assets')
            existing = [x for x in current if x['name'] == item['name']]
            if existing:
                assert len(existing) == 1 and existing[0]['size'] == item['bytes'] and existing[0].get('digest') == 'sha256:' + item['sha256'], 'existing asset differs; do not overwrite'
                asset = existing[0]
            else:
                connection = UPLOAD_CONNECTION('uploads.github.com', timeout=300)
                location = '/repos/' + REPO + '/releases/' + str(release['id']) + '/assets?name=' + urllib.parse.quote(item['name'])
                connection.putrequest('POST', location)
                for key, value in {'Authorization': 'Bearer ' + token(), 'Content-Type': 'application/octet-stream',
                                   'Content-Length': str(item['bytes']), 'User-Agent': 'spaceserve-epd-reproduction'}.items():
                    connection.putheader(key, value)
                connection.endheaders()
                sent, previous = 0, time.monotonic()
                with path.open('rb') as source:
                    while block := source.read(1024**2):
                        connection.send(block)
                        sent += len(block)
                        if time.monotonic() - previous >= 20:
                            print(json.dumps({'upload': item['name'], 'sent': sent, 'total': item['bytes']}), flush=True)
                            previous = time.monotonic()
                response = connection.getresponse()
                payload = response.read()
                assert response.status == 201, 'asset upload HTTP ' + str(response.status)
                asset = json.loads(payload)
                connection.close()
            assert asset['size'] == item['bytes'] and asset.get('digest') == 'sha256:' + item['sha256']
            observed.append({key: asset[key] for key in ['id', 'name', 'size', 'digest', 'browser_download_url']})
            (WORK / 'upload-observed.json').write_text(json.dumps(observed, indent=2), encoding='utf-8')
            print(json.dumps({'uploaded': item['name'], 'size': asset['size'], 'sha256': item['sha256']}), flush=True)
    elif action == 'verify':
        current = api('repos/' + REPO + '/releases/' + str(release['id']) + '/assets')
        assert {x['name'] for x in current} == {x['name'] for x in manifests}
        verified = {'repo': REPO, 'release_id': release['id'], 'tag': TAG, 'commit': release['target_commitish'], 'assets': []}
        for item in manifests:
            asset = next(x for x in current if x['name'] == item['name'])
            size, value = download_digest(asset)
            assert size == item['bytes'] and value == item['sha256']
            verified['assets'].append({'id': asset['id'], 'name': item['name'], 'bytes': size, 'sha256': value, 'url': asset['browser_download_url']})
            (WORK / 'download-verified.json').write_text(json.dumps(verified, indent=2), encoding='utf-8')
            print(json.dumps({'download_sha_verified': item['name'], 'bytes': size}), flush=True)
    elif action == 'publish':
        verified = json.loads((WORK / 'download-verified.json').read_text())
        assert verified['repo'] == REPO and verified['release_id'] == release['id'] and verified['tag'] == TAG and verified['commit'] == release['target_commitish']
        assert {x['name']: (x['sha256'], x['bytes']) for x in verified['assets']} == {x['name']: (x['sha256'], x['bytes']) for x in manifests}
        current = api('repos/' + REPO + '/releases/' + str(release['id']) + '/assets')
        assert {x['name']: (x['id'], x['size'], x.get('digest')) for x in current} == {x['name']: (x['id'], x['bytes'], 'sha256:' + x['sha256']) for x in verified['assets']}
        refs = api('repos/' + REPO + '/git/matching-refs/tags/' + TAG)
        for ref in refs:
            if ref['ref'] == 'refs/tags/' + TAG:
                assert ref['object']['type'] == 'commit' and ref['object']['sha'] == verified['commit']
        release = api('repos/' + REPO + '/releases/' + str(release['id']), 'PATCH', {'draft': False})
        assert not release['draft']
        STATE.write_text(json.dumps(release, indent=2), encoding='utf-8')
        print(json.dumps({'published': release['html_url'], 'id': release['id']}), flush=True)
    else:
        raise RuntimeError('unknown action')


if __name__ == '__main__':
    if not __debug__:
        raise RuntimeError('verification requires Python without -O')
    run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
