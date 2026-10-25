按g2-code-prompt.md原只读边界复审实际已修复代码。g2-code-subagent.md保存你初审4项BLOCKING及主执行者处理；三个helper均已更新，另外test_publication_guards.py真实6个离线回归通过guard-test-result.json，无凭据/联网/GPU。

请核：verify_checkout在所有后加文件后执行，并将在后续README/LICENSE/G5记录新增后重新执行以覆盖最终Git候选；NoRedirect API完全拒绝跨origin/HTTP重定向，download首次精确固定repo/asset id；proof绑定repo/release/tag/commit和asset身份/size/SHA，publish拉当前集合比对；create拒绝旧state/proof和任何同名tag，create后/publish前核tag；资产精确七ZIP固定SHA。新create不会覆盖已有Release/tag。还未跑builder/commit/push/upload。

请给同范围复审APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES、BLOCKING/NON-BLOCKING/QUESTIONS。只审不改、无远端/凭据/GPU。
