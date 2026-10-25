# G4 缓存修正实际数据复审

实际审查者：独立subagent `/root/fallback_g4`。接替原因：Claude `usage_limit_reached`，用户按AGENTS3.2.1授权。提示词 `prompts/g4-cache-fix-data.md`。以下为实际审查原文。

**G4：APPROVE_WITH_NITS。原B1可以关闭；本次G4剩余BLOCKING：0。**

实际审查者：独立 subagent `/root/fallback_g4`。本轮进行了本地只读原始数据核对与独立复算，未修改文件、运行实验或访问网络、SSH、GPU、凭据；不包含G5。

- **BLOCKING：无。**
- **B1关闭依据：**
  - 独立解析四个补测配置的全部1,280条记录：各20预热＋300正式；全部成功、实际128输出token，三重复索引完整。与旧配置及对应请求核对，图片序列、提示词、处理后输入IDs保持一致；补测使用的`benchmark.py`与原双机归档版逐字节一致。
  - 从`data/dataset.tar.gz`独立解码20张源图并重算RGB SHA，核对全部16份服务快照、320个实际图片对象；尺寸、模式和像素SHA一致。前后API PID相同，且绑定实际`runtime-config.json`；设备UUID、boot ID、依赖版本和已加载cuBLAS路径集合与原验收记录一致。
  - 独立复算四行吞吐均值、样本标准差及300条请求合并P50/P95，均与选用summary一致。补测低负载约为：qjh003基线70.116、EPD65.534 tokens/s；qjh005基线70.881、EPD66.082 tokens/s，两台均约0.93×。
  - 独立核对新低负载两端配对，均300/300输出token完全匹配；summary及comparison均选择新来源，未混用旧低负载。CSV与JSON的来源及主要统计字段一致。
  - 对照补测前清单重新计算189个旧文件SHA，全部未变；四个旧低负载仅通过validity元数据标为替代。旧1,200条正式请求完整保留。
  - 独立核查原四矩阵GPU采样中的worker PID持续一致、配置时钟顺序和首配置后的图片覆盖；结合原`run_matrix.sh`持续循环及已审无淘汰字典实现，现有证据支持保留后续负载，无需因B1扩大补测。

计数也经独立核对：归档15矩阵、50配置、15,000正式＋1,000预热；最终选用46配置、13,800正式，其中12,000有效、1,800诊断；另1,200旧低负载被替代。配对7,200、完全匹配6,416，与报告一致。新增60个固定正确性案例的输入和输出对照通过；不扩大到所有基线副本均完成独立C8检查。

**NON-BLOCKING：**

1. `report.md:3`、`report/completion-audit.md:11,17,22`、`experiment-status.json:25–35`及delivery-audit仍保留“G4待复审／B1开放”。保存本次结论后同步刷新；G5继续待审，`goal_complete=false`继续保留。
2. `report.md:130`建议沿用`h20-cache-continuity.json`的谨慎措辞，写为“根据持续运行脚本、稳定GPU worker PID及无淘汰字典推演后续RGB覆盖持续填满”。这些证据不是直接缓存命中率测量，也不能排除所有API状态变化。此表述调整不影响B1关闭。

**QUESTIONS：无。**

## 主执行者处理

采纳两项建议：同步G4状态与B1关闭依据，G5保持pending及goal_complete=false；报告使用覆盖推演措辞，不称缓存命中率实测。没有改动原始数据或重跑未受影响负载。
