# AGENTS.md — SpaceServe / EPD Disaggregation 小规模复现

本文件写给 Codex。Codex 是本项目的**主导执行者**；Claude（通过本机 Claude Code CLI 调用）是优先使用的**独立审查者**，Claude 额度耗尽时由独立 subagent 接替。Codex 负责计划、编码、跑实验、写报告；审查者只读审查，不改代码、不跑实验、不碰 GPU。

---

## 0. 称呼

请叫我睿总。

---

## 1. 当前目标

**按用户最新确认，将剩余SpaceServe／EPD工作迁移到qjh000：不重跑qjh003已经完成的EPD方案A，完成其数据核验/分析/G4/G5；在qjh000完成Qwen2-VL-7B-Instruct FP16 TP1 eager、单H20机制验证及完整公平对照，最后完成报告和归档。**

当前补充分工（2026-10-23最新goal覆盖此前005主测安排）：后续GPU实验和远端分析优先qjh000；003的8配置2400正式+160warm已完成并抓回，不重复采集；005已有120案例profiling预检保留，准备/等待进程待000环境可用后按自有身份有序停止。000若RAID不足，用户允许其他空间充足的可写专属目录，当前选本机`/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023`，不改驱动、不碰他人任务。正式性能测量禁止其他本项目负载干扰，主机和7B选型已确认无需再问。

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

### 1.3 SpaceServe（4090/L20已完成，H20为新增批次）

Qwen2-VL-2B-Instruct，FP16，TP=1，与同版本原生 vLLM 同卡对照。4090/L20保持封存；用户最新授权在qjh005补充H20完整矩阵，见下方新增批次记录。

## 2. 执行边界（硬性）

### 第一轮完成后的后续批次

第一轮已完成并封包。2026-10-23用户要求“继续工作”后，先做只读已有H20数据的离线时延分析、事件源码语义核对和下一阶段方案准备，目录 `outputs/epd-followup/`，不覆盖 `outputs/reproduction/` 或旧ZIP。该批次不启动新GPU实验；新模型/负载/基线设置仍须按原规则独立审查并交用户确认。批次成功标准及Gate状态见其plan.md与status.json；第一轮完成状态保持不变。

- 只使用确认空闲的 GPU；**绝不终止他人进程、不重启共享主机、不改内核/IOMMU/驱动**。
- 环境、模型、缓存、临时文件优先放专属数据盘目录（sapphire1 `/mnt/data`、sapphire3 `/mnt/data3`、qjh机器专属目录），不清理他人文件。qjh005旧阶段没有可写数据目录前不在系统盘凑合。**qjh000最新用户goal明确授权例外：“数据盘不足时允许使用其他空间充足的可写专属目录。”** 该授权适用于本次已核实的`/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023`（根ext4盘854GiB空闲、boyjiang700权限），预算及清理/同步风险照常核验；不构成其他机器任意使用系统盘的授权，不需重复询问本次已给出的存储许可。
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

### 2026-10-23：用户要求继续，准备离线退化分析

- 假设与范围：第一轮已完成，不将“继续工作”默认为任意新模型、负载或PD基线的授权。先只读已有4800条H20选用请求，核对阶段事件与token时序，形成新实验具体方案；旧交付保持字节封存。
- 文件：`outputs/epd-followup/plan.md`、`status.json`；G1提示词 `reviews/prompts/g1-followup-offline.md`。当前G1待审，尚无新脚本/完整分析或GPU作业；BLOCKING数量未知。后续实现、结论与本批交付仍按相应Gate审查。

- G1后续：Claude APPROVE_WITH_NITS、BLOCKING为0；仅批准离线范围，不含GPU profiling、PD/DistServe实际搭建或远端服务。采纳来源/打点语义、首间隔分离、分位数/每重复、封存前后校验及明确G3范围建议。
- 实现准备：独立目录新增analyze.py，按旧summary来源选16H20配置；6个CPU测试通过，未运行完整数据。官方bundle+归档合并补丁在分析副本重放，16个源码文件仅api_server/llm_async两份预期变化，四份真实基线generate AST相同；源文件SHA在source/replay-manifest.json。G2代码/G3事件语义已提交，等待结果；旧包与测量不改，无新GPU任务。

- G2/G3首审：Claude G2 REQUEST_CHANGES，一项B1为目录清单未绑定封存ZIP；G3对Enum覆盖和基线通知等部分事实APPROVE_WITH_NITS，其余因Grep结果截断需窄范围补读。实际原文 `outputs/epd-followup/reviews/g2-g3-followup-offline.md/json`，696361ms，在15分钟内。
- 修复与验证：加入969条约束及固定外层ZIP内清单bytes比对，采纳-O守卫、精确矩阵、明确API字段/有符号差、布尔计数、分段异常数及输出/编码检查。9个CPU测试通过，含“目录数据与自生成清单一起改仍被固定ZIP拒绝”；首轮测试fixture的Windows换行差异已修正并保留失败日志。完整数据仍未运行；同Claude会话提交代码diff与真实源码行段摘录复审，B1在结论前保持开放。无GPU作业。

- 复审与执行：Claude G2复审APPROVE_WITH_NITS、B1关闭、BLOCKING0；G3新增CPU事件/通知范围APPROVE_WITH_NITS。实际复审 `outputs/epd-followup/reviews/g2-g3-followup-fix.md/json`。此后完整脚本退出0，16配置4800正式请求均对账旧TTFT/TPOT/E2E P50/P95；旧969文件与固定原ZIP分析前后SHA相同。独立标准库quantiles inclusive再次重新读原数据复核各case首/后续间隔及TTFT/E2E，通过；2400 EPD的decoding_begin都更靠近末通知，未观测相邻重复通知时间戳。
- 本批成果：`results/analysis.json`、`per-request.csv`、`independent-recalculation.json`、`paired-mean-differences.json`，两张图已目检；report.md限定为API观察窗口和算术差分，不作GPU带宽、利用率或调度因果。低C1平均E2E增加约128–131ms，后126间隔增加约115–119ms，首间隔约5ms，不能仅靠一次首交接解释；高4/C8基线后续间隔P99约147ms、EPD约19–20ms，仍无吞吐加速。
- 下一阶段具体方案：`outputs/epd-followup/next-experiments.md` 的A为原模型/三卡/协议下2系统×2点×启闭profiler，2400正式+160预热；B为E+P1/D2同三卡PD静态候选，官方目录未启动且涉及原边界。G4/G5离线成果及A计划G1已提交Claude，只读审查中；本批无GPU/远端服务，实际新实验仍须用户确认与实现G2。

- 离线批次最终G4/G5均Claude APPROVE_WITH_NITS、BLOCKING0；A范围G1 APPROVE_WITH_NITS。采纳引擎实现差异、EPD孤立长间隔及E/P等待未解释等限定，补齐绘图依赖命令和A的触发窗口/扰动门槛。打包版analyze在新目录完整复跑，analysis.json/per-request.csv逐字节相同；9 CPU测试及两图文件验证通过。原969文件/ZIP再验未变。
- 用户在异步确认中明确选择执行方案A，2400正式+160预热；本批离线完成不等于GPU实验完成。后续在outputs/epd-profile-a/实施，先G2、采集预检G3，再正式跑；原第一轮与离线结果封存不覆盖。qjh003现场八卡空闲、数据盘约8.2TB可用，nsys2024.6.2已安装；后续实际选择Nsight+NVTX最小观测，不改通信或驱动。

