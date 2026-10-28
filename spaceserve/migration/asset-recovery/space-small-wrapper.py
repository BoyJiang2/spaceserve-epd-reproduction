import base64
import hashlib
import io
import json
import sys
import types

raw=sys.stdin.buffer.read(8*1024**2+1)
if len(raw)>8*1024**2:raise ValueError('8MiB payload budget exceeded')
data=json.loads(raw)
if set(data)!={'tool_commit','runtime_commit','booking','files','modules'}:raise ValueError('Unexpected payload keys')
expected=[('migrate_code_cpu','9cf2b505f671954a08fddeae65ab52a2cdf288f0757e663e4d2ddce49698b405'),
          ('restore_space_small_cpu','25f4756eeb8b9f547503c98ff719e8974036de5e8bf812892a84653d26d83a7f')]
modules=data.pop('modules')
if len(modules)!=2:raise ValueError('Exact two modules required')
sources=[]
for row,(name,digest) in zip(modules,expected):
    source=base64.b64decode(row['base64'],validate=True)
    if row['name']!=name or row['sha256']!=digest or hashlib.sha256(source).hexdigest()!=digest:
        raise ValueError('Published source bytes differ')
    sources.append(source)
body=json.dumps(data).encode()
print(json.dumps({'wire_payload_sha256':hashlib.sha256(raw).hexdigest(),
                  'business_payload_sha256':hashlib.sha256(body).hexdigest(),
                  'verified_modules':expected,'tool_commit':data['tool_commit']}),flush=True)
helper=types.ModuleType('migrate_code_cpu');sys.modules['migrate_code_cpu']=helper
exec(compile(sources[0],data['tool_commit']+':tools/migrate_code_cpu.py','exec'),helper.__dict__)
sys.stdin=io.TextIOWrapper(io.BytesIO(body),encoding='utf8')
exec(compile(sources[1],data['tool_commit']+':tools/restore_space_small_cpu.py','exec'),{'__name__':'__main__'})
