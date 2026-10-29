结论：APPROVE（本次实际numeric G3，仅转完整313模型预检）
BLOCKING：0
reviewed_at_utc：2026-10-28T22:44:22Z
审查者：独立 Codex subagent `/root/handoff_cpu_review`

只读本地原始证据、Git对象与SHA；未执行测试、SSH、网络或GPU操作。依明确请求保存本审查原文。

本次run为space-http-20261029，生产source为beadff9c4cc4693cd2ea8675020f757e313659e8，boot65f52a67-afe4-4919-8646-4694255b48ee，GPU0/UUID GPU-dd8ab4ed-e34e-4141-ced9-271897da8282，MASK_OFF56。

核验结果：
- numeric24份及preparation18份原件bytes/SHA全部重算一致。索引SHA分别为04b85cc05ba5d6c624b3334bccd1bd5e1fac5d9ff721a3757088c533b7bec4f2及3a2633ccadfccfa7b10f7cfd19f72db7cee17546b1ebee744e6d5f92851d39ef。
- 本次91项numeric manifest原件SHA为eae0fff1e1edf221c8716f171674c0643da8c61dc1aefe5a9e0413e1cd63157b，前80项与本run source manifest相同。80项指定bead Git blob的bytes/SHA均重算匹配。
- 本次CPU回执为60项、60个唯一ID、零skip；source manifest为b8c31f1b28f68a1f89fc16e6606d427314f90224fec52626e7acacccc03eaca5，资产输入仍为962ed4f1c1584e8f4c130e23e5ead049701bda8e5c8b0c764345e687d21b8716。
- actual claim及terminal绑定本run、boot、MASK_OFF56、冻结configSHA与native证明SHA；父监督terminal和原numeric launcher均exit0，NUMERIC_STARTED/exit的controller身份一致。
- 实际FP16 passed=true、max_abs_error0.03093719482421875，Torch2.5.1/vLLM0.7.2/Transformers4.49.0、Torch CUDA12.4/Driver API13000与GPU UUID符合本次范围。
- 三份真实MPS mask结果均为78→54→78→54，实际SM集合满足严格子集、清零精确恢复与重施同subset；三次集合完全一致。
- probe二进制SHA为0ab10e3a0972dc9a62a3b921112479c16d894b03784cf91ba75687f3d8b66b75，与COMPLETED绑定一致；libsmctrl原SHA不变。
- capture明确released=true、controller/child不存活、自有进程空；MPS本次PID4190406/ctime1793227347.27及独立token/pipe/UUID最终stopped；GPU0为0MiB/0util、compute为空。该结论基于保存的实际观测，不是本审查重新查询。

批准以本次真实审查生成本run的G3_NUMERICAL_APPROVED，并按原archive_numeric_producer.freeze保存不可覆盖producer归档。G3_NUMERIC_MODEL_CONSUMER须绑定实际新archive路径、索引/成员SHA、bead producer身份及本次manifest；不得指旧run或尚未生成的归档。bound_files覆盖91项源绑定、code-manifest、CPU/资产依据与实际numeric/资源释放原件，未重新下载的资产内容继续引用既有真实完整性证据，不虚称重新抓回。

仅允许numeric→完整原313模型预检转换。模型仍须fresh资源、精确consumer/输入与代码G2及原entry guard；服务encoder stream、冷启/重启、并发/正确性和清理须另行实际G3。CPU60和本次numeric不证明force-close已解决真实服务连接问题，连接复用根因仍为假设。

旧f5ec model失败124尝试/123响应及SSH transport记录独立保留，不被本次通过覆盖。不授权formal；本窗完整201分钟入场期限已过，不缩矩阵、不拼旧48/54。

NON-BLOCKING：无。QUESTIONS：无。

GATE_RESULT: {"gate":"G3-numeric","run_id":"space-http-20261029","source_commit":"beadff9c4cc4693cd2ea8675020f757e313659e8","numeric_code_manifest_sha256":"eae0fff1e1edf221c8716f171674c0643da8c61dc1aefe5a9e0413e1cd63157b","scope":"numeric_to_complete313_only_no_formal","decision":"APPROVE","blocking":0}
