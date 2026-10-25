# AGENTS.md — SpaceServe / EPD Disaggregation 小规模复现

本文件写给 Codex。Codex 是本项目的**主导执行者**；Claude（通过本机 Claude Code CLI 调用）是优先使用的**独立审查者**，Claude 额度耗尽时由独立 subagent 接替。Codex 负责计划、编码、跑实验、写报告；审查者只读审查，不改代码、不跑实验、不碰 GPU。

---

## 0. 称呼

请叫我睿总。

---

## 1. 当前目标

**在 qjh003 和 qjh005 两台 H20 机器上完成 EPD Disaggregation 小规模复现，与已有 SpaceServe 的 4090/L20 实验一起，形成可信、可重复的实验报告。**

不要求达到论文 A100 上的加速倍数；允许结果无加速或出现退化，但结论必须有原始数据支撑。

### 1.1 已有成果与机器状态

| 机器      | 硬件                    | 用途                    | 状态                                                         |
| --------- | ----------------------- | ----------------------- | ------------------------------------------------------------ |
| sapphire1 | 8×RTX 4090 24GB，无 P2P | SpaceServe 主测         | 已完成，结果保留                                             |
| sapphire3 | 8×L20 48GB              | SpaceServe 趋势验证     | SpaceServe 已完成；纯 CUDA 跨卡拷贝数据损坏，裸机同时存在 DMA-FQ 配置，但尚无维护前后对照证明因果；EPD 的 1,800 条记录仅作诊断 |
| qjh003    | 8×H20，约 96GB/卡       | EPD 全矩阵              | 原3600+缓存修正补测600条正式已归档；最终选用3600条；G1–G5通过，B1关闭；数据与交付目录完整性核验通过，全部完成 |
| qjh005    | 8×H20，约 96GB/卡       | EPD 低/高负载点独立复测 | 原1200+缓存修正补测600条正式已归档；最终选用1200条；G1–G5通过，B1关闭；数据与交付目录完整性核验通过，全部完成 |

固定版本：SpaceServe `66de079af423`，EPDServe `9b111f710dfb`。只做运行所必需的最小兼容修改，补丁单独保存。

### 1.2 工作内容

**① 环境与机制验证**（对应 G2、G3 审查）

- 固定官方代码、模型和主要依赖，解决已定位的 H20 cuBLAS 兼容问题。
- 两台机器**分别**验证：CUDA P2P、原生 embedding/KV 传输（含数据一致性校验）、冷启动及**重启后**的并发正确性。
- 保存版本清单、补丁和校验记录。

**② 双机分工**

- qjh003：EPD 全矩阵。
- qjh005：独立复测低负载与高负载点，验证趋势。
- 每台都在单机内运行 E:P:D=1:1:1，与**同机、同三张 GPU 上的三个完整模型副本**（客户端均衡分发）比较。

**③ 实验设置**（不得私自改动，需改须先经独立审查并由用户确认；审查者按第3节选择）

- MiniCPM-V-2_6，FP16，TP=1，关闭动态角色切换与请求内编码并行。
- 沿用固定 COCO 子集、预处理和提示词，目标输出 128 tokens。
- 每配置预热 20 请求，正式 100 请求，重复 3 次。

| 机器   | 每请求图数               | 并发    | 配置数           |
| ------ | ------------------------ | ------- | ---------------- |
| qjh003 | 1、4                     | 1、4、8 | 6 × (EPD + 基线) |
| qjh005 | 1 图/并发 1；4 图/并发 8 | —       | 2 × (EPD + 基线) |

- 基线与 EPD 使用相同请求序列和缓存条件。

**④ 指标与交付**

- 指标：吞吐、输出 tokens/s、TTFT、TPOT、端到端延迟 P50/P95、采样峰值显存、失败率、三次运行波动。
- 交付：启动与压测脚本、环境清单、必要补丁、逐请求数据、对照图和报告。
- 报告合并 SpaceServe（4090/L20）与 EPD（H20）结果，两套系统各自与自己的基线比较，不做跨 GPU 绝对排名。
- 保留 sapphire3 失败记录，在报告中明确标为诊断用途。

