import base64
import hashlib
import json
import sys
import types

payload=sys.stdin.buffer.read(100001)
if len(payload)>100000:raise ValueError('Source payload budget exceeded')
data=json.loads(payload)
if set(data)!={'unit','tool_commit','runtime_commit','booking','modules'}:raise ValueError('Unexpected payload keys')
if data['unit'] not in ('data','env','model'):raise ValueError('Unknown asset unit')
if data['runtime_commit']!='a3f03b9dd5956db92add454f9b3afd5663f84609':raise ValueError('Unexpected runtime commit')
expected=[('migrate_code_cpu','9cf2b505f671954a08fddeae65ab52a2cdf288f0757e663e4d2ddce49698b405'),
          ('materialize_assets_cpu','8ffccf7061b2ebc8ac90543d0d60c79efaf7ff87552cef8fcf1bd6555dbd0c0c')]
if len(data['modules'])!=2:raise ValueError('Exact two source modules required')
sources=[]
for row,(name,digest) in zip(data['modules'],expected):
    source=base64.b64decode(row['base64'],validate=True)
    if row['name']!=name or row['sha256']!=digest or hashlib.sha256(source).hexdigest()!=digest:
        raise ValueError('Published source bytes differ')
    sources.append(source)
print(json.dumps({'payload_sha256':hashlib.sha256(payload).hexdigest(),'verified_modules':expected,
                  'tool_commit':data['tool_commit'],'runtime_commit':data['runtime_commit'],'unit':data['unit']}),flush=True)
helper=types.ModuleType('migrate_code_cpu')
sys.modules['migrate_code_cpu']=helper
exec(compile(sources[0],data['tool_commit']+':tools/migrate_code_cpu.py','exec'),helper.__dict__)
sys.argv=['materialize_assets_cpu.py',data['unit'],'--booking-json',json.dumps(data['booking']),
          '--runtime-commit',data['runtime_commit'],'--tool-commit',data['tool_commit']]
exec(compile(sources[1],data['tool_commit']+':tools/materialize_assets_cpu.py','exec'),{'__name__':'__main__'})
