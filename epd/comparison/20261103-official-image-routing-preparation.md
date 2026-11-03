# EPD 官方基线调用链及多图修复准备

状态：本地源码核查与 CPU fixture；未部署补丁、未运行模型，不构成正式实验配置批准。

固定来源为 EPDServe `9b111f710dfb4724072b603d626a1e4dad93ef1f`。21份调用链原件、SHA256及原始字节见 [official-epd-baseline-callchain-source-20261103.json](../validation/official-image-routing-20261103/official-epd-baseline-callchain-source-20261103.json)；EPD API 原件见[三入口源文件包](../validation/official-image-routing-20261103/official-three-handlers-source-20261103.json)。安装环境 MiniCPMV 源码为此前观察记录，不称当前 GPU 加载证明。

## 完整模型候选

官方 `baselines/d` 的 Request 从 `is_prompt=True` 开始，携带多模态输入进入 decoding stage；worker 创建正常 vLLM ModelRunner 并加载模型，首步之后才切换为逐 token 解码。安装环境 MiniCPMV forward 在有图像时进入视觉编码和 resampler，再进入语言模型。因此 D 是完整 VLM 的候选入口，不能仅因目录名推断为 decoder-only；是否真正完整执行仍须首请求和设备证据。

为落实已确认的三卡完整三副本、客户端均衡，实施候选是三个独立 D 服务，每个 DP=1、TP=1、独占一张 GPU，客户端固定轮询。不能直接拿官方 D 默认 DP=7；也不能根据源码传入 parallel_config 的方式推断实际三个 worker 必然共用同一物理 GPU。实际 placement 须记录 UUID。此处没有部署服务或更改已冻结正式请求协议。

## 官方 PD 候选

`baselines/pd` 的 context stage 执行带图像的首步 ModelRunner，然后把含 KV block table 和来源配置的迁移请求送往 decode。静态调用链支持 E/P 融合在 context 侧、KV 跨阶段传递的理解；不代替 CUDA IPC 数据一致性及实际传输验证。

官方 launch 默认 `PD_CONFIG=7,0`，不能照抄为三卡分离基线。三卡候选为 P1D2 或 P2D1；分配与调优规则尚未冻结，正式测试前需 G1 明确并取得适用用户确认，不以本草案授权自动搜索。不得将该目录包装称为独立 DistServe 已实测。

两种 baseline 均使用 `distserve` 包名，应在各自独立进程绑定相应目录，并记录实际模块位置。包初始化加载 CUDA IPC 动态库，不能在 CPU-only 阶段用导入测试冒充无 GPU 副作用检查。

## 三处多图路径错误

EPD、PD、D 的 API handler 均使用 `[load_image_cache(ps[0])] * len(ps)`，四张不同路径会变成四份首图。候选补丁在三个入口统一改成 `[load_image_cache(path) for path in ps]`，不改变缓存函数、KV/IPC 或调度。

从结果仓库根目录复现：`python -X utf8 epd/validation/official-image-routing-20261103/test_official_image_routing_20261103.py`。脚本直接解析保存的官方 handler AST，只执行到 SamplingParams 创建前，使用合成 request 和路径 loader，不导入官方模块。原版三个入口均复现 A/A/A/A，修改后为 A/B/C/D；单图输出保持一致，两个并发 fixture 分别路由。结果见 [official-three-handlers-image-routing-cpu-20261103.json](../validation/official-image-routing-20261103/official-three-handlers-image-routing-cpu-20261103.json)，补丁见同名前缀 `.patch`。

首次测试因证据字典键误写为 `distserve/api_server.py` 而在执行 handler 前 KeyError；改为实际 `epdserve/api_server.py` 后测试退出0。该测试没有证明真实图片解码、HTTP 并发或模型正确性。补丁未应用服务器；官方单图首请求仍优先从原版入口运行，多图性能必须在共同修复和真实正确性验证之后。

## 测量边界与下一动作

API 在服务端收集 token 事件后统一返回。服务端时间戳可用于定义服务端首 token/逐 token 间隔，但 buffered HTTP 返回时刻不能称客户端 TTFT；客户端 E2E 使用客户端自己的时钟，禁止跨时钟相减。正式口径和事件缺失处理仍需冻结，不用 fixture 生成性能数字。

下一步依次为独立补丁审查、合法 GPU 窗口的原版 EPD 单图首请求、按首个实际失败最小适配、真实多图及传输验证，再进入 PD/D 和公平性能。当前不启动 GPU，不缩正式协议，不增建外围框架。

独立 G2 审查：APPROVE / BLOCKING 0，仅候选补丁，[原文](../validation/official-image-routing-20261103/independent-g2-review.md)。没有部署或模型通过。