### 1.3 SpaceServe（已完成，供报告引用）

Qwen2-VL-2B-Instruct，FP16，TP=1，与同版本原生 vLLM 同卡对照。本轮不再重跑，除非 G4 审查发现数据问题。

## 2. 执行边界（硬性）

- 只使用确认空闲的 GPU；**绝不终止他人进程、不重启共享主机、不改内核/IOMMU/驱动**。
- 环境、模型、缓存、临时文件只放专属数据盘目录（sapphire1 `/mnt/data`、sapphire3 `/mnt/data3`、qjh 机器上的专属目录），不清理他人文件。qjh005 没有可写数据目录前，不在系统盘或他人目录下凑合。
- **凭据**：绝不把密码、token 写入任何文件、脚本、日志、commit 或 review 提示词。需要 sudo/权限时停下来请用户或管理员处理。
- 本轮不做：跨机阶段拆分、通信层重写、论文全量消融、DistServe 基线、自动资源搜索。
- "服务启动成功"≠复现成功。机制必须有实际运行证据（设备放置、SM 划分生效、传输数据一致性等）。
- 无法完成的部分标为"未完成/受阻"，并附可复现的失败证据。

## 3. 独立审查流程（Codex 主导，Claude 优先，额度耗尽时 subagent 接替）

### 3.1 何时必须请求审查（Review Gates）

| Gate          | 时机                                                         | 独立审查重点                                                |
| ------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| G1 计划       | 开始新阶段 / 换机器 / 改实验设定前                           | 是否偏离目标、基线是否公平、边界是否被遵守                   |
| G2 代码与补丁 | 新增或修改启动脚本、压测脚本、对官方代码的补丁后，**在正式跑实验之前** | 正确性、是否引入不公平优势、补丁是否最小、是否泄露凭据       |
| G3 预检结果   | P2P/IPC/embedding/KV 传输探针、冷启动与重启后并发正确性检查完成后 | 证据是否足以证明机制可用、数据一致性检查是否覆盖充分         |
| G4 数据与结论 | 每批正式数据跑完、报告更新后                                 | 数据是否支撑结论、异常值/失败率处理、是否混入 sapphire3 等不可信数据、统计口径 |
| G5 交付       | 宣布目标完成或受阻前                                         | 对照完成标准逐条核对                                         |

小改动（拼写、注释、日志格式）不需要审查。

### 3.2 如何调用 Claude

用 Claude Code CLI 的非交互模式，限定为只读工具：

bash

```bash
mkdir -p reviews
claude -p "$(cat reviews/prompts/<gate>-<topic>.md)" \
  --allowedTools "Read,Grep,Glob,Bash(git diff:*),Bash(git log:*),Bash(git show:*),Bash(ls:*),Bash(wc:*),Bash(head:*),Bash(tail:*)" \
  --output-format text \
  > reviews/$(date +%Y%m%d-%H%M)-<gate>-<topic>.md
```

- 提示词先写到 `reviews/prompts/`，再调用，方便追溯。
- 若 Claude 明确返回额度耗尽（例如 `usage_limit_reached`、session limit），记录错误并告知用户，按3.2.1由独立subagent接替，不因等待额度恢复而停止可由其完成的审查。
- 若 `claude` 不在PATH或因其他原因失败，记录实际错误，不将普通HTTP429等同于额度耗尽；适用本次额度接替规则之外的故障，不能擅自推断为已获替代授权。**任何接替均不跳过审查直接进入下一Gate**（G1/G2/G5必须取得有效审查结论；G3/G4可先继续非破坏性工作，但结论须待审查后再定稿）。
- 单次审查超时上限 15 分钟；大范围审查拆成多个小审查。
- PowerShell 下使用 UTF-8 提示词文件管道传入 `claude -p`，可用 `--output-format json` 保存结果和 session_id；不要改 Claude 登录配置或设置 `ANTHROPIC_*` 环境变量。
- 本文件引入前已经启动的实验如实记录启动时间与审查缺口，补做相应范围的只读审查；不得伪造事前批准。是否需要重跑依据审查发现的数据或实现问题决定。之后的新阶段和实质脚本变更仍按 G1/G2 事前审查执行。

