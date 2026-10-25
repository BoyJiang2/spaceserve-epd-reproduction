# G2/G5 发布传输恢复窄核

先按当前项目AGENTS只读，Claude weekly quota接替仍有效。本次G5候选已批准、首main a7f4945a97193d54c40c38e53ba1dfb0d7e51b13已push，远端2702Git blob/README12表2图/两PNG/private均真实通过，remote-first-check.json。原七包与四源不改。

direct HTTPS上传约170KB/s，第一epd-followup已完整成功，第二epd-profile-a仅传约60MB。系统现有https代理是本机HTTP127.0.0.1:7897、无代理凭据（不改配置），已非认证HEAD探针验证同uploads.github.com TLS/HTTP302可达。新upload_via_configured_proxy.py仅将原helper的uploads.github.com HTTPSConnection改成通过现有HTTP CONNECT；TLS目标仍uploads.github.com，原token不进入CONNECT，其他API连接原样，所有size/SHA/既有asset拒绝覆盖/下载proof/publish守卫不变。

拟恢复步骤（尚未执行）：
1. 仅停止本次Python上传进程88576，创建时间2026-10-26 00:30:31、cmd精确本项目release_assets.py upload，停止前再核PID/创建时间/命令；不碰其他进程或GPU，等原session终结。
2. 重新GET本repo private、draft Release423520704/tag experiments-2026-10-25/target上述首SHA与其asset。唯一可删除的是本次自己创建的未完成epd-profile-a.zip asset675536023，created_at2026-10-25T16:30:49Z、state=starter、digest=null、声明size236452469（不是0byte；声明大小不表示上传已完成）。前后metadata保存assets-before-route-switch.json，原本机完整SHA f7a35...不变。若已经uploaded且size/digest正确，绝不删除，直接让helper跳过；任何身份/状态不同均停止。DELETE仅清理自己此未完成draft临时上传，不删除成功/历史资产。之后GET确保该starter不存在或有效完整成功。
3. 用新wrapper恢复同一七固定原包上传，已成功的epd-followup由原守卫跳过，不改asset名称/内容/tag/main。仍需完整服务器digest及实际下载SHA才publish，最后按原G5两阶段收尾。保留原失败/中止、metadata及此新审查/工具快照于第二元数据提交。

请G2审代码/TLS/凭据/进程身份/失败态清理边界，G5审此有限发布恢复是否仍符合已授权交付及不覆盖历史。你只读本地，不读真实凭据、不联网/访问GPU、不执行恢复。回APP/REQ、BLOCKING/建议。无需重审既已通过的数据/图表。
