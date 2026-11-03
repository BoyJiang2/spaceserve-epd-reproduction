# SpaceServe 官方checkout：G1与步骤1–2（2026-11-03）

本阶段仅CPU静态源码/路径/依赖元数据及分支操作，没有执行SpaceServe/vLLM目标模块、--help、模型、MPS或GPU worker。历史旧repo的预检和性能结果独立保留，不直接作为当前官方checkout通过证明。

## 已核事实

| 项目 | 现场结果 |
|---|---|
| 权威源码目录 | /local/boyjiang/SpaceServe-official |
| origin | https://github.com/gofreelee/SpaceServe.git，未修改、未推送上游 |
| 官方基线及当前HEAD | 66de079af4234b27f7f82ff91d238ef1351324ba |
| tree | a21bbb151c79769bee5685707f36e56da86aa5de |
| 分支 | adapt/qjh003-v1，原detached且clean时建立 |
| 工作区 | clean，无源码修改；现有项目任务扫描为空 |
| Git跟踪文件数 | 1798（其中按后缀统计源码1303；不表示完整作者变更审计） |
| 解释器 | /local/boyjiang/spaceserve/assets/envs/space/bin/python → /usr/bin/python3.10 |
| 实际解释器版本 | Python3.10.12，符合README的3.10/3.11范围 |
| 分发包元数据 | torch2.5.1、vLLM0.7.2、Ray2.40.0、Transformers4.49.0 |

仅以给定绝对解释器-I -S -B执行标准库sys/json，未执行site/PTH或目标包。-S下prefix=/usr不用于推断普通venv加载行为。显式静态搜索把vllm解析到官方checkout，环境分发包元数据为0.7.2；这两件事实不证明完整运行时会正确加载该源码与二进制，也不证明fork与原生0.7.2的完整提交关系。

## 仍需核定的版本关系与入口

当前Space checkout为shallow仓库，tag与历史信息有限。源码vllm/version.py尝试导入未跟踪的_version.py，缺失时有dev回退；此为源码事实，未执行以观察实际__version__。不能把环境dist-info版本替代fork真实版本。

已保存README、setup.py、pyproject、requirements和vllm入口/版本/engine相关小文件SHA。README要求VLLM_USE_V1=1，模型入口为vllm.entrypoints.openai.api_server；vllm/__init__.py会导入torch及多层engine依赖。先核调用链，可能触发CUDA的导入/--help只在合法GPU窗口执行。当前未加载目标模块，actual_loaded_file未验证。

后续核清与原生vLLM的来源及受影响改动，复用现有环境/权重/编译产物，不因元数据差异就重装。旧路径/地址/身份/SM补丁不自动迁入，按当前实际错误做最小适配。

## 协议与证据

模型保持单H20、Qwen2-VL-7B FP16 TP1，后续对照对应版本原生vLLM、解耦、解耦加有效encoder mask。设备放置、并发和mask实效都须直接证据；按实际设备/配置定义SM允许集合，有限采样不强求覆盖全部允许SM，未验证decoder互斥不称完整分区。本阶段请求/压测预算0，未冻结新的正式运行。

[分支、命令原始输出、解释器与静态包元数据](../data/official-checkout-g1-20261103.json)来自本轮现场记录，省略源码base64正文，本地原件保留。两个SSH单元exit0，HEAD/tree保持，无源码修改。G1独立审查只批准当前CPU检查与条件分支建立，不批准GPU/模型。Claude实际403账户验证不是额度耗尽，实际使用独立subagent审查。

下一步是核fork来源与编译模块路径，再在合法窗口确认实际加载位置和模型/机制；正式三组对照仍未完成。两项目同机正式GPU测量串行，所有旧部分批次和失败保留。

## 可复制的只读记录命令

以下仅复核源码与解释器，须满足实际CPU授权；不导入目标包，不是GPU运行命令。完整实际命令和退出码见证据JSON。

```bash
cd /local/boyjiang/SpaceServe-official
git status --short
git rev-parse HEAD
git rev-parse 'HEAD^{tree}'
git branch --show-current
git remote -v
/local/boyjiang/spaceserve/assets/envs/space/bin/python -I -S -B -c 'import sys,json; print(json.dumps({"executable":sys.executable,"version":sys.version}))'
```

[固定官方源码](https://github.com/gofreelee/SpaceServe/tree/66de079af4234b27f7f82ff91d238ef1351324ba)。当前尚无适配commit，不以空分支声明适配完成。