### 3.2.1 Claude 额度耗尽时的 subagent 接替

- 用户已明确授权：Claude额度耗尽时，立即使用独立subagent接替尚未完成的审查，无需再次请求接替许可。
- subagent仅承担审查，不接管主执行者职责；同样只读，不改代码、不运行实验、不访问GPU、不发送外部消息、不读取凭据。不得让实现某项变更的同一个subagent自审该项变更。
- 提供当前目标、对应Gate、实际文件和原始证据，以及已知疑点；尽量使用独立上下文，避免复制含凭据的聊天历史。沿用3.3的结论格式和3.4的处理规则，不以主执行者自审替代独立审查。
- 在 `reviews/` 保存提示词、审查结果和处理记录，标明实际审查者、agent标识、审查范围、接替原因及Claude额度失败证据。不得将subagent的结论标成Claude结论，也不得补写不存在的事前批准。
- subagent在对应Gate的有效结论与Claude结论按同一标准处理；G5仍须APPROVE或APPROVE_WITH_NITS，BLOCKING必须解决或按3.4提供证据并重审，实验设定变更仍需用户确认。
- Claude额度恢复不使已有有效subagent审查失效，也不要求仅为更换审查者重跑实验；如需复核，明确新增范围和原因。若subagent也不可用，如实记录阻碍，仍不能跳过Gate。

### 3.3 审查提示词模板

markdown

```markdown
你是本仓库的独立审查者，只读，不要修改任何文件，不要运行实验或访问 GPU。
项目背景与边界见 AGENTS.md，请先阅读。

## 审查 Gate
G<n>：<计划/代码/预检/数据结论/交付>

## 本次变更
<一句话说明做了什么、为什么>
相关文件：<路径列表>
相关 diff：git diff <base>..HEAD -- <paths>
相关数据/日志：<路径>

## 请重点检查
1. <具体问题，例如：基线与 EPD 是否使用完全相同的请求序列和缓存条件？>
2. ...

## 输出格式
- 结论：APPROVE / APPROVE_WITH_NITS / REQUEST_CHANGES
- BLOCKING：必须修复的问题（文件:行号 + 理由 + 建议）
- NON-BLOCKING：建议改进
- QUESTIONS：需要 Codex 或用户澄清的点
不确定的地方请明确说不确定，不要猜。
```

### 3.4 处理审查结果

- **BLOCKING**：必须修复，或在 `reviews/` 对应文件末尾写明不采纳的理由（附证据）。修复后对相同范围再审查一次。
- **NON-BLOCKING**：自行判断，采纳与否简要记录。
- **分歧**：同一问题来回两轮仍无共识时，停下来把双方观点和证据整理给用户裁决，不要单方面推进。
- 审查者指出的问题若涉及用户已确认的实验设定（模型、负载矩阵、基线定义），不要自行改设定，交给用户决定。
- 每次给用户的进度汇报中，列出本阶段审查结论（APPROVE / 未解决的 BLOCKING 数）。

## 4. 目录约定

```
outputs/reproduction/
  scripts/      启动、压测、预检、下载脚本
  patches/      对官方代码的补丁（每个补丁附说明）
  configs/      版本与依赖清单、每次运行的完整配置
  data/         逐请求原始数据（按 机器/系统/配置/重复 分目录）
  logs/
  report/       报告与对照图
reviews/
  prompts/      发给 Claude 或接替 subagent 的审查提示词
  *.md          标明实际审查者的审查输出 + Codex 的处理记录
```

## 5. 完成标准

- 两台 H20 上通信数据一致、三阶段链路及并发正确性（含重启后）均有通过证据；
- 公平基线与 1.2 ③ 中约定的双机矩阵全部完成，结论可由逐请求数据复算；
- G5 审查结论为 APPROVE 或 APPROVE_WITH_NITS；
- 审查者可为Claude，或按3.2.1在Claude额度耗尽时接替的独立subagent；必须保存真实审查来源，不能省略Gate。
- 报告分别回答：官方代码在当前硬件能否运行、跑通了哪些机制；哪些负载有收益/退化；限制来自显存、通信、兼容性还是调度；下一轮是否值得扩大。

