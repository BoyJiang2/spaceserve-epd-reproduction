# 当前目标验收索引

状态：本轮实验、分析及G1–G5已验收。最终封包的实际完整性与完成证据见[外置记录](../../spaceserve-7b-h20-integrity.json)，须kind=final、passed=true；准备中的状态元数据本身不代替实际最终封包校验。

| 目标 | 已核实证据 | 状态 |
|---|---|---|
| qjh000隔离环境、存储及固定依赖/权重 | configs/；evidence/environment-READY、installed-freeze.txt、model-migration.json、asset-migration.json | 技术验证完成，G1/G2已批准 |
| 保全迁移来源及旧结果 | evidence/old-seals-bound-verification.json；三个旧目录969/58/479 payload与固定ZIP清单、逐成员SHA/CRC绑定 | 已核验，无改写 |
| EPD方案A不重跑，完成核验分析 | ../epd-profile-a/report/report.md；../epd-profile-a-integrity.json；qjh003测量2400+160、qjh000仅CPU分析 | 受限G4/G5已批准并封存 |
| SpaceServe实际设备/并发/SM机制 | results/preflight-cold、preflight-restart、sm-feasibility、sm-layout；reviews/g3-model-final-subagent.md | G3通过；只证明encoder stream mask，非完整SIS |
| 首轮两点三组公平正式对照 | results/formal/points；report/space-points.json；两份g4-points真实独立审查 | 1800formal+120warm，G4通过 |
| 扩展至全部六负载三组 | 同监督器124199续跑rest；5400formal+360warm技术通过，全局COMPLETED 2026-10-23T15:02:44Z | 全部18配置完成并收回/复算 |
| 全量原始数据、结论与图表 | space-all.json/report、final-summary.md及performance-all图已真实生成并目视 | full G4数据/报告均APPROVE_WITH_NITS、BLOCKING0 |
| 结束状态及完整性 | 真实finished exit0、boot不变、冻结源660项OK、MPS原token stopped、无自有后台、目标GPU进程表为空；415payload传输包源postpack及本地CRC/SHA通过 | 技术核验及独立全量G4通过 |
| 可复跑命令、补丁、版本、失败证据 | README、scripts、configs、results/patches；model-attempts和formal-memory-failed归档 | 已保留；G5已APPROVE_WITH_NITS、BLOCKING0 |
| 最终交付包及整体目标 | G5后生成新ZIP，逐成员全读CRC/SHA及源postpack复核，外置包SHA避免循环；旧封包再验证 | G5通过；最终归档验收以外置记录passed=true为准 |

EPD高负载观测扰动超过5%的原门槛未通过；按用户“不重跑2400”授权，以已独立批准的受限用途交付，高EPD trace仅说明路径存在。不能把受限验收写成重采门槛已通过。

Space正式输出差异原样保留，不称全部逐token或语义一致；吞吐、TTFT、TPOT和尾延迟应一并解释。固定并发三重复不支持显著性或到达率SLO结论。旧4090/L20 2B、qjh003 EPD三卡与qjh000 Space7B单卡分别比较各自同机基线。
