# SpaceServe 2026-10-31 模型预检结果（正式性能尚未运行）

qjh003，单张 H20 GPU2，Qwen2-VL-7B-Instruct，FP16、TP=1；复用原仓库、环境和权重。[独立实际模型 G3](../data/space-20261031-G3.md) 已通过（BLOCKING 0），范围仅限本批模型正确性和机制预检。

| 检查 | native baseline | 解耦 | 解耦＋encoder mask |
|---|---|---|---|
| 冷启动正确性 HTTP 200 | 15/15 | 15/15 | 15/15 |
| 冷启动输出 token 与同轮基线一致 | 15/15 | 15/15 | 15/15 |
| 重启正确性 HTTP 200 | 15/15 | 15/15 | 15/15 |
| 重启输出 token 与同轮基线一致 | 15/15 | 15/15 | 15/15 |
| 实际编码器流 SM 探针，冷启动和重启 | 不适用 | 78→78 | 78→54 |
| 对齐时钟的 encoder/decoder kernel 重叠，冷启动/重启 | 不适用 | 564317 / 567123.75 μs | 1409288.25 / 1410180.25 μs |
| 本批正式性能单元 | 0 | 0 | 0 |

六组正确性请求的 processed_prompt_token_ids 也均与同轮基线一致。全模型预检根记录 generated_requests=313，其中含诊断/预热等请求，不把313全部称为正确性用例。重叠时间仅说明采样片段中并发执行，不能作为吞吐收益或严格资源比例。

原模型阶段与 launcher 实际退出码均0；外层SSH观察最终超时、local exit1，原因未定位，两者分开保留。末态受控采集实际exit0：GPU2 0MiB/0%，compute apps为空，private MPS stopped，自有及不明标记进程均为空。正式矩阵最晚07:37入场限制已经关闭，本窗口不缩矩阵、不拼旧48、不再启动正式54；仍待下一有效完整窗口。

只验证有效encoder mask，不称完整encoder/decoder互斥分区。六服务共313条 min_pixels/max_pixels 覆盖参数被丢弃警告，不能声称这些参数强制生效；实际20图均448×448/RGB、逐图SHA与缓存manifest前后相同，四图实际视觉token为1024，正确性processed IDs与基线一致，支持本批输入一致。预检profile-on诊断数据不是正式吞吐/TTFT/TPOT/E2E对比。

## 原始证据与版本

- [逐文件终态清单及释放原件](../data/space-20261031-evidence.json)：272文件，389866812字节，逐文件SHA256。
- [313条逐请求记录（含来源SHA；262原件见metadata资产）](../data/space-20261031-requests.jsonl)：逐请求JSONL保留来源文件与其SHA；262份原件共8861910字节，以原base64封装保存在metadata资产，另有可读机制JSON。
- 10个压缩profiler trace共381004902字节原件保持在原服务器；已通过stdout流式取回至单一[归档](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/tag/spaceserve-qjh003-preflight-2026-10-31)，381030400字节，SHA256 `f504b4911d33acd23e77c5db24dedc175f5e6069a570c85a491473000c077a45`，全部10成员逐bytes/SHA与清单核同，见[传输验收](../data/space-20261031-assets.json)。尚未上传Release；未在服务器生成封包，未复制权重/环境或GB级副本。
- [单次终态采集执行审查](../data/space-20261031-capture-G2.md)、[采集退出回执](../data/space-20261031-capture-exit.json)。
- runtime edcaa1bd25934591a21dc2e99a51cf07a6ec39c6；CPU verifier a899d6456a95f6d155c77d57f538631b9b71dafc；闭合启动工具bc460f50777305fa775754cbf33e79d55ed05619。
- actual模型manifest SHA256：707dee09621845e0cf460fcd90c7d619acda6896a57c30dd9d10ad5855b189cd。
- 原capture helper SHA e72f1c82b871c6b8ea3af79e75db3e97c7b2688d3095b812aa15473dc3d1fded；实际执行适配源码SHA 85c31286af762d9e46312955a534b084bfb12a8258019b6da87c100bcb4d954f，仅七处记录名替换，无校验逻辑改变。

旧失败、两轮过期input、外层SSH超时原件均保留；整体复现目标未完成，EPD公平PD后续也未因本次预检获得批准。

## 下载与复跑入口

本批 Release 尚在准备，下面列出本地已核验资产；发布后才记录真实下载验收。

| 资产 | bytes | SHA256 |
|---|---:|---|
| closed-model-traces.tar | 381030400 | `f504b4911d33acd23e77c5db24dedc175f5e6069a570c85a491473000c077a45` |
| space-20261031-metadata.tar.gz | 3410704 | `2ac08e99f6e7a23b89c37ce647864e57b131887bc2346861c9196cf288db7f4c` |

[历史正式baseline对比](README.md)与本批预检分开。完整源以固定commit读取：

- [runtime及入口](https://github.com/BoyJiang2/spaceserve-epd-reproduction/tree/edcaa1bd25934591a21dc2e99a51cf07a6ec39c6/spaceserve/runtime)
- [闭合启动工具](https://github.com/BoyJiang2/spaceserve-epd-reproduction/tree/bc460f50777305fa775754cbf33e79d55ed05619/tools/space_closed_startup.py)
- [CPU兼容验证工具](https://github.com/BoyJiang2/spaceserve-epd-reproduction/tree/a899d6456a95f6d155c77d57f538631b9b71dafc/spaceserve/runtime/tools/verify_deployment_cpu.py)

原始运行argv/config/输入清单与成功失败记录在metadata资产及evidence内；资产路径是当时主机路径，新窗口需按runtime的配置入口重新核资源与预算，不能直接重放历史批准或本次预约。