## 6. 文档维护与落实记录

- Codex 可以根据已核实的证据维护本文件；用户确认的目标、实验设定、执行边界和审查门槛不能通过改文档自行放宽。
- 每次实质项目变更，在本节追加日期、变更与原因、涉及文件或证据、实际验证结果、审查状态及下一步；同一工作批次可以合并记录。小的文字修正可随批次记录。
- 状态表只写已核实的状态，区分运行中、已归档、数据审计通过和 Claude 审查通过；实验记录与最终结论分开。
- 大段日志、逐请求数据和审查正文存入项目相应目录，本文件保留相对于当前项目根目录的索引。当前项目根为 `D:\Documents\codex\2026-10-23\new-chat-2`；切换项目时须明确记录新根目录，不能将本项目状态套用到其他项目。
- 完成每一批工作时核对本文件、`outputs/reproduction/report/experiment-status.json` 和实际证据是否一致；未完成项写明下一步，不以计划代替验证结果。
- 记录中不保存任何凭据。目录权限已在此前用户明确授权下解决；这不构成未来任意 sudo 操作的授权。

### 2026-10-23：采用持续维护的项目执行文档

- 变更：按用户要求，将本文件作为后续项目执行与调整记录；保留 Claude G1–G5 只读审查要求，补充状态更新、证据索引和落实规则。
- 已落实：两台 H20 专属目录均可用；固定官方 EPD 版本与模型。仅将环境中的 cuBLAS 升至 `12.4.5.8` 解决已复现的 FP16 SIGFPE，基线与 EPD 使用相同环境；torch 的旧版依赖声明与实际加载版本差异已在实验说明中披露。
- 验证：两台均通过六方向纯 CUDA P2P、原生 KV 与 embedding 数据一致性、四组 FP16 矩阵运算检查；各 45 个服务正确性案例覆盖冷启动及重启，固定案例的输入/输出 token 与基线一致。qjh005 额外通过实际缓存规模的三次 KV 传输及 1,200 条正式请求审计。
- 证据：`outputs/reproduction/evidence/qjh005/`、`outputs/reproduction/report/qjh005-acceptance.json`、`outputs/reproduction/data/raw/qjh005/`；qjh003 运行完成后按相同结构归档，不提前宣称验收通过。
- 结果范围：qjh005 两点吞吐约为同机三副本基线的 0.93×、0.95×，正式请求失败率为零；固定正确性用例通过不代表所有正式生成输出逐 token 相同，最终报告须分别统计。
- 审查状态：上述实验启动早于本文件在本轮提供与读取；尚无 Claude 批准。补做已有计划、脚本、预检及已归档数据的审查，最终交付仍须 G5 批准。
- 下一步：完成 qjh003 剩余基线与实际缓存传输检查，归档并审计；合并统计和报告，处理审查意见，最后核对完成标准。

### 2026-10-23：双 H20 归档通过，独立审查受额度限制

- 验证更新：qjh003 十二个配置全部完成，3,600 条正式请求已归档；两台合计 4,800 条。`outputs/reproduction/report/h20-acceptance.json` 两台均通过，每台包含实际 60,553 blocks 缓存规模的三次 KV 复制，共各 39 次 KV 校验。结束采集时，两台 GPU 计算进程列表均为空。
- 离线核对：含历史材料共 7,200 对正式请求的图片顺序及处理后输入 IDs 一致，6,416 对输出 token IDs 完全相同；其中旧 sapphire3 EPD 仍仅为诊断，不能混入性能结论。见 `outputs/reproduction/report/output-comparison.json`。
- 分析脚本：`outputs/reproduction/scripts/summarize.py` 仅增加图表上方留白，避免 TPOT 点被边缘截断；不改变统计值和实验协议。
- 审查尝试：`reviews/prompts/g1-g4-h20-adoption.md` 限定只读，CLI 结果保存于 `reviews/g1-g4-h20-adoption.json`；未授权工具调用被拒绝，未修改实验。CLI 最终返回 `usage_limit_reached`、HTTP 429，提示上海时间 12:50 重置，没有给出审查结论。调用记录显示总耗时超过本文件 15 分钟上限，记为流程偏差；后续缩小单次审查范围并显式控制超时。
- 未完成：G1/G2 补审、G3/G4 独立审查及 G5 尚未通过；BLOCKING 数未知。仅继续非破坏性离线分析与材料准备，不能宣称目标完成或跳过审查门槛。