- 离线批次封包 `outputs/epd-followup.zip` 完整性通过，SHA256 `d155537944ea9095f2b1eecbd3780f57a611100aa9701b5e5617f4137d38a3f9`，58 payload，逐文件与ZIP字节一致，CRC通过；校验输出outputs/epd-followup-integrity.json。此条在封包后追加，内层快照不含自身外层哈希。

### 2026-10-23：用户明确新双机分工与完整SpaceServe矩阵

- 用户最新目标替代1.1/1.2中旧阶段分工：qjh003保留原结果并完成EPD方案A（低1图/C1、高4图/C8，启闭观测，2400正式+160预热）；qjh005改为SpaceServe H20验证。历史表及旧EPD矩阵描述仍为已完成批次，不代表新阶段分工。
- SpaceServe设置由用户目标明确：Qwen2-VL-2B-Instruct FP16 TP1，1/4图×C1/4/8，每配置20预热+100正式×3；同一H20、同MPS比较原生vLLM、解耦、有效SM划分。SM不能证明生效时第三组不验收，保留失败证据并完成前两组。
- 实测qjh005八卡均0MiB/0%且无计算进程，/local约3.5TB可用，驱动580.126.20、boot ID与旧记录相同；原目录仅有EPD环境与MiniCPM，需要独立准备SpaceServe。每次实际运行仍重新检查占用。
- 新目录outputs/epd-profile-a与outputs/spaceserve-h20；原reproduction和epd-followup目录/ZIP保持封存。新远端分别/local/boyjiang/epd-profile-a-20261023与/local/boyjiang/spaceserve-h20-20261023。
- EPD A已有G1范围APPROVE_WITH_NITS/BLOCKING0，Nsight+NVTX具体实现仍须G1/G2复核及实际采集G3。SpaceServe G1已提交Claude，尚无批准；未安装新环境或运行模型，机制均未预先宣称通过。

- 新批次G1落实：Claude首审SpaceServe计划REQUEST_CHANGES，B1要求同私有MPS独立探针与必需服务内实际stream探针，不以性能决定第三组；修改后复审APPROVE_WITH_NITS、B1关闭、BLOCKING0，会话66deb901-7eea-4bb7-aad5-f03942965a69，原文outputs/spaceserve-h20/reviews/。仅批准环境准备，未批准机制。qjh005专属目录已建，环境准备进程1050558已实测存活，固定源码正在拉取；无GPU模型作业。
- EPD观测实现验证：5项CPU单测、真实固定源码8文件全补丁compile与重复应用拒绝、真实FastAPI状态/Request注入/关闭模式拒绝capture、全320请求模拟压测（C1/C8，on/off内容相同、capture只在第3重复index84）均通过。初始模拟测试因独立临时目录前缀不同触发巨大差异计算，已仅归一化fixture文件basename并重测，失败记录保留。新远端源码独立副本已打补丁，SHA7b7ce51473ebdba1b631195153f300f725234b7eeed8035c1415624ff3c19afc，原目录不改。G1具体观测/G2审查进行中，未启动GPU预检或formal。

### 2026-10-23：用户确认SpaceServe H20主测调整为7B

- 最新目标：qjh003 EPD方案A不变；qjh005主测改Qwen/Qwen2-VL-7B-Instruct FP16 TP1 eager，用户已确认无需重复询问。先单/多图与并发正确性、共同驻留/真实CUDA并发/SM机制，再所有可用组低1/C1高4/C8，随后扩展其余四点。完整每组六点、20预热+100正式×3、128输出tokens不变。
- 新批次outputs/spaceserve-h20-7b/，远端/local/boyjiang/spaceserve-h20-7b-20261023；独立源码、环境和模型数据，复用固定版本的已下载依赖缓存，不作无关升级。旧2B材料和封存结果保留，旧SpaceServe H20准备尚未运行GPU或形成正式测量。
- 旧qjh005准备进程已实际退出：textual==8.2.8 wheel下载30秒超时，未进入模型下载/机制验证；新准备仅延长下载超时，版本不变。7B调整G1待审；MPS辅助脚本G2存在1项所有权BLOCKING，先修后实测。
- EPD：G1具体观测及G2打点/运行均由额度耗尽接替的独立subagent批准，BLOCKING0。首次GPU pilot固定标准7例+C8 8例输出token/routing正确，三GPU worker身份和库通过；capture stop控制30秒超时导致pilot未验收，清理成功，无GPU残留，20MiB nsys报告保留。正在导出诊断，不能把该失败pilot当正式请求或G3通过。
- 报告必须区分硬件迁移、模型增大和同机机制效果；争取加速但保留所有负载与无收益/退化，不能预设或捏造加速。新目标替代此前本批2B设置，旧阶段历史记录不改写。

- EPD A最新G3：/root/profile_instrument_review独立只读核对两批120原始固定案例及8 SQLite，实际API锚点/全部请求阶段/launch关联/capture边界/RGB/重启PID均通过，APPROVE_WITH_NITS、BLOCKING0。原文outputs/epd-profile-a/reviews/g3-subagent.md；实际evidence/g3-pilot-acceptance.json和results/pilot-metadata[-restart]已抓回。deviceId属进程局部编号，物理UUID取实际nvidia-smi PID映射。仅证明已测固定案例，CUDA memcpy不单独证明带宽或数据逐字节一致。
- 此后生成正式代码SHA及G3证据绑定（远端evidence/G3_APPROVED、formal-approved-code.sha256），开始qjh003正式A，PID3574036现场验证存活；首off EPD低负载已写110行（20warm+90formal的进度快照），尚未完成2400，G4/G5待审。不得将快照当最终统计，旧结果封存不动。
- 7B模型已完成15文件下载并生成SHA清单，独立依赖准备PID1164664仍在下载固定版本。无模型GPU服务；native SM通过G2后实测：私有MPS与无MPS各3次，无掩码覆盖全部78SM，掩码均被固定libsmctrl拒绝Driver API13000。首次MPS启动曾因即时GPU空闲检查拒绝，未启动daemon；重试的daemon通过PID/创建时间/nonce/pipe inode确认后干净停止，结束进程表为空。该限制属于固定库/驱动组合，不能泛称H20硬件不支持；第三组不作有效SM验收，继续前两组。
- qjh005 SCP多次握手中断，后使用已成功建立的SSH命令/持久会话63558读取状态与传输少量脚本；不因观察失败重启远端作业。一次旧脚本重试因输出目录已存在直接拒绝，原始目录保留。独立模型预取与后续installer以PID等待/文件锁串行化权重写入，未改版本或权重。

### 2026-10-23：下载期间新增qjh005 EPD采集预检，SpaceServe优先

