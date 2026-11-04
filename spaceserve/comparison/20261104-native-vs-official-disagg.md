# 原生与官方解耦：首个真实请求正确性对照

这是两个独立单请求诊断，不是正式性能矩阵。原始证据：[native s4](../validation/official-entry-20261104/s4-evidence.json)、[fork f1](../validation/official-entry-20261104/f1-evidence.json)、[机器比较](../validation/official-entry-20261104/native-fork-equality.json)。

| 项目 | 原生 vLLM | SpaceServe 官方解耦 |
|---|---|---|
| 运行来源 | baseline d7ec548，tree与官方v0.7.2同 | 官方66de079 |
| 模型与预算 | Qwen2-VL-7B，单H20 GPU3，FP16 TP1 | 相同 |
| 请求 | COCO000328，单图，固定greedy/128 | 请求JSON字节SHA相同 |
| HTTP/curl | 200 / 0 | 200 / 0 |
| prompt/completion tokens | 281 / 128 | 281 / 128 |
| 输出内容 | 与图片主体相符 | 与native逐字一致 |
| 工作/原收尾/外层退出 | 0 / 1 / 1 | 0 / 0 / 0 |
| 恢复后释放 | 同身份stop0，GPU3显存0 | 自动收尾后GPU3显存0 |
| encoder mask | 无该解耦机制 | 实际日志明确libsmctrl不可用并跳过，未生效 |

两请求JSON SHA均为cd7c7b9c17b502a380fce9f2986c0ea6a6c3abf594b8d8e195ba75aec2f8f1c9；响应内容机器逐字比较为true，仅支持这张图的这一对请求，不是一般数值或输出一致性证明。模型对身份和地点的猜测不作事实，强制128后的尾部换行完整保留。

[Native窄G3](../validation/official-entry-20261104/native-g3.md)和[fork窄G3](../validation/official-entry-20261104/fork-g3.md)分别说明通过范围。原生旧收尾失败不改写；有界观察新助手CPU验证后在fork实际任务收尾0，不外推所有退出竞态都已消失。

f1原日志server.stdout第536行明确“libsmctrl is unavailable; skipping encoder SM partitioning.”；第553–554行记录编码器执行与结果入队。它支持官方编码路径实际运行，不证明GPU计算重叠、完整角色设备放置、SM集合或decoder互斥分区。有效mask组仍缺失。

固定请求、相同卡数和相同输出有助于后续比较，但本次运行顺序未平衡、样本各1、工具版本收尾不同，不能从初始化时间或零散日志推吞吐加速或P50/P95。TTFT/TPOT/E2E、峰值显存、并发路由与正式吞吐需按冻结协议单独测量；prompt281不等于视觉tokens数。

下一步处理实际libsmctrl缺失，再以独立机制诊断验证实际放置、并发和mask；同机正式测量串行，保留无收益和退化。完整日志和产物继续在服务器，必要小证据及逐文件SHA可浏览。

## 后续loader短诊断（仍未写入mask）

已找到现有libsmctrl，设置正确库路径后，smload2实际加载并查询到H20、capability9.0及78个SM；39只是库按架构计算的TPC估计，源码Hopper警告完整保留。[退出及GPU释放](../validation/official-entry-20261104/smload2-result.json)、[身份与起止](../validation/official-entry-20261104/smload2-identity.json)、[入场顺序审计](../validation/official-entry-20261104/smload-admission-audit.json)、[窄G3/G4](../validation/official-entry-20261104/loader-comparison-review.md)。

首次smload1在预约刷新回执返回前约7.4秒派发，不满足既定顺序，原件保留且不当作通过；smload2在已确认回执之后重新独立执行，事前顺序已核。该查询没有调用mask设置、模型、MPS或NVDEBUG，不能称mask生效。实际有效encoder mask与计算重叠仍需新机制诊断。
