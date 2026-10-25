import base64, hashlib, json, subprocess, sys
from pathlib import Path
from github_api import api, REPO
from release_assets import TAG, STATE
if not __debug__:
    raise RuntimeError('verification requires Python without -O')
root = Path(__file__).resolve().parent
checkout = root / 'checkout'
def git(*args):
    return subprocess.check_output(['git', '-C', str(checkout), *args])
head = git('rev-parse', 'HEAD').decode().strip()
repo = api('repos/' + REPO)
assert repo['full_name'] == REPO and repo['private']
ref = api('repos/' + REPO + '/git/ref/heads/main')
assert ref['object']['sha'] == head
remote = api('repos/' + REPO + '/git/trees/' + head + '?recursive=1')
assert not remote['truncated']
remote_blobs = {x['path']: x['sha'] for x in remote['tree'] if x['type'] == 'blob'}
local = {}
for line in git('ls-files', '-s').decode().splitlines():
    meta, path = line.split('\t', 1)
    local[path] = meta.split()[1]
assert remote_blobs == local
readme = api('repos/' + REPO + '/readme?ref=' + head)
assert base64.b64decode(readme['content']) == (checkout / 'README.md').read_bytes()
images = []
import re
for link in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', (checkout / 'README.md').read_text(encoding='utf-8')):
    if not link.startswith('http'):
        image = api('repos/' + REPO + '/contents/' + link + '?ref=' + head)
        assert base64.b64decode(image['content']) == (checkout / link).read_bytes()
        images.append(link)
state = json.loads(STATE.read_text())
release = api('repos/' + REPO + '/releases/' + str(state['id']))
assert not release['draft'] and release['tag_name'] == TAG
assets = api('repos/' + REPO + '/releases/' + str(state['id']) + '/assets')
manifest = json.loads((root / 'assets-for-upload.json').read_text())
assert {x['name']: (x['size'], x.get('digest'), x['browser_download_url']) for x in assets} == {x['name']: (x['bytes'], 'sha256:' + x['sha256'], x['url']) for x in manifest}
tag = api('repos/' + REPO + '/git/ref/tags/' + TAG)
assert tag['object']['type'] == 'commit' and tag['object']['sha'] == state['target_commitish']
proof = json.loads((root / 'download-verified.json').read_text())
assert proof['repo'] == REPO and proof['release_id'] == release['id'] and proof['tag'] == TAG and proof['commit'] == tag['object']['sha']
assert {x['name']: (x['bytes'], x['sha256'], x['url']) for x in proof['assets']} == {x['name']: (x['bytes'], x['sha256'], x['url']) for x in manifest}
assert {x['name']: (x['id'], x['bytes'], 'sha256:' + x['sha256'], x['url']) for x in proof['assets']} == {x['name']: (x['id'], x['size'], x.get('digest'), x['browser_download_url']) for x in assets}
assert len(proof['assets']) == len(manifest) == len(assets) == 7
subprocess.run(['git', '-C', str(checkout), 'merge-base', '--is-ancestor', tag['object']['sha'], head], check=True)
result = dict(passed=True, repository=REPO, private=True, main_commit=head, release_url=release['html_url'], release_id=release['id'], draft=False, tag_commit=tag['object']['sha'], git_blob_files=len(local), all_remote_git_blobs_match_local_index=True, readme_bytes_match=True, primary_images_verified=images, actual_download_sha_verified_assets=7, exact_asset_set_size_digest_urls=True)
(root / sys.argv[1]).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result))
