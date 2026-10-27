# Space正式部分矩阵实际数据G4

按AGENTS3.2.1 Claude额度耗尽由独立subagent只读审查，不GPU/网络/凭据/写文件；可本地CPU重算，不能覆盖候选/原件。主agent落盘结论。

数据root outputs/spaceserve-revision-20261027。冻结plan.md/schedule-v2：54cell/5400+1080，当前实际48完成/4800正式+960warm，048–053未执行。实际controller677986/child677991，ID6e1efdd0356e4551ab50c0d301122f03，exit1；formal-controller.log在048进入service前insufficient time for a formal cell plus cleanup，原900秒门槛，不重采。终态helper原SHA fc71b98ff896562c97fe9493b82b415ee548cb5d99a4d2b73dde588d47066419，00:45:53Z四原件确认boot、15/57/18、自有root进程空、GPU4零显存/compute空、私有MPS stopped。无新GPU。

原SFTP connection reset已保全；新holding work/space-formal-transfer-retry1-20261027，四路真实exit0，merge-verified.json全1713 bytes/SHA（1712new/1preserved）匹配，原远端inventory1709+4metadata。原model219文件十trace已抓，不重复下载。请抽核或全核清单/原G3consumer347绑定与dataset26。注意本地通用model manifest/G2是attempt0历史53，实际成功attempt1 alias57为G3绑定及分析所用，映射说明configs/executed-model-config-map.md经G2通过；勿盲覆盖原件。

实际候选 report/formal-terminal-reviewed-candidate：analysis.json SHA a0d68aff7e3b21bade5b04509290dc8dce2ac5a28711efac191f1fdb4608cb9b；report.md SHA 34eee9a20aedc9a4fd9d073f0d446cdb90c18c221e5d030411d4773df2567114。48valid、global_errors[]、intervals0，全54计划/54计划配对保留。partial raw PNG/SVG按事前G1/G2原始点展示批准：六分面，各load9或6有效，B2的1图C8及4图C1缺N/D/M；不均值/CI/拟合/补零。初版actual candidate点贴顶部，原图保留，max*1.08留白经独立G2通过，新图已实际view不裁点。统计不变。

核验重点：全部逐请求120=20warm+100formal/128tokens、正确图与实际IDs、每次吞吐/tokens/TTFT/TPOT/E2E原始时序/采样PID显存与MPS、RGB/导入/设备身份/请求序列、全局时间/预约/无并行冲突；只证明本分析覆盖范围，不排除瞬态host影响。partial缺失不能给完整矩阵CI/位置平衡结论。不把诊断trace当off关键路径；decoder仍visual+LM且encoder单独驻留，kwargs200704忽略实际448/256，encoder mask可撤销不代表decoder互斥。

请给实际partial G4结论及blocking/nits。完整54未达不可能批准为完整复现；可明确批准部分证据描述或要求修正。仅实际数据G4，不代表GitHub发布G5或总目标完成。
