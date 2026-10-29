# EPD static inventory — independent scope G1

Reviewer: /root/epd_pd_followup. reviewed_at_utc: 2026-10-28T22:52:38Z (clock tool). Scope: parent-authored outputs/migration-qjh003/epd-static-inventory-plan.md, SHA256 e55c8e5fb1541844b74e0b7adccf96370e30ef07b40493078d8a2937e6495321. Only local plan reading/hash and this review were performed; no implementation, tests, SSH, network, CPU inventory, credential access or GPU. This is a scope review, not execution/result approval.

结论：REQUEST_CHANGES / BLOCKING 1。

## BLOCKING

B1 — epd-static-inventory-plan.md 最后一段“原stdout/stderr/实际argv/CPU API凭据保存本地…”要求保存API凭据，与适用AGENTS凭据禁止落文件的硬边界直接冲突，也与前段“无secret/token/home配置读取”自相矛盾。请把“CPU API凭据”改为“fresh CPU预约API原始回执/票据原件（剔除Authorization、access/refresh token、cookie和任何凭据）”；明确只记录非秘密预约身份/资源/有效区间/观测时间，不读取或记录认证材料，命令/日志也不得包含凭据。若原意本就是预约回执，只需这一处最小文字更正；本审查不要求重新认证或申请资源。此项关闭前不执行。

## 其余范围判断

- 有明确前置：必须当前Space HTTP-fix313实际终态，自有CUDA与MPS释放被真实确认后，才允许一次静态CPU盘点。正式201min门槛已过不意味着模型预检已经结束；不能现在执行。异常/UNKNOWN终态不自动满足释放条件。
- 固定qjh003/UID2147/boot65f52a67-afe4-4919-8646-4694255b48ee、本人CPU票bk-20261028T0925-0332cf80/21–09、CPU50/nice10、60工作+30收口及08:58截止，不增加预算。实际执行前仍要fresh票/同boot/CPU lane无冲突，并确认完整90秒能在截止前容纳；旧票和本G1不能代替当时准入。
- 原生/usr/bin/python3 -I -S -B只读元数据、有限shebang和小IPC SHA；readelf只解析ELF静态信息、每次10秒/全程60秒；禁止Torch、ldd、dlopen/ops.load_library、GPU查询/初始化、模型和任何文件修改。不运行patchelf，不扫描凭据或home配置，不重hash大型依赖。固定库/依赖范围符合最小目标。
- 读取实际Git HEAD仅记录差异、不reset；flat库/原始库是否存在、RUNPATH/NEEDED/shebang事实与源码child_env已传CUDA_IPC_LIB_PATH相区分，不重复已有传参。静态存在不等于可加载或GPU正确。
- 原始stdout/stderr/argv/失败输出留本地独立证据，远端不新建实验目录；不改env/source/manifest、旧raw/claim，不授native36/selected360/PD或340min GPU预算。后续重定位变更仍另G1/G2/G5/Git-first和合法新单元。

本次未审实际盘点命令/工具实现。代码、精确argv与有界清理若作为新启动脚本生成，仍需相应G2；不能拿本范围G1直接给任意SSH命令放行。修正B1后可窄复审，无需扩大为通用迁移框架。

GATE_RESULT: {"gate":"G1","decision":"REQUEST_CHANGES","blocking":1}

## 窄复审：B1关闭

Reviewer: /root/epd_pd_followup. reviewed_at_utc: 2026-10-28T22:54:04Z (clock tool). Revised plan SHA256: 368ce96cc548e28770c392016a6f82a3b38f6c784ec3b01e689c15ef64fc15bc.

已直接读取修订后末段，确认只保存fresh CPU预约API资源/归属/起止/观察时间的脱敏原始回执，明确剔除Authorization/token/cookie及任何认证材料。原唯一B1文字矛盾关闭；原审查全文保留。主线程说明既有snapshot也从未保存token，本窄复审仅核本计划措辞，不据此声称已审计所有历史snapshot。

当前结论：APPROVE / BLOCKING0，仅限所述只读CPU盘点范围。仍必须等待当前Space完整313真实终态及自有CUDA/MPS实际释放，fresh CPU票/host/boot/CPU50准入、完整60+30秒与08:58截止，并取得后续具体只读命令/工具G2。当前不执行；没有批准Torch/ldd/dlopen/GPU、修改/重定位、native36/selected360或新增预算。本轮仅本地读计划/时间/SHA并追加此原文，无实现/测试/SSH/远端盘点。

GATE_RESULT: {"gate":"G1","decision":"APPROVE","blocking":0,"closed":["B1"],"scope":"static_CPU_inventory_only_pending_Space_release_and_command_G2"}
