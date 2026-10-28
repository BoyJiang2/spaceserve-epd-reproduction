结论：APPROVE（G3-native，仅native stream布局诊断）
BLOCKING：0
reviewed_at_utc：2026-10-28T21:10:51Z
审查者：独立 Codex subagent `/root/handoff_cpu_review`

只读核验本地实际原件，未运行测试、SSH、网络或GPU操作。依明确要求仅保存本审查文件。

- sm-port-capture-index.json共35份原件，全部bytes/SHA重新计算一致；索引SHA256为e7dd9021df353894b222968666d6eb526dc251c9a71ce9dc5c46ae068bc14dd0。
- 外层exit0，记录执行commit496ecb51c66280fa0f47e2d03addb2877693aa9b；terminal failure=null、总6.334秒。claim绑定指定boot、GPU0完整UUID、本人CPU/GPU票、原probe源码/二进制及libsmctrl SHA。
- 实际顺序为offset0、8、16、24、32、40、48、56，未扩大搜索。前七项均普通exit3，四阶段SM集合均78，不能视为mask通过。
- offset56首次exit0，随后repeat-0/1/2均独立PID/startticks、exit0。四次原始记录一致：全SM为0..77，mask严格子集为24..77共54，清零精确恢复0..77，再施加精确恢复同54个SM。
- 各结果JSON与terminal对应项一致，SM记录均见原始log，无重复SM ID；各子命令均小于3秒，cleanup记录为空，无超时或信号。
- 每候选/复验后均记录指定GPU0为0MiB、compute为空；最终资源记录同样为空。该释放结论基于保存的实际观测，不是本轮重新远端查询。

结论范围：在此指定boot/Driver API13000/H20/GPU UUID、原probe和原库组合下，MASK_OFF=56的native stream mask效果、清零和重施重复性具有真实证据。

本结论不证明MPS、服务encoder stream、模型预检、decoder互斥、完整SM分区或性能收益。原numeric失败不改写；下一新run/config传播MASK_OFF=56仍须独立G1/G2及新numeric实际G3，不能将此native诊断作为完整numeric或model批准。

NON-BLOCKING：无。QUESTIONS：无。

GATE_RESULT: {"gate":"G3-native","selected_offset":56,"scope":"native_stream_layout_only_no_MPS_or_service_approval","decision":"APPROVE","blocking":0}

