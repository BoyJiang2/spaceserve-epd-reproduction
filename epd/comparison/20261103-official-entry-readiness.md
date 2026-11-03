# 官方 EPD / PD / D 入口准备：目标机 CPU 验证（2026-11-03）

本批已完成官方基线恢复、原目录增量部署及三组 API 依赖加载；**真实模型请求为0，尚无新GPU性能数据**。历史性能结果继续保留在[项目对比导航](README.md)，本页不能替代正式复现结果。

## 官方来源与实际版本

- EPDServe 官方固定版本：[9b111f710dfb4724072b603d626a1e4dad93ef1f](https://github.com/vbdi/epdserve/tree/9b111f710dfb4724072b603d626a1e4dad93ef1f)。核对了README、Git tree、offline.py、launch_server.sh、baselines/pd、baselines/d和automate_e2e.py。
- [75e77fb](https://github.com/BoyJiang2/spaceserve-epd-reproduction/commit/75e77fb254746444d4db5fd25866f9db816e9eb0)补回此前部署遗漏的44份官方PD/D源码、375224字节。与官方原Git blob逐字节一致，未带入上游pycache和旧runs。
- 当前目标机版本为[1a5c61e](https://github.com/BoyJiang2/spaceserve-epd-reproduction/tree/1a5c61e448aab9fe54c4ec7a7626ef6267efa4ed/epd/runtime)。在75基础上，仅PD/D各增加可选示例图片存在性判断，并新增隔离回归。200项部署源码已核验，工作区clean。
- EPD运行路径仍包含既有兼容、RGB加载、身份采集和内部PD扩展补丁，不称“未经修改的官方代码”。本次恢复的PD/D除上述示例图片guard外沿用官方实现；内部融合PD没有冒充此官方PD。

## 入口核查与当前证据

| 系统 | 沿用的官方调用链 | 本批实际结果 | 仍未证明 |
|---|---|---|---|
| EPD | epdserve.api_server → AsyncLLM → 静态EPDOrchestrator → E/P/D | 目标机API `--help` exit0 | 模型、单图响应、并发、embedding/KV传输 |
| 官方PD | baselines/pd 的distserve.api_server → AsyncLLM → context/decoding clusters | 修复缺失示例图片后 `--help` exit0 | E随P的实际执行、KV迁移、三卡公平配置和性能 |
| 官方D | baselines/d 的distserve.api_server →完整模型workers | 修复后 `--help` exit0 | 三副本均衡、模型输出和性能 |

官方PD代码把多模态请求交给context侧vLLM ModelRunner，KV再迁往D；目前这是源码事实，尚无本批模型运行证明。准确名称为“EPDServe仓库内官方PD基线”，不能仅凭目录名宣称独立上游DistServe已经实测。

官方脚本默认EPD六卡2:2:2、PD7:0、D7；不能照抄成三卡公平实验。离线入口还会自动选卡、覆盖CUDA_VISIBLE_DEVICES，OfflineLLM默认动态orchestrator；首轮选择在线静态入口明确1:1:1和关闭请求内编码并行。automate_e2e包含/tmp通配删除和递归kill，共享主机不照搬这些清理动作。

## 真实失败与最小修复

第一次检查：EPD帮助加载成功；PD在api_server.py顶层预加载`assets/images/image2_4032_3024.jpg`时FileNotFoundError，进程exit1；D按失败即停规则未派发。服务器使用已有COCO dataset，未存放此仓库示例图片。

修复只在PD/D顶层示例预加载前增加`os.path.isfile(image_path)`。已有示例仍照旧缓存；真实请求图片缺失仍报错。没有更改调度、KV传输、精度或模型路径解析。局部回归先在原源码得到4个subcase errors，再在补丁后通过；其范围是AST提取的导入/缓存段，假Image不测试图片解码或模型。

修复后目标机真实结果：3个回归方法/6个PD/D子项通过，EPD、PD、D三个API `--help`全部exit0。CUDA_VISIBLE_DEVICES为空；没有Ray服务初始化、模型请求或性能压测。原父进程1440353/start61972697已退出，signals/cleanup为空。

## 原始证据与复核

- [首次失败原始命令日志](../data/official-20261103-help-failure-commands.log)、[失败记录](../data/official-20261103-help-failure.json)。
- [修复后原始命令日志](../data/official-20261103-help-success-commands.log)、[原始终态](../data/official-20261103-help-success-terminal.json)。
- [物理源码与释放摘要](../data/official-20261103-physical-summary.json)：从原只读回收结果提取，非完整原始封包；保留200份源码SHA、实际HEAD和原PID状态。
- [独立实际G3审查](../data/official-20261103-actual-G3.md)、[机器可读验收](../data/official-20261103-actual-G3.json)。
- [补丁及回归diff](../data/official-20261103-asset-fix.patch)、[本地红灯](../data/official-20261103-regression-red.txt)、[本地绿灯](../data/official-20261103-regression-green.txt)。
- [首请求输入及图片指纹草案](../data/official-20261103-first-request-evidence.json)，状态仍为DRAFT_NOT_SENT。

本机dist-info记录torch2.4.0、vLLM0.6.1.post2、Ray2.10.0、Transformers4.44.2；版本标签不替代安装文件完整性证明。

## 下一次真实运行

复用`/local/boyjiang/epd`现有环境、权重和COCO dataset，先在合法三卡短窗口执行官方对应在线EPD入口，E:P:D=1:1:1，MiniCPM-V-2_6 FP16/TP1，使用已有图片COCO_val2014_000000000328.jpg；目标128输出token并记录实际长度。启动入口为上述精确commit下的`python -m epdserve.api_server`，而非先强制通过native36/selected整套框架。

三张卡的真实UUID/NUMA、空闲、端口、截止与自有进程释放须在该窗口核对。当前模型配置文件存在、图片路径和SHA已实查，但没有请求发送。随后验证小并发/重启与阶段传输，跑通官方PD/D，再冻结同三卡总预算的正式矩阵；PD1:2或2:1分配不能借官方7:0示例替代调优协议。

本轮未改SpaceServe、未重跑GPU，也未改旧53/60、48/54、封存目录或ZIP。两项目正式GPU测量仍串行，正负收益均按各自baseline报告。
