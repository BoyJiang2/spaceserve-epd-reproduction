"""Use the normal Git credential helper in memory; never log or persist credentials."""
import json
import os
import subprocess
import urllib.request
from urllib.error import HTTPError

REPO = 'BoyJiang2/spaceserve-epd-reproduction'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, *args):
        raise RuntimeError('unexpected GitHub API redirect; credentials were not forwarded')


def token():
    result = subprocess.run(['git', 'credential', 'fill'], input='protocol=https\nhost=github.com\n\n',
                            capture_output=True, text=True, check=True,
                            env=dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='never'))
    values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    return values['password']


def api(path, method='GET', data=None):
    request = urllib.request.Request('https://api.github.com/' + path.lstrip('/'),
        data=json.dumps(data).encode() if data is not None else None, method=method,
        headers={'Authorization': 'Bearer ' + token(), 'Accept': 'application/vnd.github+json',
                 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'spaceserve-epd-reproduction',
                 'Content-Type': 'application/json'})
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=120) as response:
            return json.load(response) if response.status != 204 else None
    except HTTPError as error:
        raise RuntimeError('GitHub API HTTP ' + str(error.code) + ' for ' + method + ' ' + path) from None


if __name__ == '__main__':
    result = api('repos/' + REPO)
    safe = {key: result[key] for key in ['id', 'full_name', 'private', 'default_branch', 'size', 'permissions']}
    print(json.dumps(safe))
