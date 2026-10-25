"""Issue local observation-control calls; no inference or extra model work."""
import json
import sys
import urllib.request

operation, *urls = sys.argv[1:]
results = []
for url in urls:
    request = urllib.request.Request(url + '/repro/observe', data=json.dumps({'operation': operation}).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=180 if operation == 'stop' else 30) as response:
        results.append(json.load(response))
assert results
if operation != 'status':
    assert all(row['enabled'] and row['capturing'] == (operation == 'start') for row in results)
print(json.dumps(results))
