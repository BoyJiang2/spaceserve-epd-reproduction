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


## 18:01：实际 encoder stream mask 兼容性失败

在新确认的18–23点窗口内，使用同一GPU3和当前库运行独立无模型数值测试 `smnumeric1`。代码已在 `236ac7b3757e84c2ce53edf34fbd0a84db1c3533` 发布并逐文件核同。

- 未设置mask时，5轮均观察到SM ID 0–77；这是本次设备采样结果，不是硬编码验收值。
- 首次调用官方wrapper的encoder默认mask `[0,0,0,4095]` 时，库直接报错退出1：`Stream masking unsupported on this CUDA version (13000)`。masked采样轮数为0，complement未执行。
- 这里的13000是库查询到的CUDA Driver API版本，不能与PyTorch的cu124构建版本混为一谈。当前依赖源码的stream-mask分支最高列到12060；未使用MASK_OFF覆盖或伪造版本。
- 退出后GPU显存0、compute-apps为空。完整原始采样、stdout/stderr和身份/终态留在服务器 `spaceserve/runs/smnumeric1/`；[小证据及完整原件SHA256](../validation/official-entry-20261104/smnumeric1-small-evidence.json)可直接浏览。

因此当前状态为：native单请求通过；明确跳过encoder mask的官方解耦单请求通过；**有效encoder mask尚未通过**。失败定位在当前固定库与Driver API版本的兼容路径，不能推断H20硬件不支持。未验证模型stream、计算重叠、decoder互斥或任何正式性能收益。

[作者依赖源码](https://github.com/gofreelee/mysmctrl/blob/6ff57356968a3f04158b9273aa881ee6bdf04229/libsmctrl.c)保留版本分支依据。后续只按有来源的兼容更新做最小适配；不靠猜测结构偏移获得“通过”。
