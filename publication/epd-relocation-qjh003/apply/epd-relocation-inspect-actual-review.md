# EPD startup inspect — independent actual-result review

Reviewer /root/epd_pd_followup；reviewed_at_utc 2026-10-29T02:06:38Z（clock tool）。仅本地原件/源码/SHA读取和本审查输出；未重跑61文件inspect，未测试/SSH/API/网络/GPU。

结论：APPROVE / BLOCKING0，仅限实际静态startup清单。没有发现这份清单中需要绕过的未知startup项；这不证明整个环境导入/运行安全可用，也不授权执行任何.pth/activate/import或后续apply。

## 实际证据链

command.commit=ddac90e689d094aff960cbe28cb31e0b74744e4d；解码实际SSH命令内base64字节（未exec）得到源SHA8ca5723e26e0083c703d46587a57416ad7e26a7d1386f34c34fd357aa1fcf28c。input SHA与command.payload_sha256同为b66fa81df4162dbf4e0e6eba2ea7c9038816b6d1f9ff5f70629aa53aa5870783。epd-relocation-remote-source-verified.json记录exact同commit/source/3726B的GitHub connector先验观测1793238623670，早于实际工具观测1793238731017约107347ms；本轮未独立重访API，但本地原件不再把后验当事前。

实际票仍是本人qjh003 CPU bk-20261029T0057-e2efd603/09–10，原始observed1793238707487，工具启动时年龄23530ms，至票末尚468983ms，60+30及09:58边界可容纳。stdout phase=inspect、hostqjh003/UID2147/boot65f，exit0、stderr空、工具段0.013833621982485056s；不是SSH/API整段耗时。受审源码强制CPU50/nice10/native-I-S-B及路径守卫；未将该事实外推到后续未预约CPU执行。

## 61文件/3链接与startup边界

61=pyvenv1 + distutils-precedence.pth1 + console51 + activate变体8。所有10份包含text的原件均独立以UTF8重编码重算SHA相等（含activate.bat的CRLF），不是summary重建；console仅首行+原文件bytes/SHA，未声称已有完整console正文。

- pyvenv.cfg113B/SHAe7bd1cc472cb682fadda94923b8b92717a92829af4703aba9841d2b619a25c82，home=/usr/bin、version_info3.10.12、include-system-site-packages=false。
- 唯一直接site .pth为distutils-precedence.pth，151B/SHA2638ce9e2500e572a5e0de7faed6661eb569d1b696fcba07b0dd223da5f5d224。实际文本为SETUPTOOLS_USE_DISTUTILS条件下import _distutils_hack/add_shim，未含旧实验根。该同hash也已出现在checkout/tools/validate_space_cpu.py:27的已固定标准.pth清单中；仅以相同文本/SHA作来源核对，不表示已执行/审计其import模块全部代码。
- 当前工具覆盖的site-packages顶层没有输出sitecustomize.py/usercustomize.py；依受审源码存在才读的分支，只说明这两个固定位置当时没有该文件，不声称全系统不存在其他startup。未来采用任何不同Python/site/PYTHONPATH模式仍需其自身准入。
- 8份activate完整文本中activate、activate.bat、activate.csh、activate.fish、activate.nu各1个旧env绝对根引用；activate.ps1、activate.xsh、activate_this.py没有该旧绝对根，采用相对/动态路径。不能为“全改”而重写无旧根的三个文件。activate_this.py本身有site.addsitedir逻辑，是原文取证，绝不在本阶段执行。未观察需修改.pth/pyvenv的证据。
- 51 console首行仍指旧env解释器，需要后续逐文件beforeSHA约束的精确首行替换。3 Python链接为python→/usr/bin/python3，python3/python3.10→python，均resolve=/usr/bin/python3.10，只有链接元数据取证，不能说启动了目标env解释器。

可将51 console及5个含旧根activate作为下一最小allowlist候选来源；每项应按这次真实beforeSHA再核、仅必要旧env绝对路径替换，完整原件备份。不同角色/平台的activate是否必需应按计划最少原则选择，不改三个无旧根文件、pyvenv或.pth。flatIPC/RUNPATH仍依据上次readelf静态证据另审新副本，不由这次startup清单自动批准修改。未知SHA/新startup/额外root引用在apply前必须停，不能继承这次exit0。

## 原件SHA256

|文件|SHA256|
|---|---|
|command.json|25ef28c3ebf3e256dc1915344c02e9b2ea9e27fb6439b0c1dad817c55b27326d|
|input.json|b66fa81df4162dbf4e0e6eba2ea7c9038816b6d1f9ff5f70629aa53aa5870783|
|stdout.json|db8ffa0366f33bc67c09feb470e6337bae26a6cb45b5b31a909605d404ed6e56|
|stderr.log|e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855|
|exit.json|a57a61042c27bcfff553b46d303185dc0db5c1a744450ecb178d86f3c3c4d4c5|

GATE_RESULT: {"gate":"actual_static_startup_inventory","decision":"APPROVE","blocking":0,"scope":"61_file_3_link_inventory_only","rerun":false,"apply_or_GPU_authorized":false}
