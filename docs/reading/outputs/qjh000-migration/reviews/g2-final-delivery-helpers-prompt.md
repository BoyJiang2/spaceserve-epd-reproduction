> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g2-final-delivery-helpers-prompt.md) SHA256 81b53ddc328d89a49613ad63801345f59e2223e36048dbd13d74dcc7bd47b7a8。原数字及解释不变。

# G2：收尾证据与最终封包helper只读预审

先读D:/Documents/codex/AGENTS.md。当前Claude实际usage_limit_reached证据outputs/epd-profile-a/reviews/g4-cuda-report-claude.json，已知reset22:50，当前尚未恢复；按3.2.1独立subagent只读接替。不得改文件、访问GPU/远端、执行实验；可读本地源码和现有清单格式，不运行下面helper（正式全量尚未完成）。主执行者实现，审查者只审查。

正式监督器124199仍在qjh000运行，首六G4已通过，当前技术完成12/18。以下代码只在本地work准备，没有上传、更改远端冻结代码或执行终检：

- work/capture_space_final_metadata.py：仅正式COMPLETED/实际日志finished exit0/原监督器不再活着/boot相同后，CPU调用已批准check_background读取本项目残留，nvidia-smi只读目标GPU表、两repo固定HEAD和当前diff。只新建证据文件，不停进程、不启动推理/模型。
- work/pack_space_phase.py、unpack_space_phase.py：points版已真实运行过并G4独立核199payload，新增all分支必须5400formal+360warm、COMPLETED/G4原bytes、同token的MPS stopped、最终cleanup/source/code证据，之后tar逐payload/源postpack不变及本地CRC/安全成员/原始文件不覆盖差异。
- work/package_space_7b.py：只有all统计18配置通过、COMPLETED和fullG4批准才生成candidate；final还须G5批准。先只读核旧三目录969/58/479全部payload SHA和旧三个ZIP固定SHA，不改旧批次。新目录排除__pycache__/pyc及自身SHA256SUMS，生成完整清单；work临时ZIP逐成员SHA/CRC/唯一集合+源postpack对齐，final才移到不存在的outputs/spaceserve-7b-h20.zip，并外置integrity/zip.sha256避免自哈希循环。

原旧清单格式已实际读确认均为sha双空格相对路径，不含pyc；兼容旧带根前缀的形式。packhelper目前只是代码/语法检查，未生成候选包或宣布全量完成，实际G4/G5和完整性仍将后验。

请核：旧结果保护、manifest完整/唯一集合、ZIP全读CRC+SHA是否足够、路径/覆盖规则、metadata是否只有真实结束后才收集、不触GPU实验/不杀任何进程、是否有自哈希/状态循环或不必要复杂实现。指出实际代码问题，不以代码通过冒充最终数据/包通过。

输出APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES，BLOCKING文件行号理由建议，NON-BLOCKING，QUESTIONS；回复主执行者保存，不改文件或写marker。
