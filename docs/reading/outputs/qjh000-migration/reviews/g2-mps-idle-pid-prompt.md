> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g2-mps-idle-pid-prompt.md) SHA256 1cad01413eb777fd686468407cebddf4efe33140bb77741dc94c61c1d826d0b4。原数字及解释不变。

# G2追加：已有空MPS server无client时只有数字PID

实际cold retry2已完成baseline-space的COMPLETED、标准+C8正确性及诊断采集；角色切换后space启动前，原始space/mps-idle.status.txt仅3819864，ps没有header/row，parser再次拒绝，清理后无残留。此次不是加载后缺client。
仅修改capture_mps_clients.py末尾：allow_no_server=True且所有非空行都是纯数字PID时可返回空；未知/混合错误仍拒绝。带api-pid仍拒绝缺header、并要求非空clients。test_mps_status.py新增真实numeric-only idle回归，Linux共6项PASS，证据evidence/mps-status-cpu2.log。
请只读复核这项delta，是否仍fail-closed；其他角色/模型/前置G2不变。准备保留整个cold试次/首次native reference到失败目录后，重新完整cold，不覆盖任何已有结果。原生baseline已有通过证据不会当最终三组G3。额度接替仍有实际429usage_limit记录。仅批准cold/restart，不formal。
