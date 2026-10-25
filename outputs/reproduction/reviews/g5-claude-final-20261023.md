# Claude (claude-opus-5-5) G5

实际会话：`baf9dad2-d355-4528-b56c-02c841d6131a`；用时 496298ms；permission_denials为空。实际提示词 `prompts/g5-claude-focused.md`，原始结果 `g5-claude-final-20261023.json`。

# G5 最终交付审查

**审查者：** Claude（claude-opus-5-5），只读会话。本次调用 Read/Grep/Glob 共 18 次：读了 12 个指定文件，另读 `h20-final-script-provenance.json`、`patches/README.md` 和 `summary.csv` 表头；对 `delivery-audit.json` 只用 Grep 查了状态字段；用 Glob 列出交付目录 `reviews/`；做了一次凭据特征 Grep，只返回文件名。AGENTS.md 已在会话上下文中，没有另行调用。没有改文件、运行命令或实验，没有访问网络、SSH 或 GPU，没有读凭据或聊天历史。

**范围：** 按完成标准逐条核对。G1–G4 采用已归档的 subagent 有效结论，没有重做逐请求复算。我无法用只读工具检查 `work/g5-review-candidate.zip` 的字节内容。候选包完整性依据的是主执行者自报的 `work/g5-candidate-integrity.json`，我没有独立复核。

## 结论：**APPROVE_WITH_NITS**，BLOCKING：0

完成下文"收尾条件"并校验通过后，可以宣布既定目标完成。

## 完成标准逐条核对

| 要求（AGENTS §5 / goal.md） | 依据 | 判定 |
|---|---|---|
| 两台 H20 通信数据一致；三阶段链路正确；冷启动及重启后并发正确 | G3 独立核对原始证据（`subagent-g3:5–9`）：每台六方向 P2P、39 次 KV、3 次 embedding，45 例覆盖 epoch1/2 及 C8 请求重叠。补测新增 60 例由 G4 复核（`subagent-g4-cache-fix-data:18`） | 满足。限制已在 `report.md:45,49` 披露：只做过一次重启；60553 是缓存分配规模，每次只传 18 blocks；探针用常数模式 |
| 公平基线；约定的双机矩阵全部完成 | qjh003 跑 6 个点、qjh005 跑 2 个点，均为 EPD 对同机同三卡三副本。1/C1 在纯 RGB 预载后成对补测，16 份实际缓存快照与独立解码一致；B1 已由 G4 关闭（`subagent-g4-cache-fix-data:5,10–16`） | 满足。后续负载的缓存覆盖是推演，不是实测命中成本，`report.md:130` 已如实限定 |
| 结论可由逐请求数据复算 | `summary.csv` 表头齐全：request_throughput、tokens/s、TTFT/TPOT/E2E P50/P95、failure_rate、显存峰值、sd、source_case/source_kind。复算命令见 `README.md:83–94`；G4 已独立复算新增行和计数 | 满足 |
| 协议：MiniCPM-V-2_6、FP16、TP1，IRP 与动态切换关闭，20 预热 + 100×3，128 token | `report.md:5,11,128`；G1 | 满足 |
| 指标与交付物 | summary 覆盖 §1.2④ 全部指标；scripts、patches、configs、data、evidence、report 及图表齐备；`patches/README.md:8–9` 写明历史补丁与最终补丁互相替代、不叠加 | 满足 |
| 合并 SpaceServe 4090/L20，各自对自身基线，不做跨 GPU 排名 | `report.md:51–84` | 满足 |
| sapphire3 失败记录保留并标为诊断 | `report.md:7,103,122`；`README.md:106` | 满足 |
| 执行边界与凭据 | 文档声明没有改内核、IOMMU 或驱动，只清理本实验进程树（历史 G2 已核对 `stop_server.py`）。我对 sh/py/md/json 做的凭据特征扫描没有命中 | 满足。扫描是启发式的，没有覆盖 log、jsonl、txt、diff、patch、csv |
| 报告分别回答四个问题 | 答案分散在 `report.md:13,43–49,55,101,116–124` | 基本满足，见 N3 |
| 审查来源可追溯 | `reviews/` 下有 subagent 原文、prompts，以及 Claude 额度失败证据（`g1-g4-h20-adoption.json`、`claude-availability-20261023.json`） | 满足，索引需补全（N2） |
| G5 为 APPROVE 或 APPROVE_WITH_NITS | 本审查 | APPROVE_WITH_NITS |

## BLOCKING

无。

## 收尾条件（本批准沿用到最终包的前提）

1. **只允许以下变更：**
   - 新增本轮 G5 提示词和本输出，署名"Claude (claude-opus-5-5) G5"。处理记录写明 G1–G4 是 subagent 审查、G5 是 Claude 审查，Claude 额度恢复不使前述结论失效。
   - 同步状态字段（见 N1）。
   - 采纳下列 NIT 中只复述既有事实或数字的文字修改。
   - 重新生成 SHA256SUMS 和 ZIP。
2. **以下内容必须与候选一致：**
   - `data/raw/`、`data/cache-fix/`、`evidence/`、`configs/`、`patches/` 以及启动和压测脚本不变。
   - `summary.csv/json`、`output-comparison.json`、`h20-acceptance.json`、`cache-fix-acceptance.json` 的非时间戳字段与候选相同。
   - 优先不重跑审计；如果重跑，要逐字段比较。
3. **保存差异与校验输出：**
   - 列出候选（958 个 payload）到最终包的文件差异：新增、修改、删除的文件及新旧 SHA。
   - 保存最终 SHA256 和 ZIP CRC 的完整校验输出。
   - 在 AGENTS §6 记录最终 ZIP 的 SHA。
