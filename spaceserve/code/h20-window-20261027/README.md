# H20 SpaceServe：指定commit部署入口（模型预检完成，正式未启动）

实际模型运行使用固定 runtime commit `83edff6608fc9db33ea90c3d04ce091705ee643f`，313 请求的模型 G3 与预检报告 G4 已通过；完整54正式矩阵未启动。[原件、实际版本及发布状态](../../preflight-20261027-1300/README.md)单独保存。下方部署命令保留原窗口语义，不能在新窗口直接复用旧预约/批准。

本目录冻结同单H20/Qwen2-VL-7B/FP16/TP1/eager的native、解耦、有效encoder mask三组代码。模型预检的实际版本与通过状态见上方，未完成新54单元，不提供新的性能结论。[旧48/54真实对照](../../comparison/README.md)独立保留；旧数值与零请求启动失败发生在本代码commit建立前，不能追溯称由此commit运行。

## 固定配置与依赖

模型上下文4096、max_num_seqs8、max_num_batched_tokens4096、seed0、显存比例0.65；生成temperature0/ignore_eos/128tokens；COCO每请求1/4图、并发1/4/8。实际处理448×448、256视觉tokens/图，pixel kwargs被忽略。三角色decoder仍含visual权重，encoder mask不证明decoder互斥。源为SpaceServe66de079af423及同基线vLLM0.7.2、torch2.5.1、transformers4.49.0。模型/环境/缓存独立管理，仓库仅提交文件SHA元数据及必要补丁。

[56源码清单](configs/runtime-extension-source-manifest.json)、[部署文件清单](configs/deployment-files.json)、[输入与环境逐文件SHA](configs/relocated-inputs.json)、[54顺序](configs/schedule-v2.json)、[模型pins](configs/input-pins-summary.json)、[补丁](patches/)及[实际CPU31/审查](reviews/)均在本目录。动态预约、GPU批准、运行回执是独立证据，不通过提交历史PASS代替新准入。

## 指定commit部署

本地修改/测试/独立审查后commit并push；从GitHub读取实际main SHA作为`<commit>`，服务器只在有效预约与空闲状态部署。创建新的独立checkout，禁止修改旧封存：

```bash
git clone --filter=blob:none --sparse --no-checkout --depth=1 https://github.com/BoyJiang2/spaceserve-epd-reproduction.git /var/tmp/boyjiang-space1300-stage/git-checkout
git -C /var/tmp/boyjiang-space1300-stage/git-checkout sparse-checkout set spaceserve/code/h20-window-20261027
git -C /var/tmp/boyjiang-space1300-stage/git-checkout checkout --detach <commit>
/var/tmp/boyjiang-spaceserve-window-20261027-1300/envs/space/bin/python -B /var/tmp/boyjiang-space1300-stage/git-checkout/spaceserve/code/h20-window-20261027/tools/deploy_commit_cpu.py --checkout /var/tmp/boyjiang-space1300-stage/git-checkout --commit <commit>
```

部署器只允许将已审、与当前runtime逐SHA相同的代码重新部署，记录`evidence/GIT_DEPLOYED.json`中的commit及逐文件清单；不启动GPU。它拒绝dirty checkout、错误commit、运行中的root、源/目标SHA差异和覆盖旧部署回执。环境模型需另行准备并通过完整pins核验；本命令不是空机器一键安装。

## 运行与验收

此次窗口严格限qjh000/GPU4指定UUID。实际本人两票连续覆盖，但用户仅授权至18:00，17:58收尾。未来窗口必须先本地改时段/资源，经审查形成新commit，不能直接复用旧预约或批准文件。

```bash
source /var/tmp/boyjiang-spaceserve-window-20261027-1300/scripts/env.sh
# 实际数值G3及numeric→model consumer、精确模型代码G2、新鲜预约与输入、空闲等全部门槛满足后才执行：
python -B "$EXP_ROOT/scripts/model_launcher.py"
# 实际模型G3、formal G2与201分钟完整入场预算通过后才执行：
python -B "$EXP_ROOT/scripts/formal_launcher.py"
```

本批记录一次零请求基础设施失败，经独立审查批准的唯一313预检接续不扩大模型请求预算；失败再次停止，不自动第三次。正式为54cell/5400请求+1080预热，20预热+100正式每cell；完整窗口不足不缩验证/矩阵或跨窗拼旧区组。源码/补丁/静态配置运行期间冻结；批准和运行回执允许按规范新建，不能修改代码继续声称同commit。

全部成功/失败逐请求、实际命令/commit/配置、正确性/SM机制、吞吐/TTFT/TPOT/E2E/显存/失败率与波动、完整性和限制须按对应范围独立G4/G5后发布。模型预检及报告已审，完整性能与项目交付尚未完成；大trace另Release并给大小SHA。历史通过记录不构成新窗口的运行许可。