### 2026-10-23：离线汇总与待审查材料

- 变更：`outputs/reproduction/scripts/make_report.py` 合并双 H20 与 SpaceServe，分开统计5,400对有效测量与1,800对诊断配对，并明确标注报告草稿及待审查状态；`scripts/verify_delivery.py` 将独立审查和剩余要求写入技术审计结果，避免 `passed` 被误解为目标完成。
- 验证：十一矩阵、46配置、13,800正式请求及920矩阵内预热通过离线技术核对，其中12,000条测量有效、1,800条仅诊断；134个历史及H20固定服务案例已按范围核对，不代表全部图片语义质量通过。两张H20对照图已人工查看，图中数据和标记未被截断。
- 结果：qjh003六个配置吞吐比为0.89–0.99×，qjh005两点约0.93×/0.95×，相对于各自同机三副本基线均无吞吐加速；两台新增正式请求失败率均为零。显存、延迟与输出差异见报告草稿，不能只选有利指标。
- 索引：`outputs/reproduction/report.md`、`report/summary.csv`、`report/delivery-audit.json`、`report/completion-audit.md`、`report/experiment-status.json`；提示词及额度失败记录另复制到交付目录 `reviews/`。本文件快照保存在 `report/project-instructions-snapshot.md`，原文件仍为维护入口。
- 状态：`goal_complete=false`；只准备标明待审查的材料包与完整性校验，不发布为最终验收包。下一步仍须恢复Claude审查，处理发现并取得G5批准，再生成最终归档。
- 目标同步：`outputs/reproduction/goal.md` 已补充本文件要求的Claude G1–G5审查及G5批准标准，不改变模型、负载、基线或性能目标。

### 2026-10-23：缩小审查范围并披露首配置缓存疑点

- 版本核对：17个H20相关脚本的双机归档快照逐字节一致，其中13个与当前交付版一致；四个准备/流程脚本的整理差异已输出到 `outputs/reproduction/reviews/h20-replay-differences.diff`，清单见 `report/h20-script-provenance.json`。从两台远端只读取回实际watch与collect辅助脚本，补全 `evidence/<host>/execution-helpers/`。
- 新证据：根据原始请求及已核对的无淘汰RGB缓存源码，首个单图/C1配置全局20条预热后，EPD端COCO图片覆盖20张，三副本基线分别7/7/6张；首次正式重复会遇到40个未预热的“副本/图片”组合。后续配置继承已填充缓存。这是覆盖推演，未直接测量缓存命中率或额外耗时，不据此定量归因。
- 处理：`scripts/make_report.py` 删除“相同缓存条件”的过强表述，披露相同请求/缓存实现策略下初始覆盖并不完全相同；报告和技术审计标签不再被解释为公平性已批准。记录位于 `reviews/h20-fairness-facts.json`、`reviews/h20-cache-note.md`，状态与完成核对加入这一待审查问题。没有改预热数量、删除首重复或自行补测。
- 审查准备：将原先范围过大的补审拆成 `reviews/prompts/g1-h20-plan-focused.md`、`g2-h20-code-focused.md`、`g3-h20-mechanism-focused.md`、`g4-results-focused.md`；仍待Claude额度恢复后逐项审查，必要时按G1/G2与用户约束决定最小修复或补测。原始G1–G4尝试没有形成审查结论；BLOCKING数未知。
- 当前状态：本轮新增证据与待审查材料，不是验证等待中的活进程；此前Claude进程已终止且无批准。目标继续为未完成，G5门槛不变。

### 2026-10-23：复核额度仍受限，记录执行受阻

