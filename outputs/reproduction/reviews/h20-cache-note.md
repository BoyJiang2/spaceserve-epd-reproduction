> 最终G4结论APPROVE_WITH_NITS，B1已关闭，BLOCKING为0；下文保留最初发现与修复中的历史讨论。原文见subagent-g4-cache-fix-data-20261023.md。

# 待审查：H20 首配置的 RGB 缓存覆盖差异

这是 Codex 在离线核对中发现的疑点，不是 Claude 审查意见或既定归因。

后续：独立subagent的G2/G4确认该问题需要定点成对补测；具体纯RGB初始化补丁已在正式运行前经G2批准，两台补测均已完成并通过技术审计，16份实际缓存快照匹配源图。原低负载数据被新配对替代但没有删除；G4复审前B1仍开放。下文保留最初发现与方案讨论，当前状态见report/experiment-status.json。

证据：

- `scripts/benchmark.py` 将全局20条预热按 `index % len(urls)` 分发，基线三端点，EPD一个端点；每配置正式100条重复3次。
- `scripts/baseline_server.py:50` 附近创建每进程图片字典，按路径缓存RGB，无淘汰。
- qjh003当前固定EPD源码 `src/epdserve/epdserve/api_server.py:72–86` 经SSH只读核对：每服务进程 `image_cache = {}`，`load_image_cache` 按文件basename缓存，首次调用载入，后续复用，无淘汰；COCO文件名唯一。官方自带一张非COCO图片不影响COCO20张的覆盖统计。
- `reviews/h20-fairness-facts.json` 从归档的config与requests逐项生成。覆盖字段假设新启动服务初始COCO缓存为空、同矩阵服务持续运行；它不是instrumented缓存命中计数。固定正确性请求可能先覆盖部分EPD图片，但首次20预热后仍已覆盖全部20张。

两主机首配置 images1-c1 的预热后COCO覆盖：EPD端20；基线三个副本7/7/6。第一正式重复中，基线还有40个未在预热中覆盖的“端点/图片”组合。后续配置沿用前序正式请求填充的缓存。因此“相同缓存实现策略与请求序列”成立，不能进一步声称“完全相同的初始缓存状态”。没有对首次RGB加载成本做额外测量。

待判断：这对首配置性能对照是否构成阻断；是否需要在不改变全局20预热协议的条件下，用统一的启动前RGB预载方案针对性补测，或限定结论。上述方案尚未实现、未审查、未运行，不自行改为每副本20条推理预热，不删掉第一重复或挑选有利结果。报告保持草稿，项目未完成。