- 用户明确授权新分工，不中断qjh003正式A。16:27现场同PID3574036仍运行，off四配置各320行（各20warm+300正式，共1200正式完成），on EPD低负载233行进度；不是最终2400验收。
- qjh005现场八卡空闲，4/5/6同NUMA1且两两NV18，CPU90–179；GPU0留给SpaceServe。7B依赖uv PID1164681持续下载，缓存由1.6增至2.0GiB；不因下载日志暂未新增而重启安装。
- 新目录`outputs/epd-profile-qjh005/`及远端`/local/boyjiang/epd-profile-qjh005-20261023`，只读链接旧005环境/权重/扩展，独立复制源码及数据/缓存。仅做两次服务启动合计120固定正确性采集案例，不新增正式性能矩阵，也不把其延迟作为加速结论。
- G1由/root/profile_plan_review APPROVE_WITH_NITS、BLOCKING0。G2首审/root/profile_runner_review REQUEST_CHANGES，两项为父MPS环境继承和无runID的私有MPS残留可能提前放锁；已修复并提交复审，未获复审前不启动005 GPU预检。CPU Linux三项互斥/让路/私有MPS替身测试PASS，首次无关/proc拒绝导致保守持锁失败记录保留，精确核实后仅清理本次CPU测试wrapper。
- 同机host flock覆盖启动、请求、采集、清理、Nsight收尾。当前Space批次environment-READY出现前后均检查优先级；监督器只TERM直接子进程组，runner按精确runID清理本次服务，残留无法确认则持锁不让路，禁止清理未知进程。被打断结果保留并标未完成。正式测量须结束另一套服务与本项目下载/安装/导出负载，确认私有MPS客户端/整卡占用后再跑。
- Space基础startup G2及native SM G3分别由/root/profile_runner_review、/root/profile_plan_review APPROVE_WITH_NITS，BLOCKING0；归档`outputs/spaceserve-h20-7b/reviews/g2-basic-startup-subagent.md`及`g3-native-sm-subagent.md`。这不代表7B实际加载或服务G3已通过；服务driver新增互斥仍在G2复审。固定库/当前驱动不支持第三组，前两组仍继续。

- 新005互斥/优先级G2复审APPROVE_WITH_NITS，前两项BLOCKING关闭；实际Linux三项测试与干净父/子MPS继承日志已被独立审查者补读通过，证据outputs/epd-profile-qjh005/evidence/。新增ready启动链亦G2 APPROVE_WITH_NITS，BLOCKING0；均不是正式测量或服务G3批准。
- 005预检PID1461356已现场确认运行，GPU4/5/6实际worker映射及cuBLAS通过，cold EPD与三副本均完成；restart正在进行。GPU0无模型服务。qjh003同PID3574036仍运行，16:32时五个配置已写满320行，第六on EPD高负载306行；仍不宣称正式A完成。
- SpaceServe已启动一次性等待链PID1512045：依赖准备成功写当前environment-READY后，EPD监督器让路；CPU安装startup-only设备记录hook，再取得共享host锁执行cold/restart服务预检。准备失败则停止，不自动跳过G3或启动formal。权重已下载；依赖缓存由2.0增至2.2GiB，仍在下载。相关脚本outputs/spaceserve-h20-7b/scripts/start_when_ready.sh，审查reviews/g2-priority-chain-subagent.md。

- 16:34后现场更新：005预检cold/restart两批均实际COMPLETED，120固定案例与8份原生trace/SQLite已抓回，自动CPU核验通过，独立G3全量审查进行中；不以弱自动parser代替审查。16:37目标四卡计算进程列表为空，Space仍未READY，uv缓存2.3GiB且准备/等待链仍在运行。证据`outputs/epd-profile-qjh005/results/`、`evidence/g3-pilot-acceptance.json`与execution.md；该预检不计入性能数据。003原PID正式A六配置1800条已完成，第七on baseline低负载进行中，未中断，不把进度快照当最终验收。

- 随后005独立G3完成：/root/profile_instrument_review APPROVE_WITH_NITS、BLOCKING0，直接原始JSON/8 SQLite全核120案例输入/输出/路由、全部请求E/P/D或baselineP/D launch关联、API锚点、完整capture边界、GPU4/5/6身份、服务重启及RGB均通过；原文摘要`outputs/epd-profile-qjh005/reviews/g3-subagent.md`。模板parser硬编码003路径的非阻塞溯源建议已通过保存初次实际适配器/来源SHA/命令、公开可独立复跑analysis/validate_precheck.py落实；CPU实际复跑通过。仅预检机制验收，不是正式性能/Space G3或整体目标完成。

### 2026-10-23：用户确认迁移剩余工作至qjh000

- 最新goal覆盖原005 Space主测安排；主机及7B FP16 TP1 eager已确认，不再请求确认。003正式A已8case各320行且global完成、PID3574036退出，共2400正式+160warm；实际原始数据/8份nsys与SQLite/运行源码/补丁/脚本/显存/控制记录已抓回`outputs/epd-profile-a/results/formal/`，远端封存tar165MiB。结束GPU表空、前后代码SHA一致。不能重跑、改来源主机或将000分析运行环境冒充003测量环境。
- 003统计脚本G2首审/root/profile_plan_review REQUEST_CHANGES，3项为逐请求与重复计时窗口、三物理GPU/显存身份、capture控制状态/请求ID；尚未正式全跑聚合，先修复重审。G4/G5未完成。
- 此前005 formal driver G2首审2项（points双层SHA绑定、准备父退出后的孤儿负载）已修并独立复审APPROVE_WITH_NITS、BLOCKING0，5 CPU guard及Linux孤儿用例通过；该批准仅旧005代码，不能直接当000新路径/驱动授权。005尚无7B模型GPU服务或正式测量。
- 000现场：8×H20 97871MiB，驱动535.161.08，实际DriverAPI12020，八卡无计算进程。RAID14T仅余15G，未使用；/var/tmp所在ext4盘余854GiB，已建boyjiang700专属`/var/tmp/boyjiang-spaceserve-epd-qjh000-20261023`并存磁盘、boot、GPU与topology证据。此路径非tmpfs；临时清理策略未知，阶段及时同步本地与SHA。用户已允许此类非数据盘专属目录，至少180GiB预算，不写home、不清他人文件。
- 本机nvcc实际12.8可用但PATH未设，13.0目录不完整；nsys2024.6.2。固定Torch2.5.1/cu124与vLLM0.7.2及libsmctrl需新环境实测兼容性，DriverAPI12.2分支不等于SM已可用；需原生及服务内实际stream证据，G2/G3后才正式测量。
- 005原prepare1164664/uv1164681及等待链1512045仍在，先将本项目GPU启动marker保存为`G2_MODEL_APPROVED-before-qjh000-migration`，防旧等待链自动启动GPU；没有终止CPU准备或改历史审查。000环境实际可用后再停止不再需要的自有准备/等待进程。官方PyPI8MiB探测实耗247秒，非可行加速路径，未因此重启下载或改版本。
- 新迁移计划`outputs/qjh000-migration/plan.md`，G1提交独立subagent；000尚未安装环境或跑GPU探针。复用权重/完整依赖缓存的复制方式正在检查，源数据/旧ZIP保持完整。

### 2026-10-23 17:54：qjh000迁移、EPD统计与原生SM实际进展

