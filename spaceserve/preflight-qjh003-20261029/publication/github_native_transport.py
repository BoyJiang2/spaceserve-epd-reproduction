"""Bounded native TLS for the exact reviewed new Space Release; no automatic retries."""
import hashlib,json,subprocess,sys,urllib.parse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'work/repository-upload'))
from github_api import REPO,token

def api(path,method='GET',data=None):
    if not path.startswith('repos/'+REPO+'/') and path!='repos/'+REPO:raise ValueError('Repository differs')
    cfg=['url = '+json.dumps('https://api.github.com/'+path),'request = '+json.dumps(method),'header = '+json.dumps('Authorization: Bearer '+token()),'header = "Accept: application/vnd.github+json"','header = "X-GitHub-Api-Version: 2022-11-28"','header = "User-Agent: spaceserve-epd-reproduction"']
    if data is not None:cfg+=['header = "Content-Type: application/json"','data-binary = '+json.dumps(json.dumps(data,ensure_ascii=True))]
    r=subprocess.run(['curl.exe','--disable','--silent','--show-error','--fail','--proto','=https','--max-redirs','0','--connect-timeout','20','--max-time','120','--config','-'],input=('\n'.join(cfg)+'\n').encode(),capture_output=True,timeout=130)
    if r.returncode:raise RuntimeError('GitHub native transport failed; sensitive response omitted; no retry')
    return json.loads(r.stdout)

def upload():
    import publish_space_release as p
    state=json.loads((p.WORK/'release-state.json').read_bytes());approval=json.loads((p.WORK/'G5-publication-approved.json').read_bytes());items=json.loads((p.WORK/'assets-for-upload.json').read_bytes())
    assert approval['passed'] is True and approval['scope']=='Space-preflight-publication' and approval['repo']==REPO and approval['tag']==p.TAG and approval['status']=='preflight_only' and approval['assets']==items
    assert len(items)==2 and {x['name'] for x in items}=={'space-http-20261029-raw.tar.gz','source-files.json'}
    repository=api('repos/'+REPO);assert repository['id']==1433331669 and repository['private'] is False
    release=api('repos/'+REPO+'/releases/'+str(state['id']));assert release['id'] not in (423520704,424838375,424952961,425359214) and release['draft'] is True and release['tag_name']==p.TAG and release['target_commitish']==approval['commit']==state['target_commitish']
    observed=[]
    for item in items:
        path=p.WORK/item['name'];assert path.stat().st_size==item['bytes'] and p.sha(path)==item['sha256']
        current=api('repos/'+REPO+'/releases/'+str(release['id'])+'/assets');existing=[a for a in current if a['name']==item['name']]
        if existing:
            assert len(existing)==1;asset=existing[0]
        else:
            url='https://uploads.github.com/repos/'+REPO+'/releases/'+str(release['id'])+'/assets?name='+urllib.parse.quote(item['name'])
            cfg='\n'.join(['url = '+json.dumps(url),'request = "POST"','header = '+json.dumps('Authorization: Bearer '+token()),'header = "Content-Type: application/octet-stream"','header = "User-Agent: spaceserve-epd-reproduction"'])+'\n'
            r=subprocess.run(['curl.exe','--disable','--silent','--show-error','--fail','--proto','=https','--max-redirs','0','--connect-timeout','20','--max-time','600','--data-binary','@'+str(path),'--config','-'],input=cfg.encode(),capture_output=True,timeout=615)
            if r.returncode:raise RuntimeError('Native asset upload failed; inspect current assets before any continuation')
            asset=json.loads(r.stdout)
        assert asset['size']==item['bytes'] and asset.get('digest')=='sha256:'+item['sha256']
        observed.append({k:asset[k] for k in ('id','name','size','digest','browser_download_url')});(p.WORK/'upload-observed.json').write_text(json.dumps(observed,indent=2),encoding='utf8');print('uploaded',item['name'],asset['size'],flush=True)

if __name__=='__main__':
    import publish_space_release as p
    p.api=api
    if sys.argv[1]=='upload':upload()
    elif sys.argv[1]=='verify':
        import verify_space_assets_curl as v
        p.download_digest=v.download_digest;p.run('verify')
    elif sys.argv[1]=='inspect':
        rows=api('repos/'+REPO+'/releases');print(json.dumps([dict(id=x['id'],tag=x['tag_name'],draft=x['draft'],commit=x['target_commitish']) for x in rows]))
    else:p.run(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else None)
