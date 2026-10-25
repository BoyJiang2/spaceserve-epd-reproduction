> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g5-final-prompt.md) SHA256 dd7258882a43427c90352812d8ce634d713c4e73c23436d422f4c232017c403d。原数字及解释不变。

# G5 最终交付（草稿，full G4和candidate实际完成后才调用）

先读D:/Documents/codex/AGENTS.md。你是独立只读审查者，不改文件/marker、不访问远端或GPU、不运行实验。可在本地CPU读取和校验归档，但不得生成/改写交付数据。回复正文供主执行者保存。

当前用户goal：剩余工作迁移qjh000；qjh003 EPD方案A2400+160不重跑，完成核验/分析/G4/G5；qjh000 Qwen2-VL-7B FP16 TP1 eager同一H20上完成native、解耦、实际encoder-mask三组完整1/4图×C1/4/8，先两点通过G4再续其余四点。保护旧封存，可信可重复优先，不预设论文倍数，不新增PD/DistServe。

调用本稿时主执行者须补充实际full G4审查文件、candidate ZIP路径/SHA和外置receipt；没有实际文件不能批准或猜测。

核验清单：
1. report/acceptance-checklist.md逐项与goal/AGENTS/status/README/实际证据一致；完成/受限/未完成区分。Space全量18配置5400formal+360warm、原始数据和图表/脚本/依赖/权重pin/最小补丁均齐，full G4有效且BLOCKING0。
2. G1/G2/G3/两点G4/fullG4审查实际来源与范围，Claude额度失败证据/独立subagent接替准确，不能主执行者自审冒充独立批准。收尾helperG2修复3项关闭并有4CPU回归。
3. actual GPU/MPS清理、终结exit0、boot/660项冻结源/运行used-scripts/数据传输SHA/CRC/full唯一成员集合/源postpack证据；失败预检和首旧采样失败300+20完整保留且未入选。
4. 完整模型/解耦/encoder-mask机制边界和正式结果解释准确；输出变化保留，非全量逐token/语义等价，不将CPU事件当GPU因果/预检重叠当正式利用率，不夸大mask小收益或固定并发SLO。
5. EPD A已受限G5封存，不重跑也未混入Space同机结果：高EPD观测5.0027158%超阈，trace路径存在用途，不称原重采门槛通过；off低/高0.930/0.941×三副本，因果瓶颈未确定。旧4090/L20 2B和其他EPD分批保存。
6. 三旧封存目录969/58/479 payload与固定ZIP内容绑定且ZIP固定SHA未变。candidate新目录清单和ZIP全payload/CRC/唯一集合、源postpack一致，无自哈希循环。对最终G5/status纯收尾更新，允许按同已审helper重新封final并独立全读SHA/CRC；最终包验收仍由主执行者实际执行并记录，不提前伪造。

输出APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES；BLOCKING逐项文件行号+原因+最小建议，NON-BLOCKING，QUESTIONS，实际检查范围和未检查范围。不是替主执行者标goal complete或写marker。

当前最新Claude两次完整G4实际usage_limit_reached、reset03:50已保存g4-full-data-claude.json和g4-full-report-claude.json；依AGENTS3.2.1由独立subagent接替G5。不要将permission_denials本身当额度错误。全量数据/报告两个独立G4均APPROVE_WITH_NITS、BLOCKING0，文字建议均已落实并独立窄核APPROVE0。G5若批准，主执行者只补真实G5记录、最终状态及AGENTS快照，再用已审helper封final；final实际全读CRC/SHA和源postpack/旧封存复核成功后才update_goal complete。最终包SHA/校验receipt保存在新目录之外以避免自哈希循环，最终包准备过程不等于已完成声明。


## 本次实际候选包

{
  "kind": "candidate",
  "passed": true,
  "archive": "D:\\Documents\\codex\\2026-10-23\\new-chat-2\\work\\space-7b-candidate-20261023T232604.zip",
  "bytes": 947432610,
  "sha256": "4360ad5b7077a9642d275bee7b153f53cb3caaaf1dbc93b334d67c0c9c0bf2de",
  "payload_files": 1032,
  "zip_entries": 1033,
  "source_and_archive_all_payloads_match": true,
  "full_entry_crc_reads_passed": true,
  "sealed_batches": [
    {
      "directory": "reproduction",
      "payload_files": 969,
      "zip": "reproduction-h20.zip",
      "fixed_zip_sha256": "3d12536a846208e3202b67650adeee2f424cc4da1bb0a6cc28c67a494941be38",
      "directory_bound_to_fixed_zip_manifest_and_payloads": true,
      "passed": true
    },
    {
      "directory": "epd-followup",
      "payload_files": 58,
      "zip": "epd-followup.zip",
      "fixed_zip_sha256": "d155537944ea9095f2b1eecbd3780f57a611100aa9701b5e5617f4137d38a3f9",
      "directory_bound_to_fixed_zip_manifest_and_payloads": true,
      "passed": true
    },
    {
      "directory": "epd-profile-a",
      "payload_files": 479,
      "zip": "epd-profile-a.zip",
      "fixed_zip_sha256": "f7a35baf1c7e0e13ea1b1df65d4436efff199c5b21c876198289fbbfb2a1c094",
      "directory_bound_to_fixed_zip_manifest_and_payloads": true,
      "passed": true
    }
  ]
}
外置receipt：D:\Documents\codex\2026-10-23\new-chat-2\work\space-7b-candidate-20261023T232604.integrity.json

候选包已真实全读1032payload+1清单、CRC/SHA/唯一集合/source postpack和三个旧封存绑定通过；自此未改新目录payload。请独立核当前目录、SHA256SUMS及候选包，读取真实full G4与窄核结果。两个独立full G4均APPROVE_WITH_NITS/BLOCKING0，数据5760行54重复58294显存样本，报告18行6负载/图表核准。

G5若通过，主执行者保存你的真实结论、提示词及处理记录，更新G5字段/报告页脚/完成状态/AGENTS作为最终封包内容，然后使用同一已审helper的final分支。最终包实际全读CRC/SHA、源postpack和旧封存复核成功前不update_goal complete；若封包失败立即恢复pending并保留失败证据。最终包外置receipt为归档完成证据，不把准备中的完成状态当作已宣布交付。最终成功后只向根AGENTS及outputs外置final-AGENTS快照记录包SHA，不再修改已封目录，避免自身哈希循环。请明确此纯收尾范围是否可接受。