- 迁移G1经用户已授权存储范围复核后APPROVE_WITH_NITS/BLOCKING0，`outputs/qjh000-migration/reviews/g1-subagent.md`。000已完成7B共15文件复制、逐文件SHA及本地独立原始pin对比；源码Space66de079af4234b27f7f82ff91d238ef1351324ba、mysmctrl6ff57356968a3f04158b9273aa881ee6bdf04229及数据/已完成缓存均SHA验证。模型manifest为每文件固定revision，不能冒称单一共同commit。
- 000 CPU环境准备PID3361334仍在下载固定179包中的大包，不因观察超时重启。先前两次实际终止分别为cache相对symlink检查和只读Git pack重放，已保存失败日志，最小修复后才重启；未修改正在执行的准备脚本。manage独立环境已离线装psutil7.2.2。系统tmpfiles配置中的`/var/tmp`30d项是注释，仍按每阶段同步与SHA保全，不能保证管理员永不清理。
- 已核对sapphire1完整CP310 Space缓存与本批freeze SHA完全相同`12cc7ae16e15cb32a58d197b10c139df7d715a8c3eeb4246b77eebe5d4814b0f`。源UV0.12.5使用wheels-v6，000当前UV0.13.5使用v7；将完整缓存与匹配工具复制至独立cache-sapphire，禁止并发覆盖当前缓存/环境。源归档SHA`31943c861ed283ad6e95f87ef53d954d84526c8f3777c91293d40303626b0e9f`、tar完整性通过，传输PID3434667进行中。源只读HTTP629221及Windows localhost SSH relay仅服务本项目公开依赖，不复制凭据。必须离线完整验证固定依赖可用后，才能受控替代当前安装；005准备仍保留至000可用。
- qjh003正式A实际8配置2400formal+160warm均完成，000复制包SHA/CRC通过。G2聚合3项BLOCKING修复复审APPROVE_WITH_NITS/BLOCKING0，真实统计已在qjh000执行通过；原始测量仍标qjh003。`outputs/epd-profile-a/report/performance.json/csv`已有8配置真实统计。独立G4第一部分/root/profile_instrument_review APPROVE_WITH_NITS/BLOCKING0，全量原始数据及969个旧封存payload逐文件核对；CUDA关键路径与最终报告仍待审。
- 已审事实：off EPD/三副本吞吐比低0.9298189434、高0.9407783602；高EPD on/off为-5.002715819%，必须保留越5%诊断，不能说显著性或纯CUDA profiler开销。C8 capture启动时77–83仍在飞，84–99是完整选定16请求，trace不能声称仅16请求；start开销计入第三次吞吐但先于选定请求提交，stop排除。高并发存在少量有效输出token差异，不宣称全部字节一致。
- qjh000原生SM/runtime G2首审1项runID残留BLOCKING修复，复审/root/profile_runner_review APPROVE_WITH_NITS/BLOCKING0；CPU实际孤儿持锁/第二wrapper等待/外来身份不动通过，`outputs/qjh000-migration/evidence/cpu-lock-test.log`。仅批准原生SM与有限FP16探针，不批准模型或formal。
- 原生SM实际PID3457909已结束COMPLETED，GPU0 H20 DriverAPI12020，sm90二进制；无MPS和私有MPS各3次已保留stdout/stderr/exit及清理证据至`outputs/qjh000-migration/results/sm-feasibility`。首例78 SM变64，原生可行性G3已交Claude实际新审查，不能由此批准第三组；7B模型尚未启动，服务实际encoder_stream、CUDA overlap、冷启/重启正确性G3及正式G2均待完成。

### 2026-10-23 18:31：000环境实际可用、旧准备停止，SM与报告继续审查

- Sapphire完整缓存3,923,818,237字节及匹配UV0.12.5已SHA校验，独立cache-sapphire解包完成。首次普通offline解析因旧vLLM0.7.2缓存缺registry metadata失败，实际没有停止原安装，失败日志保留；随后对完整精确freeze使用offline/no-deps dry-run154包通过，才按UID/精确命令/父子关系停止000原CPU installer3361334/3363327。154包安装、pip check全兼容、Torch2.5.1+cu124/vLLM0.7.2/tf4.49导入通过，18:09实际environment-READY。未引入原在线resolver额外解析出的25个非freeze包。
- G2已批准的GPU有限FP16 probe实际通过，qjh000 boot a9617eaa-1638-45fc-8997-a62b528e8f30/API12020/目标GPU0 UUID固定，CPU参考最大绝对误差0.030937；仅运行时预检，不是7B验收。证据`outputs/qjh000-migration/evidence/runtime-probe.json`、pip-check.txt、dependency-import.txt、offline-adoption.json。
- 新环境实际可用后，按原用户goal有序停止005自有prepare1164664、bootstrap1164669、uv1164681、等待链1512045及其sleep子1917844、临时资源HTTP1629479，实际remaining=[]，只发TERM、不删数据、不碰他人。证据evidence/qjh000-migration-stop.json。005原GPU启动marker仍撤销；000以后主测，旧结果保持。Sapphire自有cache HTTP629221及Windows两个专属relay SSH49864/80308也已停止，迁移来源SHA及文件保留。
- Claude已恢复实际返回审查：000原生SM G3 session7c380db4-09f7-4607-8a3e-67849dfd43a5 APPROVE_WITH_NITS/BLOCKING0；无MPS/私有MPS各3次均78→64，模式内集合一致，零stderr、退出0。原生库与服务build/lib SHA一致529e2502f633b0d7ef07db2848c64e42154cea73992a794c27a31d0361e5e7c5。不能说12TPC或64/78资源比例；官方仅encoder mask，decoder mask注释。
- 为继承原G1布局标准，新增逐bit0–11及零mask恢复、组合0xfff校准；代码G2由同Claude APPROVE_WITH_NITS/BLOCKING0，不批准7B/第三组。helper nm-D实测无cudaMalloc/cudaLaunchKernel/__cudaRegisterFatBinary导出，仅自身入口/kernel stub，保持原链接，不加无必要flag；CPU nvcc构建通过。服务将复用实际校准同一helper二进制并核SHA。实际布局采集尚未启动，待旧MPS socket清理G2。
- 已停止的000私有MPS daemon无进程/无GPU残留，但control socket仍留在私有700目录，inode4831151/uid2147与stopped owner完全一致。新增只在host锁、已停止owner/原PID消失/无任何MPS/同UID及inode/socket类型验证后unlink精确socket的helper，真实production未动。4个Linux CPU fixture（有效、错inode、活动daemon、symlink）通过，production inode不变；G2正交Claude，不手工绕过。7B冷启/重启与实际stream探针G2亦在Claude审查，尚无7B GPU服务或formal。
- EPD CUDA CPU分析已在000实际运行通过4case/64完整选定请求/8SQLite，report/cuda-analysis.json已抓回。trace G2独立subagent APPROVE_WITH_NITS/BLOCKING0，新增4项CPU测试含同correlation跨进程隔离及GPU晚于CPU范围合法。跳过/局部deviceId/间接PID→UUID映射明确。report/report.md、throughput-latency.png/svg已生成并目视检查；事实统计G4有效，CUDA及最终报告G4新审已交恢复后的Claude，G5未完成。整体goal仍active。

### 2026-10-23 19:06：原生布局通过，7B预检格式错误已保留，EPD G4完成

