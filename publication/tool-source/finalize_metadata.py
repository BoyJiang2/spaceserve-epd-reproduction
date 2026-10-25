import hashlib,json,shutil
from pathlib import Path
if not __debug__:
    raise RuntimeError('verification requires Python without -O')
w=Path(__file__).resolve().parent
c=w/'checkout'
remote=json.loads((w/'remote-published-check.json').read_text())
assert remote['passed'] and remote['private'] and remote['actual_download_sha_verified_assets']==7
for name in ['README.md','publication/ASSETS.md']:
    p=c/name
    s=p.read_bytes().decode('utf-8')
    old=('发布前：以下为目标地址，尚未实际上传或下载验收。真实状态见publication/publish-state.json。' if name=='README.md' else '发布前：以下为目标地址，尚未实际上传或下载验收。真实状态见publish-state.json。')
    assert old in s
    s=s.replace(old,'已发布并验收：七个完整原包均已从GitHub实际下载，大小与SHA256逐包匹配；仓库仍为private。验收记录见publication/publish-state.json。' if name=='README.md' else '已发布并验收：七个完整原包均已从GitHub实际下载，大小与SHA256逐包匹配；仓库仍为private。验收记录见[publish-state.json](publish-state.json)。')
    p.write_bytes(s.encode('utf-8'))
source=json.loads((w/'source-postcheck.json').read_text())
assert source['passed'] and source['source_files_unchanged']==2545 and source['original_archives_unchanged']==7
state=json.loads((c/'publication/publish-state.json').read_text())
state.update(phase='published_verified',remote_publication_verified=True,note='No GPU rerun; original seven archives downloaded after publication and SHA256 verified. Immutable release tag is preparation commit; main adds only publication acceptance metadata.',verified_at='2026-10-26',tag_commit=remote['tag_commit'],download_verified_assets=7,source_files_unchanged=2545,original_archives_unchanged=7,private=True)
(c/'publication/publish-state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
e=c/'publication/evidence';e.mkdir(exist_ok=True)
for name in ['remote-first-check.json','remote-published-check.json','download-verified.json','download-verified-draft.json','upload-observed.json','source-postcheck.json','parts-cancelled.json','route-recovery.json']:
    shutil.copyfile(w/name,e/name)
for pattern in ['transport-*.md','parallel-*.md','buffered-*.md','history-*.md','remote-helper-*.md']:
    for p in w.glob(pattern):shutil.copyfile(p,c/'publication/reviews'/p.name)
for name in ['release_assets.py','upload_buffered_asset.py','upload_history.py','verify_remote_final.py']:
    shutil.copyfile(w/name,c/'publication/tool-source'/name)
t=c/'publication/tool-source'
(t/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(t.iterdir()) if p.is_file() and p.name!='SHA256SUMS'),encoding='utf-8')
(c/'publication/evidence/README.md').write_text('验收在2026-10-26实际完成。download-verified-draft记录draft时下载；正式发布后URL由untagged变为固定tag，因此再次完整下载七包，download-verified记录正式资产ID、URL与实际SHA。remote-published-check核对首提交的远端树/README/PNG、固定tag、正式七包及private。最终main仅追加真实验收元数据，最终commit与复核记录见项目外置交付回执。分卷计划在原完整包成功后取消，15个本地派生卷未上传，七原包完整保留。\n',encoding='utf-8')
print('metadata prepared from actual published verification')
