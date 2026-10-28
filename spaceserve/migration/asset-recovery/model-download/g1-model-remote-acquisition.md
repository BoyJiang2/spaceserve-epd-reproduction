结论：APPROVE
BLOCKING：0
reviewed_at_utc：2026-10-28T15:18:25Z
审查者：独立 Codex subagent `/root/handoff_cpu_review`

批准本地工具及负例测试源码准备，并条件性批准经G2、结果复核、G5/Git-first及三端源码核验后的模型恢复范围。

已只读核验固定manifest SHA256 `aef697ea3d388ac3914eecef7a37a9f8423e8438dac274c3b7fac1ebc44bd16e`：15项与现行pins逐项bytes/SHA一致；排除已恢复五项后，剩余确为10项、16,592,698,781字节。原download_manifest与旧curl失败/partial保持原样。

实现与实际执行须明确：

- 每个缺失文件一个独立fresh CPU单元、专属claim及排他partial；不发Range、不自动重试，任一失败停止后续整个序列。已恢复五项仅核SHA复用。
- 固定原repo/Revision/name，默认TLS验证；每次重定向逐跳拒绝非HTTPS、最多三跳。不记录query、userinfo、cookie或临时签名；URL出现在异常文本中时也须脱敏。
- socket timeout取 `min(30秒, 工作截止剩余时间)`；连接、重定向及每次read前后检查工作/API/预约边界，写chunk前再次核期限与大小上限。240秒不是保证能下载完大shard，无法完成即失败，不能临时延长或续传。
- pins、metadata、指定a3f源码与实际执行身份须绑定；空间预算在网络前核验。
- `os.link(partial, final)` 可以作为同目录排他发布：仅用于本unit新建、完整bytes/SHA验证并fsync的regular file；绑定目录与inode/UID，拒绝symlink、替换及已有final。解除的只能是该unit核实的临时名。若终态异常，保留实际文件状态，不据此重试或覆盖。
- 成功只记真实模型文件完整性。没有Space环境、目标CPU和实际GPU Gate时，不创建CPU_STAGED或宣称整套assets ready。

建议负例覆盖：HTTP→非HTTPS跳转、第四跳、超长响应、截断/错SHA、deadline/API过期、已有目标/partial、链接或inode替换，以及发布后临时名清理失败的真实状态保留。无需增加通用下载框架。

本结论不包含环境安装、其他主机访问、新预约、pins或实验设置变更；实际代码仍须独立G2。

NON-BLOCKING：无。
QUESTIONS：无。

GATE_RESULT: {"gate": "G1", "scope": "pinned_ModelScope_ten_missing_model_files_new_CPU_acquisition_after_G2_G5", "source_manifest_sha256": "aef697ea3d388ac3914eecef7a37a9f8423e8438dac274c3b7fac1ebc44bd16e", "decision": "APPROVE", "blocking": 0}