- Claude再次实际返回usage_limit_reached/session limit，reset22:50，证据outputs/epd-profile-a/reviews/g4-cuda-report-claude.json及000两份G2 split JSON；额度错误和15分钟timeout都不是批准。按3.2.1由独立subagent只读接替。
- 000 SM布局G3由/root/profile_plan_review APPROVE_WITH_NITS/BLOCKING0：低12位中bit0/1/2/3/9/10/11各移除2SM，其他5位无影响；无MPS移除集合互不重叠并集14SM，组合78→64，零mask全部恢复78。私有MPS有编号映射差异，不混作物理SM位置。实际校准同一helper已复制服务build并SHA核验；仅原生G3，不是服务SM有效验收。
- 模型hooks G2与runner G2均独立APPROVE_WITH_NITS/BLOCKING0；runner B1按UID/root/runID逐目标先验及发信号前复验修复，3项CPU用例验证本run清理/其他run和外来子进程保留。首次zombie读取环境错误保留，补skip zombie后复测通过。
- 000冷启预检实际PID3757566在首次模型加载前失败：driver535空MPS的ps返回Server not found，旧parser拒绝；自动清理退出1，MPS stopped，GPU表空。失败原日志及used-scripts保留，不能称7B已加载。最小修复只在无api-pid的idle检查接受完全相同的空server响应，保存原始status；活动模型检查仍拒绝，5项CPU回归通过，复审前不重启GPU。
- EPD方案A统计、CUDA及最终报告G4均/root/profile_instrument_review APPROVE_WITH_NITS/BLOCKING0；64完整选定请求、8192 API输出及8SQLite独立复核。文字澄清已落实：共享解码曝光不能判off因果瓶颈，阶段交接解释仅待验证假设。G5/封包完整性进行中，总goal仍active。

### 2026-10-23 19:18：EPD G5发现缺口，受限处置复核；原生7B首轮正确性通过

- EPD G5首审/root/profile_instrument_review REQUEST_CHANGES/BLOCKING2：缺约定逐通知间隔同rid/同step时间归属；高EPD -5.0027158%越阈值后处置未闭环。已有统计/CUDA事实G4继续有效，不能称本批全部完成。实际首审outputs/epd-profile-a/reviews/g5-delivery-subagent.md。旧969/58payload及两ZIP独立复核未变，候选CRC/逐文件SHA通过。
- 按最新goal“不重跑已完成2400”，不擅自缩窗新增GPU采集。G1受限范围/root/profile_plan_review APPROVE_WITH_NITS/BLOCKING0：补现有trace CPU分析、高EPD仅路径存在性，明确未重采且off因果瓶颈未解释；B1新代码G2/结果G4/G5仍须完成，不能用范围复核冒充数据达标。
- 000 baseline冷启一次已实际COMPLETED，标准+C8正确性/RGB及Kineto诊断采集完成，非formal。角色切换前MPS仍有空server，status仅数字PID3819864、无ps header，parser再次保守退出；实际raw已保存。仅idle允许纯数字server列表的新delta有6项CPU回归PASS、G2复审中；加载后仍要求header与实际client。原生baseline成功证据与首次reference保留，三组/重启G3尚未通过。
- 迁移遗漏rgb_cache helper已按旧7B/封存脚本完全相同SHA02c81034681535b83e35a03ea5f34970d21b640291965d9ba73553b62bab04c7补全，CPU --help通过，/root/profile_runner_review G2 APPROVE/BLOCKING0。所有预检失败尝试保留，无正式性能数据。

### 2026-10-23 19:23：离线通知分析G2通过、000真实导出等待修复后重试

- EPD新analysis/notification_intervals.py由/root/profile_plan_review最终APPROVE_WITH_NITS/BLOCKING0：已修首→次通知冒称完整handoff、CPU候选遗漏异步GPU两项问题；完整P/首D GPU边界及含早于首通知的copy单列，CPU候选与真实prefill CUDA重叠独立筛选。5项CPU测试及实际Linux验证通过。批准后000 CPU PID3853570开始只读现有数据分析，排除高EPD数值归属；结果G4及G5两缺口尚未关闭。审查原文与范围证据在outputs/epd-profile-a/reviews/。
- 000前cold PID3841088已结束：baseline与unmasked Space实际标准/C8/RGB正确性已完成；Space首次实际编码PID3852615与创建stream 93842513032256一致。profile控制返回仅表示异步发送，旧流程过早stop服务，trace未导出，analyze_trace按缺文件拒绝，不能声称CUDA overlap或SM有效。原整个试次/首次reference/device records/日志按failed-incomplete-export保留。
- stop_server出现psutil pidfd_open EINVAL，精确runID orphan cleanup实际兜底且GPU空。停止后才改同Process对象有界poll，保留UID/root/runID全体检查与每次TERM/KILL前复验，3项实际CPU身份用例通过。新增wait_for_traces在stop_profile后等待真实worker唯一gzip、稳定size及完整CRC/EOF后才stop服务，2项CPU模拟通过。/root/profile_runner_review G2 APPROVE_WITH_NITS/BLOCKING0，返回前整体复查唯一性建议已采纳。
- 000正式driver新主机G2 /root/profile_runner_review APPROVE_WITH_NITS/BLOCKING0：清除probe/profiler，SM_EFFECTIVE实际通过才第三组，roles进入points SHA，先低/高两点全部可用组，双层SHA绑定G4后再四点，后台/外来进程/采样守卫保留。该批准仍不代表可现在正式测量；服务G3/SM及代码重冻结前置不变。
- 再冻结实际脚本/core/worker及服务SM二进制SHA后，冷启重试PID3878609现场已启动；所有先前失败保留，formal仍0，整体goal active。

### 2026-10-23 20:00：EPD受限交付G4/G5通过，000三组cold完成并启动restart

- EPD通知间隔/受限报告G4由/root/profile_instrument_review APPROVE_WITH_NITS/BLOCKING0，7SQLite独立全核6096/6096间隔、16完整交接及21个他prefill CUDA重叠，raw/source SHA不变。marker/API间隔差最大绝对值216.228073us；不声称显式stepID/依赖链、GPU物理idle或baseline API耗时0。kernel边界和kernel/copy/memset边界两处间隔口径明确。
- 同审查者G5复审APPROVE_WITH_NITS、B1/B2均关闭、BLOCKING0，仅批准当前受限EPD交付：高EPD精确-5.0027158% trace仅路径存在，未缩窗重采/原重采门槛未完成/off因果未解释均保留。原formal归档206文件与交付逐字节一致，旧969/58payload和两ZIP不变。真实复审reviews/g5-delivery-closure-subagent.md。按许可更新状态/README/报告状态句，最终SHA/CRC封包检查随后执行；总goal仍active，不标完整目标完成。
- 000 cold PID3878609已三组全部COMPLETED/退出0，5份原始gzip完整导出CRC、所有GPU清理、私有MPS stopped、code与SM二进制SHA通过。实际模型参数均FP16/CUDA0；unmasked实际encoder创建及首次stream均78SM，masked同PID/stream78→64→78→64→首次64。fork两组都观测CUDA kernel overlap，cold事实G3独立预审中，不能由此提前写SM_EFFECTIVE。
- 同冻结预检代码在GPU空闲后启动restart PID4055241，现场存活；不修改其调用脚本。cold原始包SHA39752f18b94b828f7b0bca1a8861c289479ef8d59c81b9e6b6879f53f6441f67，177条目已本地SHA核验解包。此前4次失败归档SHAcea883b8cd17a511e7a11e418d7a17043d1d0e08793c9079664bdfce6e07309e。正式请求仍0，服务最终G3及两点G4前置不变。

- EPD最终封包已实际通过逐文件ZIP/目录SHA与CRC，479payload/480entries/236452469bytes，外层SHA256 f7a35baf1c7e0e13ea1b1df65d4436efff199c5b21c876198289fbbfb2a1c094。旧969/58目录payload及两ZIP再次固定SHA通过。首轮最终检查因旧ZIP内manifest带目录前缀而停止，检查器修正后复验通过，原始说明保留，不改旧包/数据。outputs/epd-profile-a及ZIP现封存；外层完整性outputs/epd-profile-a-integrity.json，报告/归档仅代表受限EPD批次完成，总goal仍active。