- 实测：最小CLI可用性检查退出码1，HTTP429、`usage_limit_reached`，仍提示上海时间12:50重置；原始结果见 `outputs/reproduction/reviews/claude-availability-20261023.json`。该调用未读取文件、未调用工具且已终止，不是审查批准或活进程等待。
- 核对：既有待审查包764文件SHA256及ZIP CRC通过。本数字对应本次状态记录更新前的包；更新后的材料重新生成完整性清单，不改变原始测量数据。
- 状态：同一外部阻碍连续三个目标轮次存在，现有可独立完成的归档、分析与审查准备已完成；持续目标执行状态标记为blocked，`goal_complete=false`。G1/G2/G3/G4/G5均未获批准，BLOCKING数未知。审查入口自身不可用使G5无法执行，此处仅如实记录执行受阻，不伪造G5批准或放宽完成标准。
- 下一步：额度实际恢复后完成分项审查，先处理缓存覆盖公平性疑点，再依审查决定最小修复或补测，最终必须取得G5批准。未创建后台自动重试或新的实验。

### 2026-10-23：用户授权额度耗尽时由 subagent 接替

- 用户新要求：Claude额度耗尽时，使用subagent接替。已更新第3节及相关表述，明确无需重复请求接替许可，但只读边界、G1–G5、BLOCKING处理和用户固定设定均不放宽。
- 历史记录保留：此前Claude的额度错误和受阻状态是真实历史，不改写为已通过审查；后续subagent结论必须单独署名并保存证据。
- 落实：当前已有明确的 `usage_limit_reached` 证据，可按此规则交由独立subagent继续待完成审查，不必等待Claude额度恢复。项目仍未完成，实际Gate状态以审查结果为准。
- 本轮执行：已以独立上下文安排 `/root/fallback_g1_g2`、`/root/fallback_g3`、`/root/fallback_g4` 进行只读接替；提示词与任务安排见 `reviews/prompts/subagent-handoff-20261023.md`。G1为APPROVE_WITH_NITS；G2/G4为REQUEST_CHANGES，共享首配置RGB缓存公平性BLOCKING一项，原文分别存于 `reviews/subagent-g1-g2-20261023.md`、`reviews/subagent-g4-20261023.md`；G3尚待最终结论，G5未审查。
- 已采纳处理：报告在低负载表行及趋势旁标注原协议观察与公平补测待完成，不删除原始重复。下一步的纯RGB初始化须保持全局20推理预热和100正式×3，经G2复审后成对补测两台单图/C1；G1/G2审查已确认这是落实既定缓存公平要求，无需额外推导确认流程。实际补丁尚未实施，不能将建议当作实现批准。
- 最终接替结果：G3也已返回APPROVE_WITH_NITS、BLOCKING为0，原文存于 `reviews/subagent-g3-20261023.md`。当前G1/G3通过并有建议，G2/G4共享一项未解决BLOCKING，G5未审查；不再因Claude额度停止独立审查。处理记录见 `reviews/review-followup-20261023.md`，交付目录同步留存。
- 验证与范围澄清：新增离线检查确认全部14,720条预热/正式响应的token时间戳有限且非递减，见 `outputs/reproduction/report/timestamp-order-audit.json`。60553为缓存分配规模、每次实际传18 blocks；服务证据支持首次启动与一次重启，不称两次重启。未改变原始数据、推理预热数量或模型设置。

### 2026-10-23：准备缓存公平性最小修复与定点补测

- 代码：双方EPD适配器启动阶段预载同manifest的20张RGB图片，填充各自实际接口缓存；新增 `scripts/rgb_cache.py` 与 `check_rgb_cache.py` 对实际RGB buffer做像素SHA核对，校验接口不执行推理。涉及 `baseline_server.py`、`apply_epd_compat.py`、`start_server.sh`。SpaceServe不启用预载。
- 运行范围：新增 `run_cache_fix_h20.sh`，复用原 `benchmark.py` 与矩阵工具，使用独立结果目录，仅两台单图/C1的EPD与三副本基线成对补测；仍为全局20推理预热、100正式×3，旧数据不覆盖。`run_matrix.sh`增加仅首负载点与独立结果根的本次必要支持。
- 验证：`work/test_rgb_cache_fix.py` 四个CPU用例通过，覆盖实际buffer变更、缺失条目、mode/尺寸及路径/重名校验。正式运行前须取得G2复审结论；提示词 `reviews/prompts/g2-rgb-cache-fix.md`。此条记录不是审批，B1在补测与G4复审通过前保持未解决。

