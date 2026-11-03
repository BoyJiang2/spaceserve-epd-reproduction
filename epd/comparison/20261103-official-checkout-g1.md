# EPDServe 官方checkout：G1与步骤1–2（2026-11-03）

本阶段只做CPU静态源码/路径/依赖元数据检查及适配分支建立。没有导入EPD、vLLM、torch或Ray，没有执行目标API或--help，没有模型请求、GPU worker或MPS；这不构成一般意义的“导入无GPU副作用”证明。

## 已核事实

| 项目 | 现场结果 |
|---|---|
| 权威源码目录 | /local/boyjiang/epdserve-official |
| origin | https://github.com/vbdi/epdserve.git，未修改、未推送上游 |
| 官方基线及当前HEAD | 9b111f710dfb4724072b603d626a1e4dad93ef1f |
| tree | e1d61bf20a265a856bd84eb03a3c2d1d8d1cb5c6 |
| 分支 | adapt/qjh003-v1，原detached且clean时建立 |
| 工作区 | clean，无源码修改；现有项目任务扫描为空 |
| Git跟踪文件数 | 188（其中按后缀统计源码83；不等于已审计全部作者改动） |
| 解释器 | /local/boyjiang/epd/assets/envs/epd/bin/python → /usr/bin/python3.10 |
| 实际解释器版本 | Python3.10.12；官方env声明3.10.14，差异保留 |
| 分发包元数据 | torch2.4.0、vLLM0.6.1.post2、Ray2.10.0、Transformers4.44.2 |

解释器只以-I -S -B运行标准库sys/json；记录了真实sys.executable和版本。-S下sys.prefix为/usr，不据此判定venv损坏。依赖版本来自dist-info，静态PathFinder显式搜索官方目录与该环境site-packages；不执行PTH，也不把静态spec当实际import结果。目标包实际loaded_file仍未验证。

## 官方入口及边界

核对了README、env.yml、offline.py、launch_server.sh、epdserve包入口/API、PD/D API及文件SHA。epdserve/__init__.py会导入torch并执行torch.ops.load_library，不能把普通import或--help归为必然无GPU副作用；此类检查安排在合法GPU窗口。

官方仓库本身已跟踪示例图片，旧repo遗漏示例引发的导入失败不能机械认定新checkout也会失败。旧sample guard、多图路由、身份、地址、通信或调度修改均未自动迁入；需要当前问题依据、针对性检查与适用审查。旧repo保留为历史。

静态代码显示在线AsyncLLM选择EPDOrchestrator，离线入口另有选卡与动态角色路径，后续优先明确E:P:D=1:1:1、关闭请求内编码并行的官方在线入口。模型仍MiniCPM-V-2_6 FP16 TP1；正式三卡比较为三个完整副本、官方PD和官方EPD，PD三卡分配/调优与正式协议后续冻结，本次请求预算0。

## 证据与下一步

[状态、原始命令输出及静态环境记录](../data/official-checkout-g1-20261103.json)从本轮只读检查与分支操作结果提取，源码大段base64省略，本地原件保留。Git symbolic-ref在原detached HEAD下的exit1是预期查询结果；两个SSH单元最终exit0。G1的独立审查只批准17:05–18:30的CPU动作，不批准GPU或模型。

Claude优先调用实际返回403账户验证错误，不是额度耗尽；本阶段由独立subagent审查，来源如实记录。

下一步继续核当前解释器与vLLM API兼容、明确既有资产路径；在合法三卡窗口执行官方单图真实请求，再验证并发、重启及embedding/KV。适配commit形成后离机保存并推已核属用户远端，官方origin保持不变。当前无适配commit、无新模型结果、无性能结论；旧批次结果不作当前checkout通过证明。

## 可复制的只读记录命令

以下仅复核源码与解释器，须满足实际CPU授权；不导入目标包，不是GPU运行命令。完整实际命令和退出码见证据JSON。

```bash
cd /local/boyjiang/epdserve-official
git status --short
git rev-parse HEAD
git rev-parse 'HEAD^{tree}'
git branch --show-current
git remote -v
/local/boyjiang/epd/assets/envs/epd/bin/python -I -S -B -c 'import sys,json; print(json.dumps({"executable":sys.executable,"version":sys.version}))'
```

[固定官方源码](https://github.com/vbdi/epdserve/tree/9b111f710dfb4724072b603d626a1e4dad93ef1f)。当前尚无适配commit，不以空分支声明适配完成。
