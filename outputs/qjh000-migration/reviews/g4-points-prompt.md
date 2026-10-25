# G4：SpaceServe三组首轮低／高两点

先读同目录g4-points-prompt-draft.md和D:/Documents/codex/AGENTS.md，沿用只读/不访问GPU/不改文件/不启动实验边界。审查正文直接回复主执行者保存。Claude同批usage_limit_reached证据仍有效，按3.2.1接替。

真实数据现已齐全并收回，允许本地CPU独立复算；不是仅审代码：
- 正式监督器124199，当前在qjh000保持同MPS/锁的POINTS_READY_FOR_G4暂停，所有API已停；实际evidence/points-paused-mps.json仅private MPS server124699，clients=[]，无G4 marker，无rest。
- 三组各1/C1和4/C8，6配置1800formal+120warm，所有technical-audit及role COMPLETED。
- 实际冻结代码清单SHAa1df0568a0982b2c66e370f7153072534309323b3c3b856fe81518a303aaf975；analysis-output/points-current-code-check.txt为暂停后真实全量SHA验证OK记录，points-payload-check.txt也通过。
- 传输包work/formal-points-20261023.tar.gz，SHAca4d480c99ae6111b1e02ae0a6af64e0f66a2a4a4f363bdb35ac391c2679a56b，3,234,959bytes，199payload。源postpack不变、本地SHA/gzipCRC/EOF/逐payloadSHA与唯一member完整集合均通过，evidence/formal-points-{transfer,local-integrity,payload-sha}.json。
- points内层manifest文件SHA78642d0259f77df19ceabb3f9fdc52965d34ef542f5e1f46f77f01ddc73887fa，外层points-manifest.sha256原bytes保留，尚未创建G4批准。
- CPU统计已在qjh000真实运行通过，report/space-points.json；report/space-points-report.md和performance-points.png/svg已实际生成，主执行者目视图表无裁切，仍须独立G4核对。

已知事实必须保留：
- outputs IDs对原生有差异：Space低5/320、高82/320；masked低8/320、高85/320（含20warm）。所有输入图片序及processedinput IDs相同，128输出均成功。请抽查差异原始文本/首次分歧位置及同配置跨重复，判断是否存在路由错误证据；不能未经证明将差异归因为FP16，也不能说逐token全一致。真实fixed90案例G3仍有效，formal差异key和raw都保留。
- 初步统计低点native/Space/mask为0.4457/0.4514/0.4489req/s，高点2.0138/2.1318/2.1404req/s；只是待审数字，不是预定结论。注意高点TTFT改善同时TPOT P50变差，mask对unmask仅约0.4%，不要称显著或全面改善。
- 首旧300formal+20warm采样覆盖失败已独立保全，不复用；唯一monitor修复G2已批准且原守卫不变。model/SM G3未重做，因为源码/协议/机制未改，当前正式关闭probe/profiler。
- 归档首次SSH连续Connection closed，核实原监督器仍活着、根本没有生成tar/receipt/log快照后，仅重试归档；没有重启/重跑GPU。现归档完整性真实通过。

请按draft六类检查，但本次侧重完整数据、raw数值复算、重复摘要、输入/输出差异、所有显存样本/实际身份以及双层清单完整集合。另有独立审查者核文字/图表/机制范围；你的有效结论也不能被替代。

输出APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES，BLOCKING文件行号+理由+建议，NON-BLOCKING、QUESTIONS。不写G4 marker、不操作远端。所有BLOCKING0且另一报告范围也通过后，主执行者方可放行rest。