### 2026-10-23：缓存修正补测完成，提交数据复审

- G2事前结论：独立subagent批准具体RGB修复，收尾复核为APPROVE；记录 `reviews/subagent-g2-rgb-20261023.md`、`subagent-g2-rgb-followup-20261023.md`。CPU真实API集成测试复现并修正旧插入guard的重复应用问题，连续两次补丁字节一致，未导入模型；runtime采集移至正确性后。完整复跑版四次只读cache检查另获G2 APPROVE，见 `subagent-g2-full-replay-20261023.md`。
- 实际执行：两台各完成EPD/三副本基线单图C1的600正式+40预热，任务已结束；数据在 `outputs/reproduction/data/cache-fix/` 独立归档，结束计算进程列表均为空。所有服务前后缓存20张RGB的mode、尺寸及像素SHA与独立源图一致，共16份快照；源码SHA、API PID、GPU UUID、boot ID、库路径与原协议检查通过。新增固定正确性60例，基线固定检查仅首端点，缓存与正式请求覆盖全副本。
- 选择与原始数据：全归档50配置/15000正式/1000预热；报告选46配置/13800，其中12000有效测量、1800历史EPD仅诊断，另1200旧H20低负载被补测替代。189个原归档文件哈希未变，只更新4个validity元数据，没有改写逐请求测量文件。全部16000响应时间戳有限且非递减。
- 复算与图表：源码选择器在summary及输出配对同时选择新低负载，source_case/source_kind记录来源，旧摘要保留。新增 `audit_cache_fix.py` 和 `audit_cache_continuity.py`；后者以原顺序请求、稳定GPU worker PID及无淘汰字典支持其余负载延续缓存。最终统计与图表已复算并目检，003吞吐比0.89–0.99，005低/高约0.93/0.95，未见吞吐加速。
- 分析环境：因SSH偶发断开，绘图改用本地专属 `work/analysis-env`（Matplotlib3.9.2、NumPy1.26.4），未修改共享Python或远端模型环境；Pillow12.3.0独立解码与实际RGB哈希一致。分析版本另存report/。
- 状态：G1/G3 APPROVE_WITH_NITS、G2 APPROVE；技术审计通过不替代G4，B1等待实际数据复审，G5未批准，`goal_complete=false`。下一步只做数据/报告复审、处理发现及G5，不重跑未受影响负载。

### 2026-10-23：G4实际数据复审通过，B1关闭

- 独立审查者 `/root/fallback_g4` 对四补测配置1280条记录、16缓存快照及独立RGB解码、统计/来源选择、189旧文件SHA和后续负载连续性逐项复核，结论APPROVE_WITH_NITS、BLOCKING为0，明确B1可以关闭。原文 `outputs/reproduction/reviews/subagent-g4-cache-fix-data-20261023.md`，不包含G5。
- 采纳两项建议：报告/状态/完成核对同步实际G4结论；后续缓存措辞限定为持续脚本、稳定worker PID和无淘汰字典所支持的覆盖推演，不称实测命中率，不排除所有API状态变化。README补齐离线连续性审计命令及分析环境版本，patch说明区分历史与最终H20合并补丁。
- 当前G1/G3/G4为APPROVE_WITH_NITS、G2 APPROVE，未解决BLOCKING为0；G5仍待审，goal_complete=false。下一步核对候选归档并独立G5审查，批准后仅更新完成记录、重新生成报告与最终完整性包，不改原始测量。

### 2026-10-23：Claude恢复后完成G5，执行最终收尾