### 2026-10-23 20:25：000三组机制最终G3通过，正式低/高两点启动

- /root/profile_plan_review最终G3 APPROVE_WITH_NITS/BLOCKING0，cold+restart合计90固定案例和216诊断请求均通过；原始10gzip独立流读CRC/SHA/真实CUDA overlap，restart同PID4097863/同stream再次78→64→zero78→reapply64→首次64，物理UUID与FP16真实驻留一致。helper重启后实际SHA3be03cf88212241b7b5de47673939170d5781a0fcce57839be9c9fcb194b3a1b/lib529e2502...核验，与校准一致。只验encoder mask，不声称互斥decoder/fullSIS/资源比例，LM仍有visual权重。
- restart归档SHA333026ecdfb93698bbf244f9efdcdbad2bc77d6af7904810cb007ce09492a466，161条目已本地SHA解包。真实review及G3_MODEL_APPROVED/SM_EFFECTIVE在outputs/qjh000-migration，marker只在有效G3后创建。
- 新正式统计analysis/space_results.py首审3项身份/显存/endpoint BLOCKING，按真实worker100/pipe/UUID/正组件、非空NVML/private server、逐样本PID/sum/非负bytes/精确NVML容量102625181696/单调时间、实际API命令端口与all320 endpoints最小修复；5项CPU反例测试通过。/root/profile_instrument_review复审APPROVE_WITH_NITS/B1B2B3关闭/BLOCKING0，points双层SHA和G4 bytes/audit依赖SHA保留。
- 所有实际运行脚本/fork全部Python/native worker/SM二进制/分析代码已冻结，formal清单SHA850602ca06ea42055b670c3d1b5987d58936cdd75e8e7e108d867d5e97c78f2b。GPU0空闲且无本项目准备/分析后，20:25启动正式监督器PID18837；目标三组各低1/C1及高4/C8，共1800formal+120warm，再独立两点G4后扩其余4点，总5400formal+360warm。此为启动，不把进度算验收；关闭profiler/SM诊断，保留同privateMPS/host锁及身份/污染/内存守卫。整体goal仍active。

### 2026-10-23 20:45：正式首配置采样守卫拒绝，保全后最小修复待审

- 正式监督器18837首native1/C1实际完成300formal+20warm后审计退出1；不是手工中断，也未放宽守卫。1746显存样本周期中位0.396067s、最大0.523900s，第二重复首样本晚0.310766s超过0.3s；请求全部成功/128输出、采样foreign=[]，但本次数据不选入性能对照。服务/自有MPS实际已清理，GPU进程表空。
- 原formal目录、used-scripts、实际runtime记录、旧批准SHA、日志与诊断已打包抓回，SHA042347e42b5c331cc784e9ac5fff01eb7923a314a057e5f4d0e5f4d51e445d96；outputs/qjh000-migration/results/formal-memory-failed-20261023T2038.tar.gz，独立本地CRC/EOF与逐文件读取核验记录另存evidence。不覆盖EPD/旧封包。
- 定位每次monitor整机process_iter与children递归耗时：真实主机CPU旧归属路径中位0.284316s。最小改为只针对每次NVML实际返回的各GPU PID查UID/真实root Process身份/祖先或私有MPS pipe，不缓存PID；100ms sleep、输出字段、0.3s/1s审计守卫不变。CPU新归属查询中位0.0000381s，不当作GPU吞吐或采样保证。5项Linux CPU回归PASS，测试目录最初缺失失败也保留。
- 模型/SM/正式请求设置未改，原G3仍有效；新增采样代码G2由/root/profile_runner_review按3.2.1只读接替审查中，复审前不重启GPU。通过后重新冻结源SHA、保留失败目录、从同一首配置重新跑，不复用该失败case，仍需六配置后独立G4才扩矩阵。总goal仍active。

### 2026-10-23 20:46：采样G2通过，同矩阵重新冻结启动

- /root/profile_runner_review独立从失败包复算全部1746样本与重复边界，G2 APPROVE_WITH_NITS/BLOCKING0，确认新实现保留全部NVML PID逐轮分类、身份/私有MPS和foreign失败关闭，未改0.3s/1s阈值。fixture stdout警告已修，五项CPU再次全PASS。真实review和处理outputs/qjh000-migration/reviews/g2-memory-sampler-subagent.md；不是数据G4通过。
- 旧失败目录及runtime实际隔离保留，日志另存；77文件失败包本地SHA/gzip CRC/EOF/文件尺寸核验通过。旧批准manifest另存before-memory-fix，新manifest SHAa1df0568a0982b2c66e370f7153072534309323b3c3b856fe81518a303aaf975，逐项确认仅scripts/monitor_gpu.py一项SHA变化，其余冻结源码/模型/SM/协议未变。evidence/memory-sampler-fix-adoption.json保留变更前后SHA与真实审查SHA。
- 正式监督器新PID124199已启动相同矩阵，旧300formal+20warm不复用；先三组低/高六配置共1800formal，再G4放行rest，总5400formal。MPS/host锁、诊断关闭、后台/污染/显存守卫不变，GPU实际采样周期仍须本次数据核验。整体goal active。

### 2026-10-23 20:58：新采样正式首配置通过技术审计

- 监督器124199仍存活；native1/C1完成320行、300formal+20warm，technical-audit.json实际passed。三重复显存样本1963/1972/1976，最大内部gap0.1784/0.1796/0.2373s、起始gap0.0426/0.0080/0.0806s、末尾gap0.1082/0.0535/0.0151s，均满足未修改守卫；无记录foreign。非独立G4，暂不汇总性能结论。
- native4/C8已实际进入测量；仅首6配置中的1配置技术完成。全部正式计时仍不在000分析/导出。README补齐真实启动/压测/复算入口、每文件模型pin和机制/失败限制；固定dataset从旧封存包只读复制，SHA71a483ba2a1e4e4809ac1889a0a76eb1970f60be9d445424df4d6c791bb62f26一致，旧包未改。数据取回与G4审查稿只在本地准备，尚未提交G4或创建批准marker。总goal active。

### 2026-10-23 21:02：原生低／高两配置技术完成，切换解耦组

- 监督器124199仍存活；native1/C1及4/C8各320行/COMPLETED，role也COMPLETED，合计600formal+40warm。高点technical-audit实际passed，三重复样本433/436/442，maxgap0.1741/0.1808/0.1704s，边界gap均小于0.083s；未改守卫。原生API自有身份清理完成/orphan=[]，按原driver继续解耦角色；同privateMPS和host锁未释放。
- 仍仅首六配置中的2配置技术完成；技术audit不是独立G4，尚未取回本轮数据、汇总性能或创建G4_POINTS_APPROVED。G2采样修复APPROVE_WITH_NITS/BLOCKING0，G3有效；G4/G5待全部数据。后续work/pack_space_phase.py及unpack_space_phase.py只在本地准备，须POINTS_READY暂停后、approved CPU分析结束才实际归档/同步。总goal active，不把当前进度当最终验收。

### 2026-10-23 21:17：解耦低／高两配置技术完成，转入SM组

