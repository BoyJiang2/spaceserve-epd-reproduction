# EPD退化的后续离线分析

第一轮复现已验收；本批只读其最终选用的4800条H20请求，核对事件源码语义、输出时间线和下一阶段实验方案。第一轮的原始数据、统计及ZIP不覆盖。当前进度及真实Gate结论见status.json，范围与验收标准见plan.md。

## 复跑条件与命令

分析及CPU测试需要Python3.12和标准库；绘图/报告生成另需Matplotlib3.9.2、NumPy1.26.4，本次实际分析Python3.12.14。将第一轮的reproduction-h20.zip与解压出的reproduction/放在本目录旁，保持旧目录全部字节不变；旧包外层SHA固定为 `3d12536a846208e3202b67650adeee2f424cc4da1bb0a6cc28c67a494941be38`。不要先重生成旧报告或更新其时间戳；本批分析不依赖旧报告图片能否在新路径显示。

在本目录执行：

```bash
python tests/test_analysis.py
python scripts/analyze.py ../reproduction results
python scripts/render_report.py .
```

第二个参数必须是新的输出目录，不能位于旧reproduction/内；已有analysis.json时拒绝覆盖。脚本在完整读取前后逐个核对旧969个payload的SHA及外层ZIP SHA；首1图/C1按旧summary选择cache-fix，其余选择原矩阵，排除所有预热及诊断记录。

render_report读取results/analysis.json并生成两图与report.md，固定位置写入图像绝对路径以供本应用预览；换目录后执行它刷新链接。重算到不同目录时，请自行指定新的目录名，不先删除已交付结果。

输出results/analysis.json与per-request.csv。每host、每case分别统计，保留三次重复；后续126间隔的分位数按间隔池计算，样本之间有关联，不解释成独立试验或显著性证据。TTFT分段只在逐请求链路有序时给出，异常比例明确记录；报告不能把各段P95相加。

## 来源和解释边界

- source/replay-manifest.json：固定官方Git commit及归档合并补丁的文本重放SHA，含四份实际基线适配器快照。仅api_server/llm_async有预期修改，核心事件代码与Git blob逐字节一致；没有执行这些模型源码。
- source-notes.md：API消费时刻与orchestrator callback的区别、decoding_begin覆盖、P首token与迁移顺序等源码依据。只有EPD有阶段事件，不与基线作kernel级比较。
- per-request中的decode_window是首末输出通知窗口；reported_decode是原事件所记录的跨度，不能互换。output_window_overlap是同端点输出窗口重叠代理，不是GPU batch size；同时间戳合并通知的0号bin不是零个在途请求。
- next-experiments.md：具体profiling方案与同三卡PD候选，均未启动，需独立审查和用户确认。当前批次不更改第一轮模型、负载、基线或观测记录。

审查提示词及实际结果在reviews/。Claude优先，实际额度耗尽时按用户要求由独立subagent接替；每个结论单独署名，不以脚本自检代替G4/G5。