4. **何时不能沿用本批准：** 任一步校验失败，或出现新数值、新归因、统计脚本改动时，不能沿用本批准，需要对这部分增量做一次小范围复审。

以上全部满足后，才能把 `goal_complete` 设为 true。

## NON-BLOCKING

- **N1 状态同步（收尾时必须做）**
  - 需要更新的位置：`report.md:3`；`completion-audit.md:1`（标题里的"待独立审查"）、`:15`、`:18`；`experiment-status.json:2–3,30,33–34,48–49`；`delivery-audit.json:934–959`；AGENTS §1.1、§6 和 `report/project-instructions-snapshot.md`。
  - `experiment-status.json:43,45` 和 `delivery-audit.json:959` 指向的 `g1-g4-h20-adoption-status.md`、`blocked-audit.md` 应标为历史记录。
- **N2 审查索引补全**
  - `experiment-status.json:35–42` 漏列 `subagent-g2-rgb-20261023.md` 和 `subagent-g4-selection-precheck-20261023.md`。
  - `completion-audit.md:17` 漏列 `subagent-g2-rgb-20261023.md`、`subagent-g4-20261023.md`，以及最关键的 `subagent-g4-cache-fix-data-20261023.md`。
  - 交付目录 `reviews/prompts/` 中没有 `subagent-g2-rgb-followup` 和 `subagent-g2-full-replay` 对应的提示词（项目根目录的 `reviews/` 我没有查）。这两份结果也没有写接替原因和额度失败证据的指针（AGENTS 3.2.1 要求）。建议在处理记录中补齐这些元数据；如果它们是对同一 agent 的续问，补存续问原文。
- **N3 补一个四问小节，并在原句处限定吞吐结论**
  - 建议在报告中加一个短节，只复述已有内容：
    1. 官方代码能否运行、跑通了哪些机制。
    2. 收益与退化：EPD 在 8 个点上吞吐均低于基线；TTFT P95 在 C1/C4 变差、C8 略好；E2E P95 除 qjh003 的 4/4 外都变差。SpaceServe 吞吐收益最明显的点 TTFT P95 明显变差：4090 4/8 为 1250.2→2146.5 ms，L20 4/8 为 1333.3→1977.8 ms（启用 mask 时 1696.7 ms），但 TPOT 和 E2E P95 改善。
    3. 限制来源：兼容性（cuBLAS 已解决；4090 不支持 SM mask）；通信（H20 数据正确，但没有做开销归因；sapphire3 损坏原因未定）；显存（没有失败，EPD 采样峰值更高）；结构与调度（单解码卡对三副本，Ray 和逐块提交的影响未定量）。
    4. 下一轮：先做 profiling 和 PD 基线，再决定是否扩大。
  - `report.md:55` 的"6 个配置中有 4 个高于基线"里，有 3 个点的差值与重复标准差同量级（n=3）：1/4 为 +9.5 对 sd 10.1，1/8 为 +14.6 对 sd 12.5，4/4 为 +2.0 对 sd 2.7。只有 4/8 的 1.08× 明显超出波动。L20 1/1 的 1.01× 也在波动内。建议在原句处直接限定。
  - 如果采纳这一条，只能复述 report.md 和 summary.csv 中已有的数字。
- **N4** `report.md:26,41,66,82` 的图片链接是本机绝对路径，ZIP 解压到别处后会失效，需要先运行 `make_report.py`（`README.md:96`）。建议改成相对路径。
- **N5** `report.md:92` 的 baseline-epd-l20 计入了 12,000 条有效测量，也列在显存表中，但它对应的 EPD 只作诊断，不支撑任何 EPD 结论。建议加脚注说明。
- **N6** `h20-final-script-provenance.json:2` 只比较了原始运行的脚本快照与现行脚本（17 个中有 8 个不同，差异见 `h20-final-replay-differences.diff`）。它不覆盖缓存补测实际执行的以下脚本：`baseline_server.py`、`start_server.sh`、`run_matrix.sh`、`apply_epd_compat.py`、`rgb_cache.py`、`check_rgb_cache.py`、`run_cache_fix_h20.sh`。如果 `cache-fix-acceptance.json` 已记录这些执行版本的 SHA，在 README 或 provenance 中加一个指针；否则如实披露。补测的公平性依据是 16 份运行时缓存快照，这一条只影响可复现性。
- **N7** `README.md:46` 建议明确写出：整合版 `run_epd_h20.sh` 本轮没有端到端执行过。
- **N8** 最终打包前，主执行者对完整 payload（含日志、jsonl、diff、patch）再做一次凭据特征扫描，只记录扫描结果。本审查按约定没有扫描日志。

## QUESTIONS

- **Q1** Glob 显示 `outputs/reproduction/reviews/prompts/g5-final-delivery.md` 已在交付目录中，但提示中说本轮 G5 提示词目前只放在交付目录外的项目 `reviews/`。这个文件是否属于候选包的 958 个 payload，还是早期草稿或候选生成后新增的？我不确定。如果是后来新增的，"候选 SHA 创建后未改 payload"只对清单内文件成立，需要在收尾条件 3 的差异清单中列出。最终包必须收录本轮实际使用的 G5 提示词。
- **Q2** 两份 G2 续审的提示词在哪里（见 N2）？
- **Q3** `cache-fix-acceptance.json` 是否记录了补测实际执行脚本的 SHA（见 N6）？

## 能否完成既定目标

**可以。** 就我读到的材料，G5 以外的完成标准都有独立证据或已获 Gate 批准，本次 G5 为 APPROVE_WITH_NITS。主执行者完成收尾条件 1–4 并校验通过后，即可宣布目标完成。PD 基线、规模扩展和全量消融不在本轮范围内，不作为阻断。