- 监督器124199存活，unmasked Space1/C1及4/C8均COMPLETED、role COMPLETED；与native合计4配置1200formal+80warm。低点三重复显存maxgap0.1866/0.1859/0.1746s，高点0.1800/0.1769/0.1765s，均满足原采样覆盖阈值、technical-audit实际passed。解耦API清理完成，orphan=[]，继续同MPS/host锁转SM-mask角色，没有重跑或改变设置。
- 正式SM两配置尚待完成；首六配置数据未齐，不启动000 CPU分析/导出，不创建G4 marker，不公布吞吐收益。模型/SM G3及采样G2已批准/BLOCKING0，实际数据G4和最终G5仍待审，总goal active。

### 2026-10-23 21:38：首六配置齐全并暂停，真实统计与传输通过，G4审查中

- 21:32现场监督器124199存活，三组各低1/C1与高4/C8全6配置/每配置320行/COMPLETED，总1800formal+120warm；已进入POINTS_READY_FOR_G4，同私有MPS/host锁保持，所有API停，实际clients=[]、目标GPU仅private MPS server124699。没有rest或G4批准marker。
- 暂停后源代码全量SHA及points双层/payload SHA实际通过；envs/manage的approved analysis/space_results.py在000真实执行passed，report/space-points.json保留1800计数、全身份/显存/输入及输出差异key，不把技术统计当G4。CPU分析完成后才打包，199payload源postpack不变；3,234,959bytes包SHAca4d480c99ae6111b1e02ae0a6af64e0f66a2a4a4f363bdb35ac391c2679a56b已本地外层SHA/gzipCRC/EOF/逐payload SHA/完整唯一集合核验解包。
- 首次归档SSH连续Connection closed，退避后重连确认原监督器存活、tar/receipt/日志快照均未生成，仅重试CPU归档；未重启模型或重跑数据。所有运行与原始配置保持冻结清单SHAa1df0568a0982b2c66e370f7153072534309323b3c3b856fe81518a303aaf975。
- 真实report/space-points-report.md和performance-points.png/svg已由批准renderer生成并主执行者目视。输出IDs与native有低5/8、高82/85对320差异，原始文本保留，未经证据不归因FP16或称精确全一致；原生高点同图组也有多种输出。仅技术候选，不公布最终性能结论。
- 独立G4数据/root/profile_instrument_review、报告/图表/机制/root/profile_plan_review已提交，按3.2.1额度接替；审查提示/真实原始证据在outputs/qjh000-migration。两范围BLOCKING均0且有效批准后才将外层manifest原bytes写G4_POINTS_APPROVED；先结束所有000 CPU分析/导出再扩rest，总goal active。

### 2026-10-23 21:54：两点G4双范围通过，实际放行其余四点

- 数据G4/root/profile_instrument_review APPROVE_WITH_NITS/BLOCKING0：独立全核1920行、18重复/统计、22797显存样本、120完整唯一points文件、660冻结项/49used-scripts及199payload+1清单传输包。G4报告/root/profile_plan_review实际看PNG/SVG/逐表值，APPROVE_WITH_NITS/BLOCKING0；最新取舍/E2E P95/输出变化段也实际窄核APPROVE/新增BLOCKING0。原文reviews/g4-points-data-subagent.md和g4-points-report-subagent.md，SHA绑定在evidence/g4-points-approval.json。
- 主执行者采纳状态计数纠正：实际完成formal_requests=1800、completed_formal_requests=1800，独立验收数另记1800；不是把数据完成数写0来表示G4待审。首六技术1800/120/6与G4已通过分开；全矩阵G4/G5仍pending。renderer仅本地文字delta先G2 APPROVE/BLOCKING0再生成，不改远端冻结代码。
- 已审事实：高4/C8 Space/native吞吐1.0586x、mask/native1.0629x，但TPOT P50由19.27变22.03/22.21ms；mask/unmask低−0.56%、高+0.41%不证明稳定额外收益，mask高E2E P95略退化。输出IDs差异全320含warm为5/82与8/85，正式300为5/79与6/81；原生高点同输入也有变异，不归因FP16、不保证全量语义。raw和全部差异key保留，不过滤退化。
- 21:52:12先确认监督器124199存活、统计/归档进程均已结束、源SHA再次全通过；在真实双G4批准后，将points-manifest.sha256原bytes原子放成远端G4_POINTS_APPROVED，外层bytesSHA3467a90b01f3b32adddbc334599f0dde4cca4d798385ce111fa5683aaa01cd37、内层SHA78642d0259f77df19ceabb3f9fdc52965d34ef542f5e1f46f77f01ddc73887fa。原点数据和源冻结均未改。
- 21:53:52监督器仍活，points verifier实际passed，rest/native1/C4已116行，说明真正续跑；保持同MPS/host锁/模型/协议，余12配置3600formal+240warm，目标总5400formal+360warm。000计时期间再次停止CPU分析/导出，只有本地报告状态维护；整体goal active，不能以首六G4代替全矩阵验收。

### 2026-10-23 22:07：扩展矩阵技术完成8配置，交付输入逐像素核对通过

- 22:03:35实际监督器124199存活，rest/native1/C4及1/C8均320行/COMPLETED，4/C1已147行继续测量；全批技术完成8/18配置，2400formal+160warm。独立G4仍只批准首6配置1800formal+120warm，剩余全量G4/G5未验收；状态按这两个范围分开，不把新增请求当已独立批准。
- 本地正式交付dataset.tar.gz与旧封存copy外层SHA71a483...一致；迁移qjh005使用另一容器SHA b0cfbe...，不能混同归档bytes。已在本地独立读tar的同manifest与20张JPEG：manifest bytes SHAadbfff89533d4ab2bbab96cb372b47b7ba0e4790567ac480b1e0c26a39b41198、20个文件SHA、PIL解码RGB448像素SHA均与实际formal的RGB记录完全匹配，evidence/dataset-payload-match-formal.json。输入一致性已证，不是因容器SHA不同就重跑模型；两容器差异不推测为仅header，其他5个routing/captions文件随旧封存原样提供。
- 仅本地work准备了全量结束后的metadata收集与封包步骤：全量COMPLETED/监督器实际finished exit0、无本项目后台、目标GPU表、boot、两repo实际HEAD及当前累计diff/MPS stopped原owner对齐，后续才CPU复算/收回。新helper未上传执行，远端冻结源和正式设置未动；000正式计时期间无CPU分析/导出。总goal active。

### 2026-10-23 22:16：原生六负载全部技术完成，整体10/18配置

- 22:15:06实际监督器124199存活，rest/native1/C4、1/C8、4/C1、4/C4均320行与COMPLETED，rest/native角色COMPLETED，自有API清理orphan=[]。加首轮native两点，原生六负载全部技术完成；加另两组首轮两点，整体10/18配置、3000formal+200warm技术完成，独立G4验收仍仅首轮1800formal+120warm。
- driver依既定顺序继续unmasked Space的其余四负载，保持同MPS/host锁/模型/请求协议与冻结源码。没有000 CPU分析/导出、没有重启测量或新增基线。新正式数据只在全量结束后统一取回/复算/审查；全量G4/G5及最终归档仍pending，goal active。

### 2026-10-23 22:40：原生与解耦六负载技术完成，收尾helper修复待复审

