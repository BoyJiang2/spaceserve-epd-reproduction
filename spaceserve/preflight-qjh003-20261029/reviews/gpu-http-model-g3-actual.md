结论：APPROVE_WITH_NITS（实际313模型预检G3）
BLOCKING：0
reviewed_at_utc：2026-10-29T00:27:30Z
审查者：独立 Codex subagent `/root/handoff_cpu_review`

本次只读本地原件、Git对象与原始压缩trace并重算SHA/集合/时序，没有运行实验、测试、SSH、网络或GPU操作；依明确请求保存审查原文。

## 身份与完整性

本run为space-http-20261029，生产source beadff9c4cc4693cd2ea8675020f757e313659e8，boot65f52a67-afe4-4919-8646-4694255b48ee，GPU0/UUID GPU-dd8ab4ed-e34e-4141-ced9-271897da8282。

- 本地archive实际355691974B，重新计算SHA为799d1774f1e45a82dfdf9c516c7f757c5911d6e4cf8e769ccf5e172815edeb88；tar顺序检查588成员/525 regular files，没有重复、链接或越界成员，全部文件bytes/SHA与local-index一致。
- 解压的525份文件与local-index逐项匹配。model-attempt1-files.json的260份实际model原件也全部bytes/SHA匹配。
- model manifest94项全部可在本地原件中逐项核bytes/SHA，原件SHA为0590bc625d2d3dff2d412bd240aeba29e6193016bcccb340fb38a24e654fb8f6；对应80项生产源码与指定bead Git blob逐项一致。numeric绑定仍为eae0fff1e1edf221c8716f171674c0643da8c61dc1aefe5a9e0413e1cd63157b，未复用旧失败producer。

## 实际请求、长度与路由

- 7条reference加6个冷启/重启角色，每角色15条correctness和36条diagnostic，合计7+6*(15+36)=313。
- 六个server.log独立计数Added request分别为58、51、51、51、51、51，总313，与请求原件一致，不仅采信COMPLETED总数。
- 90条target correctness均HTTP200，按原case顺序执行；实际输出token/timestamp长度等于case要求，时间戳单调并落在实际提交/完成区间。processed input token IDs逐条等于对应native reference；图像路径及case顺序保持原向量。
- 六角色前四个不同主体输出各自四种，语义关键词/顺序通过；实测同时在途C4=4、C8=8。没有用并发配置值冒充实际并发。
- 216条diagnostic均success，实际输出128 tokens、视觉1024 tokens；每角色20 warmup+16 profiled、C8/4图配置保留。这些是预检诊断数据，不是formal性能成绩。
- 六角色RGB before/after均passed，其records完整一致；只有捕获时间不同。

## 放置、实际mask与trace

- 冷启与重启的10份实际worker记录使用不同PID，全部实际CUDA UUID属于指定GPU0，参数只在cuda:0且为torch.float16；baseline单worker，disaggregated有独立encoder与decoder，encoder的only_vision_encoder=true。各实际MPS比例记录100及本run独立pipe。
- 未mask组实际encoder stream保持78→78，首次encoder执行仍78。
- cold/restart mask组各自原始stream记录为78→54→78→54，首次实际encoder执行仍为同54子集；清零精确恢复全集，重施精确恢复同subset。对应SM-validated及worker身份一致。
- 四组encoder/decoder的原始Kineto trace按各自baseTimeNanoseconds对齐，独立流式重读kernel事件后，以原绝对时间算术重算重叠总量，逐项精确匹配overlap.json：cold-space70695.75us、cold-space-mask404663.75us、restart-space61749us、restart-space-mask404287.25us。对应trace PID与encoder/decoder worker PID一致。
- 时钟数值使用大绝对浮点时间；不同求和/平移顺序可有微秒级舍入差。本审查核准的是实际正重叠证据及原算法结果，不将其升级为性能加速倍数。

以上仅证明encoder实际stream mask及观测到的encoder/decoder kernel时间重叠；不证明decoder使用互斥SM集合，不称完整SM分区，也不把54/78解释为吞吐份额。

## 终态与限制

- MODELS_ATTEMPT1_STARTED与models-attempt1-exit的controller_id、PID/ctime/start匹配，实际远端exit0；实际约1253.585秒。
- 实际capture记录released=true、controller/child均不存活、owned_processes空；最后MPS PID62465/ctime1793228705.02及独立token/pipe/UUID为stopped；GPU0为0MiB/0util、compute为空。
- 本地SSH observer TimeoutExpired属于观察/传输层状态，不能替换上述实际远端终态，更不能据此重跑；相应observer原始错误应继续与远端exit0分别保存。本审查的退出与释放结论依据已下载的实际exit/capture原件，不冒称重新远端观测。
- capture中的new_inference_requests=0只指取证操作本身；本run实际生成请求为313，不能引用该字段写成模型零请求。
- 所有旧path/transport失败、旧124尝试123响应及旧run保持独立。此次成功不能证明连接复用假设是先前失败的唯一根因。

## NON-BLOCKING

1. 五条target输出token序列不完全等于reference：四个disaggregated cold/restart角色的coco-4，以及cold-space-mask的一条cat。它们实际输入token/长度与原语义路由契约均通过，现行已审validate不对这些case强制逐token输出相等。因此不阻止本次机制G3，但报告必须披露，不能写90条输出token全部逐项等于native reference，也不能据此证明数值完全等价。原响应不得删改。

QUESTIONS：无。

本次批准仅为指定run的实际模型/机制预检G3。formal仍0/54，没有新完整性能对照，本窗201分钟入场门槛已过；不授权formal启动，不拼旧48/54，不宣称完整Space或EPD目标完成。

GATE_RESULT: {"gate":"G3-model","run_id":"space-http-20261029","source_commit":"beadff9c4cc4693cd2ea8675020f757e313659e8","model_code_manifest_sha256":"0590bc625d2d3dff2d412bd240aeba29e6193016bcccb340fb38a24e654fb8f6","actual_requests":313,"formal_cells":0,"decision":"APPROVE_WITH_NITS","blocking":0}
