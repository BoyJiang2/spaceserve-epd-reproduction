结论：APPROVE_WITH_NITS
BLOCKING：0
reviewed_at_utc：2026-10-28T16:40:38Z
审查者：独立 Codex subagent `/root/handoff_cpu_review`

认可转入固定版本、hash-lock及wheel-only的uv方案，避免继续手写逐包resolver。批准本地实现及负例测试准备；各实际action仍以新G2、测试复核、G5/push、三端工具字节及fresh资源核验完成为前提。

本轮只读确认：旧prepare_space通过importlib.metadata定位wheel，UUID修补为文本修改；apply_space_compat主要使用AST和合成CPU回归，不需要导入Torch/vLLM。protected清单确为2582项，其中8个链接已有明确相对link文本及target_member，可以按pin恢复。

批准边界：

- uv先排他复制并核原始SHA，系统Python精确核3.10.12；不使用EPD环境代替Space。
- 五个action分别独立claim、完整日志及终态；依赖前一action真实成功，不把失败partial当已完成，不自动重建env或重跑action。
- 清除外部UV/PIP index、配置、凭据及环境注入，显式固定官方index、受控cache/tmp。UV_HTTP_RETRIES=2仅属于本新resolver范围，始终受240秒action硬截止约束，不重试旧catalog。
- compile仅生成版本/hash锁，不能宣称artifact字节已取得；install必须消费该精确锁、wheel-only/no-deps/require-hashes，不回退sdist、构建或自动Torch backend。
- framework只使用固定官方commit、明确补丁和原库；不运行下载包的导入副作用，不make，不重编原两份.so。历史脚本须按新资产根形成受审调用，不能原样沿用旧root或marker。
- install后静态核154版本及uv pip check，再核完整protected内容和8个精确链接；任何差异停止，不改旧pin、不把同版本视为同字节。
- 只有所有action及最终完整核验成功才能记ASSETS_MATERIALIZED；仍不等于目标CPU、CUDA机制或GPU Gate通过。

NON-BLOCKING：

240秒安装上限可能不足以下载并安装完整CUDA依赖。首次失败须保留cache/partial与env实际状态，阻断后续framework/verify；如需恢复，再按具体失败审一个明确cache/partial恢复单元，不能提前赋予自动续跑权限。

另需在G2检查实际uv参数与已保存help完全相符；不支持时直接失败，不能删掉安全参数后继续。

原两个catalog单元保留为部分metadata记录，不再重跑，也不需要将其伪补齐后才能采用uv方案。此批准不改变runtime a3f、模型SHA、实验设置、资源预约或旧封存。

本次仅只读审查，未测试、网络、SSH、GPU或写文件。

GATE_RESULT: {"gate": "G1", "scope": "bounded_Space_uv_hash_locked_wheel_only_environment_and_pinned_framework_preparation_after_G2_G5", "decision": "APPROVE_WITH_NITS", "blocking": 0}
