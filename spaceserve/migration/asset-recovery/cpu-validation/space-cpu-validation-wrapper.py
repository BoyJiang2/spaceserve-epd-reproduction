import base64
import hashlib
import io
import json
import sys
import types

raw=sys.stdin.buffer.read(100001)
if len(raw)>100000:raise ValueError('100000-byte CPU recipe budget exceeded')
data=json.loads(raw)
if set(data)!={'phase','tool_commit','runtime_commit','booking','source_config_base64','modules'}:raise ValueError('Unexpected payload fields')
if data['phase'] not in ('prepare','cpu'):raise ValueError('Unknown environment action')
if data['runtime_commit']!='a3f03b9dd5956db92add454f9b3afd5663f84609':raise ValueError('Unexpected frozen runtime')
expected=[('migrate_code_cpu','9cf2b505f671954a08fddeae65ab52a2cdf288f0757e663e4d2ddce49698b405'),
          ('validate_space_cpu','fd4ccfd1a7c4ff689d7eb39eee83067abee52359e29717d5373166694329631c')]
modules=data.pop('modules')
if len(modules)!=2:raise ValueError('Exact two approved modules required')
sources=[]
for row,(name,digest) in zip(modules,expected):
    source=base64.b64decode(row['base64'],validate=True)
    if row['name']!=name or row['sha256']!=digest or hashlib.sha256(source).hexdigest()!=digest:
        raise ValueError('Published source bytes differ')
    sources.append(source)
body=json.dumps(data).encode()
print(json.dumps({'wire_payload_sha256':hashlib.sha256(raw).hexdigest(),
                  'business_payload_sha256':hashlib.sha256(body).hexdigest(),
                  'verified_modules':expected,'tool_commit':data['tool_commit'],'phase':data['phase']}),flush=True)
helper=types.ModuleType('migrate_code_cpu');sys.modules['migrate_code_cpu']=helper
exec(compile(sources[0],data['tool_commit']+':tools/migrate_code_cpu.py','exec'),helper.__dict__)
sys.stdin=io.TextIOWrapper(io.BytesIO(body),encoding='utf8')
exec(compile(sources[1],data['tool_commit']+':tools/validate_space_cpu.py','exec'),{'__name__':'__main__'})
