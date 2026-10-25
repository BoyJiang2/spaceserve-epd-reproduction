审查者：Claude（claude-opus-5-5），只读，本次用了 8 次调用，读了 report.md、independent-recalculation.json、paired-mean-differences.json、README.md、next-experiments.md、render_report.py、analysis.json 前 170 行和 plan.md。没读的有：raw-field-samples、per-request.csv、analysis.json 其余部分、cpu-checks.txt、status.json、两张 PNG 图。

## G4：APPROVE_WITH_NITS，BLOCKING 0
已核对：
- **16 格分位数：** 报告表里的首间隔 P50 和后续间隔 P99 与独立重算逐格一致；首格与 analysis.json 的值完全相同。独立文件对池化 P95 和均值只给了 true 标志，没有数值，这两项我没能独立核对。
- **ΔE2E 分解：** 8 行分项之和都等于 ΔE2E，例如 127.63＝7.66＋4.87＋114.98＋0.13，131.11＝7.74＋4.70＋118.52＋0.16。
- **4 图/C8 尾部：** 两台机器上基线后续间隔 P99 三次重复都在 146.9–147.4ms，EPD 为 18.8–20.4ms。报告没有据此推导吞吐更好或 prefill 因果。
- **来源与封存：** 分析前后快照一致（969 文件，ZIP 3d1253…）；16 个源文件路径确认两台机器分开，1 图/C1 来自 cache-fix，其余来自原矩阵，SHA 齐全。
- **事件与统计措辞：**
  - 无效 TTFT 链为 0、KV 只是 CPU/API 单向关系、没有重复时间戳，这三点在 render_report 里都有断言；reported_decode 只作描述。
  - 均值可加、分位数不可加，间隔之间有关联，P95 约 15 个尾部样本，C1 来自后补会话，这些都已写明。

NON-BLOCKING：
1. C1 后续间隔差约每个间隔 0.9ms，这里面也包含 EPDServe 自带引擎与原生 vLLM 的实现差异。报告应明说这部分不能归于解耦本身。
2. EPD 也有很大的单次最大间隔，约 209–532ms：两台机器的 1 图/C1、4 图/C1 的两次重复、1 图/C4 的一次重复。报告只谈了基线长尾，建议加一句提示，不需要新增数值。
3. 四个假设里"E/P 等待"报告没有讨论，建议注明 TTFT 分段只存在 analysis.json 里，本批没有解释。
4. render_report 第 64、84 行叙述里的数字是写死的，没有断言；目前与数据一致。

## G5（本离线批次）：APPROVE_WITH_NITS，BLOCKING 0
plan.md 的验收项都满足：4800 条来源覆盖完整，封存前后不变，独立重算一致，源码语义经 G3，报告分开了观察、源码依据和假设，下一轮只形成方案。G1、G2（B1 已关闭）、G3、G4 都是有效结论。

批准有一个前提：收尾逐文件核验时，要确认 cpu-checks.txt（9 项通过）、两张 PNG 和 status.json 里的真实 Gate 状态都在包里。这几项我没读到。

NON-BLOCKING：
1. README 写"仅标准库"，但 render_report 需要 matplotlib 和 numpy，README 也没写复跑命令 `python scripts/render_report.py .` 和依赖版本。这是纯文档更正，不涉及数值。
2. analysis.json 没记录脚本自身的 SHA。本批 SHA 清单要覆盖 analyze、render 和 tests；建议用打包版脚本重跑到新目录，逐字节比对输出（输出应是确定的）。
3. 封包时再验一次旧的 969 文件清单和 ZIP。
4. plan 第 4 条要求的"明确证伪条件"只部分满足，转为方案 A 进入 G2 前的前置要求。

## 方案 A 的 G1：APPROVE_WITH_NITS，BLOCKING 0（只批范围，不授权 GPU）
模型、协议、三卡、两个已有负载点、2400 条正式加 160 条预热的预算都与原设定一致；profiler 开启的会话只作诊断；B 方案没有纳入。进入 G2 前需补：
1. **判定规则：** 每个假设写明判定规则，例如在 C1 下对照 D 端每步 GPU 跨度差和 API 间隔差。"记录现有采集不足"不能作为唯一的验收结果。
2. **按现象触发采集：** 三类窗口分别是稳态解码、"P 最后一步→KV 复制→第一个 D 步"、基线新请求 prefill 造成的停顿。固定 8 步的窗口可能捕不到 147ms 那段尾部。
3. **关闭模式的定义：** 写明关闭模式是否保留 API/Ray 标记。如果保留，要拿第一轮三次重复的范围核对标记开销，并给出数值化的扰动阈值。
4. **trace 导出时机：** 导出放在计时窗口之外。

B 方案（同三卡 PD）须用户另行同意，本次不批。
