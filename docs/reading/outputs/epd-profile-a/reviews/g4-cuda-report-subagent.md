> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/epd-profile-a/reviews/g4-cuda-report-subagent.md) SHA256 47349b695c59781ffbdd9f18f5ccb118161f418f121b0a3fac7ed2bb6f7c8419。原数字及解释不变。

# G4：CUDA关联及本版最终报告

实际审查者：独立subagent `/root/profile_instrument_review`。Claude新实际is_error/usage_limit_reached，原始JSON g4-cuda-report-claude.json（session ae10e6bc-4489-4643-98ec-f81e0f9da609、reset22:50）已保存，按AGENTS3.2.1接替。只读核8SQLite/原始请求/JSON/源码，目检PNG及SVG，未改文件或跑GPU。

结论原文：**G4 CUDA分析及本版报告 APPROVE_WITH_NITS，BLOCKING为0。既有事实统计G4继续有效；本结论不替代G5，也不批准新增实验或SpaceServe机制。**

实际独立核查：

- 64请求、8192 API输出逐项匹配rid/endpoint/token号/原始时间戳；四配置index84–99完整。
- 同进程correlation、同线程完整worker范围关联，逐请求kernel数/首尾/跨度/并集/handoff均与JSON一致；baseline无mixed批。
- 实际worker PID集合、逐PID物理UUID正确，局部deviceId不当物理编号。选定kernel均在capture内，8 SQLite前后SHA不变。
- 整捕获迁移copy数/记录bytes/时间并集重算一致，未按rid分摊或称带宽。
- 高baseline边界跳过kernel88/354/346、memcpy8/17/8，未混入完整选定请求或完整GPU总成本。
- 共享batch存在，报告仅称参与活动曝光；CPU await/通知未构造GPU时长。
- EPD低/高E/P/D kernel并集P50为16.550/16.641/1517.111ms及60.773/49.792/1320.910ms。
- 报告保留无加速、-5.0027158%越诊断阈值、start计入第三重复/stop排除、77–83边界、有效输出差异及采样显存限制。PNG数值/误差线/图例正确无截断。

NON-BLOCKING落实：生成器和报告已改“64请求，每请求128次，共8192 API输出”；阶段交接抵消收益明确为待验证假设，D为多步解码/共享曝光，不能凭跨度判断off瓶颈或定量归因通信；保留只能证明已关联活动覆盖的口径。仅文字澄清，未改统计/原始数据。

QUESTIONS：无。G5及归档完整性仍待完成。