- 22:39:55实际监督器124199仍运行，同一冻结源/私有MPS/锁。rest/native及rest/space均四负载和角色COMPLETED，加首轮共14/18配置、4200formal+280warm技术完成；独立G4仍仅首轮1800formal+120warm。当前继续encoder-mask剩余四负载，没有中断、重跑或远端CPU分析/导出。
- 独立subagent /root/profile_runner_review 对本地收尾helper G2给REQUEST_CHANGES、3 BLOCKING：旧目录与固定ZIP未绑定、Windows解包路径/链接逃逸、-O可关闭assert。主执行者已最小修复并采纳warm/case计数建议；4项CPU回归真实通过（含实际Windows junction与两种ZIP布局双改拒绝），同范围复审pending，尚不算关闭。reviews/g2-final-delivery-helpers-subagent.md、evidence/delivery-helper-regression.json。
- 本地只读复核旧三个完整目录和固定ZIP，969/58/479 payload、清单/归档全成员SHA/CRC绑定均通过；旧目录与封包未修改，evidence/old-seals-bound-verification.json。收尾helper尚未在000上传执行。正式全量G4/G5及最终包仍pending，总goal active。

### 2026-10-23 22:43：收尾helper同范围G2复审通过

- 独立subagent /root/profile_runner_review 只读复核后给APPROVE，三项BLOCKING关闭、剩余0，reviews/g2-final-delivery-helpers-recheck-subagent.md。4项本地CPU回归和三个旧封存包完整绑定核验均通过；源码快照与SHA保存在evidence/delivery-helper-source/。
- 该批准只覆盖收尾代码，不替代全量G4/G5/包完整性。正式作业尚运行，收尾helper尚未在000使用，不触动冻结实验代码或更改设置；总goal仍active。

### 2026-10-23 22:59：正式17/18，Claude额度恢复可用

- 22:59:02监督器124199存活，masked4/C1已COMPLETED，最后4/C4开始36条；整体17/18配置、5100formal+340warm技术完成，独立G4仍仅首轮1800+120，全量G4/G5待执行。远端未启动分析/导出，冻结源和正式设置不变。
- 已过22:50原重置时间后，实际本地Claude仅可用性检查返回READY、is_error=false，reviews/claude-availability-after-reset.json；不是任何Gate批准。后续新全量G4/G5优先Claude，之前subagent有效审查不失效，不据此重跑实验。
- 本地report/acceptance-checklist.md及全量G4/G5提示已准备，仍标待执行；整体goal active。

### 2026-10-23 23:02：用户休息期间继续自主完成

- 用户直接授权“遇到问题不要问我自己决定，继续跑下去”。主执行者继续处理本目标内的故障、必要最小修复、数据核验、独立复审和交付，不为例行选择重复询问；各项决定、证据和真实审查仍记录，不跳Gate。当前既定矩阵/模型/基线无需改变。
- 23:01:49监督器124199仍存活，最后masked4/C4已252/320行；原生/解耦/掩码前五点均完成，尚无全局COMPLETED。结束前仍不运行000 CPU分析/导出。全量G4/G5及归档验收完成前保持goal active。

### 2026-10-23 23:10：Space7B完整矩阵结束并收回，全量G4进行中

- 全局COMPLETED实际2026-10-23T15:02:44Z，监督器124199已退出，日志finished/child_exit0；18配置5400formal+360warm均技术通过。结束后才运行批准的收尾helper：boot不变、两repo固定HEAD、无本项目后台、GPU0进程表为空、MPS原token stopped。660项冻结源全OK，当前累计diff SHA93dc0519bfafce57907cfcb7e39e1644b50f8c487beeeb69ea8cc777583d6457，与交付SpaceServe-complete.patch完全相同。
- 000 CPU全量统计passed。传输包9,301,339bytes/415payload，SHAd7d75ef664e750ba87b3810ba43ccc3b06ff0f159814d28cba59a8ac9f0e6814；源postpack不变，本地外层SHA、gzip CRC/EOF、完整唯一成员集合及逐payload SHA均真实通过。原始points及其G4原bytes无覆盖冲突。evidence/formal-all-{transfer,local-integrity,payload-sha}.json。
- 全量report/space-all-report.md、final-summary.md与PNG/SVG已生成；实际目视发现全六点柱顶数字重叠，renderer仅all图数字旋转90度并重新目视通过；SM额外变化小的文字限定为首轮两点，不概括新增四负载。未改统计/远端冻结源。
- 全量显示unmasked吞吐相对原生−6.32%至+5.86%，mask相对原生−7.52%至+6.29%；新增四负载mask均比unmasked低。正式失败0、128输出，所有负值/输出差异/TTFT及TPOT退化保留，固定顺序/时间漂移和因果限制明确。实际Claude数据与报告两范围G4已调用，尚无批准；G5/最终包仍pending，总goal active。

### 2026-10-23 23:14：Claude新额度错误，独立subagent接替全量G4

- 重置后READY检查确实成功，但实际全量数据/报告两次调用随后均is_error=true、api_error=usage_limit_reached，提示reset03:50；原JSON保存reviews/g4-full-{data,report}-claude.json，没有有效批准。调用还记录只读工具权限拒绝，未将这些普通权限错误当作额度证据；接替依据是最终明确usage_limit_reached。
- 依3.2.1和用户睡前授权，/root/profile_instrument_review接全raw数据与归档范围，/root/profile_plan_review接完整报告/图表/机制与本地renderer两行delta。仅本地CPU只读，不写文件、不访问远端/GPU，主执行者保存真实结论；此前points审查不改。全量G4/G5及最终包仍待验收，goal active。

### 2026-10-23 23:24：Space全量数据/报告双范围G4批准

- 独立数据审查 /root/profile_instrument_review：APPROVE_WITH_NITS、BLOCKING0；实际独立复算5760行（5400formal+360warm）/54重复/58294显存样本。最大内部采样间隙0.237257s、窗口首尾0.124610s，全部通过；660源三检查日志、49used-scripts、points120文件逐字节和marker、415payload全SHA/gzipCRC/EOF、真实结束与清理均核验。输出差异全部key和正式/含warm计数核准，未见精确串到别输入的证据，不保证全量语义/所有路由排除。reviews/g4-full-data-subagent.md。
- 独立报告审查 /root/profile_plan_review：APPROVE_WITH_NITS、BLOCKING0，18行数值/六负载百分比/显存/实际PNG和SVG、退化及机制/因果限制均核准；renderer布局/文字delta通过。两项文字建议已落实并窄核APPROVE0，reviews/g4-full-report-{subagent,text-delta-subagent}.md。数据审查320分母建议已明确含预热0–96/320和正式0–90/300，不改raw。
- 当前全量G4已批准，G5和最终包未执行，goal active；下步按已批准helper封候选包并独立G5，最终真实SHA/CRC/旧封存不变全部通过后才目标完成。

### 2026-10-23 23:36：G5批准，按限定准备最终封包

- 独立subagent /root/profile_runner_review给G5 APPROVE_WITH_NITS、BLOCKING0，实际全读候选947432610bytes/1032payload+1清单，SHA4360ad5b7077a9642d275bee7b153f53cb3caaaf1dbc93b334d67c0c9c0bf2de；再次独立复核三旧封存969/58/479与固定ZIP绑定、raw计数/54重复/58294样本及统计/660源检查和49used-scripts/points原bytes/结束清理，均通过。reviews/g5-final-subagent.md。
- G5明确允许仅补真实审查、状态/报告页脚、AGENTS快照，再以已审helper封final；不改raw/统计/解释。元数据为最终封包内容准备，只有外置final integrity实际passed=true后才目标完成；封包失败须恢复pending并留证。根goal此刻仍active。
- 最终包SHA/receipt置封存目录外，完成后只追加根AGENTS及外置final-AGENTS，不再修改已封目录payload。