- 用户要求的“Claude额度耗尽用subagent接替”已落实：G1–G4为独立subagent有效审查，额度恢复不使其失效。12:50后最小可用性检查实际返回AVAILABLE；随后Claude (claude-opus-5-5) G5为APPROVE_WITH_NITS、BLOCKING为0，会话 `baf9dad2-d355-4528-b56c-02c841d6131a`，496298ms、18次只读调用，未超过15分钟，permission_denials为空。原文和实际提示词见 `outputs/reproduction/reviews/g5-claude-final-20261023.md/json` 与 `prompts/g5-claude-focused.md`。
- 收尾意见：补全两份G2实际续问及授权/额度证据指针，补四问结论和重复波动限定，明确旧L20基线的用途、补测七文件实际SHA来源和整合runner未端到端执行。均为既有事实的文字/索引更新；未修改统计脚本、启动压测脚本、数据、evidence、configs或patches。图像绝对路径保留以符合应用预览要求，README注明换目录刷新方法。
- 验证：G5候选958个payload/959 ZIP条目逐文件SHA和CRC通过；完整文本payload凭据特征扫描954文件未命中，含logs/jsonl/diff/patch/csv/txt，不将启发式检查称作绝对无凭据证明。最终候选差异及保护目录不变证明将与完整校验JSON保存到ZIP旁。
- 完成顺序：先核对收尾差异、受保护目录/统计字段不变及封包完整性，再置最终完成状态并封包复核。ZIP内本文件快照不包含生成外层ZIP后才能知道的自身哈希；最终ZIP SHA在打包后追加本文件，并保存ZIP旁最终AGENTS快照，避免哈希循环。当前仍为goal_complete=false，最终goal工具仅在全部核验通过后标complete。

### 2026-10-23：收尾验证通过并封包

- G5全部文字/索引意见已处理，Q1未执行subagent草稿属于候选958个payload，实际Claude提示词与结论作为新增材料留存。G2两份续问由实际agent逐字回传，无伪造历史审批。
- 候选到收尾data/evidence/configs/patches/scripts全部字节一致，summary.csv/json、output-comparison、h20-acceptance、cache-fix-acceptance逐字节一致。954文本文件启发式凭据特征扫描无命中。968个payload的收尾验证包SHA及ZIP CRC全通过，见report/closeout-validation-integrity.json。
- 据此同步goal_complete=true及全部完成状态，剩余要求为空；接着对只含完成元数据更新和校验记录新增的最终ZIP再做完整差异/SHA/CRC检查。实际目标工具在最终外层校验成功后才complete。如最终校验失败，不沿用完成状态或G5批准，先修复/复审。
- 最终交付目录 `outputs/reproduction/`；最终ZIP、差异与完整性JSON均在outputs/。ZIP自身SHA在生成后追加下条，ZIP内此快照止于封包时，因此不包含外层自身SHA。

### 2026-10-23：最终外层归档校验完成

- 最终 `outputs/reproduction-h20.zip` 包含969个payload与SHA清单，共970 ZIP条目；逐文件本地/ZIP SHA与清单全部一致，完整CRC通过，外层SHA256：`3d12536a846208e3202b67650adeee2f424cc4da1bb0a6cc28c67a494941be38`。
- 完整差异为新增11、修改12、删除0；data/evidence/configs/patches/scripts全部保持候选字节，五个主要统计/验收文件完全不变。最终956个文本payload凭据特征扫描未命中；第一次954个文件是较早收尾批次的记录。全归档15000正式，最终选用13800，其中12000有效、1800诊断；旧1200低负载被替代但保留。
- 校验输出 `outputs/reproduction-h20-integrity.json`，差异 `outputs/reproduction-h20-differences.json`，外层哈希 `outputs/reproduction-h20.zip.sha256`。G1–G4为独立subagent、G5为Claude APPROVE_WITH_NITS；BLOCKING为0，所有约定完成标准已落实，无剩余工作。
- 此条为打包后追加，不能再写回ZIP内部快照，否则外层自身哈希改变。最终完整AGENTS另存 `outputs/reproduction-h20-final-AGENTS.md`；归档内快照准确反映封包时状态。目标工具此时可标complete。
