import base64
import hashlib
import json
import sys
import types

payload=sys.stdin.buffer.read(100001)
if len(payload)>100000:raise ValueError('Source payload budget exceeded')
data=json.loads(payload)
if set(data)!={'name','tool_commit','runtime_commit','booking','modules'}:raise ValueError('Unexpected payload keys')
if data['name'] not in ('model-00001-of-00005.safetensors', 'model-00002-of-00005.safetensors', 'model-00003-of-00005.safetensors', 'model-00004-of-00005.safetensors', 'model-00005-of-00005.safetensors', 'model.safetensors.index.json', 'preprocessor_config.json', 'tokenizer.json', 'tokenizer_config.json', 'vocab.json'):raise ValueError('Only the ten missing model files are allowed')
if data['runtime_commit']!='a3f03b9dd5956db92add454f9b3afd5663f84609':raise ValueError('Unexpected runtime commit')
expected=[('migrate_code_cpu','9cf2b505f671954a08fddeae65ab52a2cdf288f0757e663e4d2ddce49698b405'),
          ('fetch_space_model_remote_cpu','4f511ceda75bcaf1e73277c7bfac09c514cbe2b01689b03443eaa282a822068b')]
if len(data['modules'])!=2:raise ValueError('Exact two source modules required')
sources=[]
for row,(name,digest) in zip(data['modules'],expected):
    source=base64.b64decode(row['base64'],validate=True)
    if row['name']!=name or row['sha256']!=digest or hashlib.sha256(source).hexdigest()!=digest:
        raise ValueError('Published source bytes differ')
    sources.append(source)
print(json.dumps({'payload_sha256':hashlib.sha256(payload).hexdigest(),'verified_modules':expected,
                  'tool_commit':data['tool_commit'],'runtime_commit':data['runtime_commit'],'name':data['name']}),flush=True)
helper=types.ModuleType('migrate_code_cpu')
sys.modules['migrate_code_cpu']=helper
exec(compile(sources[0],data['tool_commit']+':tools/migrate_code_cpu.py','exec'),helper.__dict__)
sys.argv=['fetch_space_model_remote_cpu.py','--name',data['name'],'--booking-json',json.dumps(data['booking']),
          '--tool-commit',data['tool_commit']]
exec(compile(sources[1],data['tool_commit']+':tools/fetch_space_model_remote_cpu.py','exec'),{'__name__':'__main__'})
