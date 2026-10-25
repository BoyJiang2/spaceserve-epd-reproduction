"""Transfer one approved historical seal using a larger per-socket send buffer."""
import http.client
import json
import socket
import release_assets


def connection(host, port=None, **options):
    assert host == 'uploads.github.com'
    result = http.client.HTTPSConnection(host, port, **options)
    result.connect()
    result.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024**2)
    return result


if __name__ == '__main__':
    if not __debug__:
        raise RuntimeError('verification requires Python without -O')
    original_work = release_assets.WORK
    assets = json.loads((original_work / 'assets-for-upload.json').read_text())
    selected = [item for item in assets if item['name'] == 'reproduction-h20.zip']
    assert len(selected) == 1 and selected[0]['sha256'] == '3d12536a846208e3202b67650adeee2f424cc4da1bb0a6cc28c67a494941be38'
    worker = original_work / 'buffered-asset-worker'
    worker.mkdir(exist_ok=True)
    (worker / 'assets-for-upload.json').write_text(json.dumps(selected), encoding='utf-8')
    release_assets.WORK = worker
    release_assets.UPLOAD_CONNECTION = connection
    release_assets.run('upload')
