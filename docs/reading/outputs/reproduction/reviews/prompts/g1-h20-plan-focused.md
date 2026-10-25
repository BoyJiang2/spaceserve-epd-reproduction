> GitHub阅读副本：仅修正链接；[封存原文](../../../../../../outputs/reproduction/reviews/prompts/g1-h20-plan-focused.md) SHA256 39b6a2d727764c24ccabcabcbc1dbe4cec6aa7e24fd5dbda7d79afe33c3b751f。原数字及解释不变。

你是本项目独立只读审查者。只用 Read/Grep/Glob，不修改文件、不运行命令、SSH或GPU，不访问凭据与聊天记录。
项目根：D:\Documents\codex\2026-10-23\new-chat-2。请阅读 D:\Documents\codex\AGENTS.md。

本次仅G1计划/范围补审，不审代码或逐请求大文件。限定阅读：outputs/reproduction/goal.md、report/completion-audit.md、report/experiment-status.json、report.md 的“测量和复跑”与“结果解释与边界”，reviews/h20-fairness-facts.json 的两个主机images1-c1片段。

所有实验启动早于本轮引入Claude gate，无事前批准，不能补写成事前批准。003已完成1/4图×C1/4/8，005已完成1图C1、4图C8；各EPD对同机同三卡三个完整模型副本，FP16 TP1 MiniCPM-V-2_6，20全局预热+100正式×3，输出128。剩余是证据审查与可能针对性修复/补测，暂不做新实验。

特别问题：单图首配置全局20预热在基线三副本RGB图片缓存覆盖7/7/6张，EPD端20张；正式第一重复基线可能新增40个副本/图片缓存对，后续已覆盖。请求顺序和缓存实现策略一致，但不能声称初始缓存状态完全一致。用户固定预热20，请不要自行改为每副本20，也不要仅凭此推断额外开销的大小。请判断这是否需要后续G2/G4验证/补测，以及可在保持协议下怎样最小修复；需要用户改变设定时明确写出问题。

只评计划对目标与执行边界是否一致，最多12次只读工具调用；资料不足请列明确缺口，不扩大到所有日志。输出G1结论APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES；BLOCKING（文件:行、证据、最小处理）；NON-BLOCKING；QUESTIONS。不能把计划批准当成G2/G3/G4/G5批准。
