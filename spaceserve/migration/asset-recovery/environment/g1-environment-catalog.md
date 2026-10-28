结论：APPROVE
BLOCKING：0
reviewed_at_utc：2026-10-28T15:47:49Z
审查者：独立 Codex subagent `/root/handoff_cpu_review`

已只读核验原freeze：3,140字节，SHA256 `12cc7ae16e15cb32a58d197b10c139df7d715a8c3eeb4246b77eebe5d4814b0f`，共154条，均为明确 `name==version`，没有直接URL或浮动版本。

批准本地catalog工具及HTTP-mock负例源码准备；经G2、测试结果复核、G5/Git-first后，条件性允许一次所述官方metadata GET序列。

实现边界：

- 仅请求固定 `https://pypi.org/pypi/<规范化name>/<原exactversion>/json`；验证返回name的PEP503身份及exact version。拒绝跨host/非HTTPS重定向，最小做法是直接拒绝所有重定向。
- 154项各最多一次，串行、零重试、首失败停止。2MiB响应上限同时检查声明长度与实际读取字节；连接/read timeout受工作剩余时间约束。
- 120秒工作、180秒父级边界内预留原件和终态收口；不能因项目多而自动延长或续跑。
- 只保存原始响应、HTTP状态、SHA及制品描述；不下载wheel/sdist、不执行metadata内容。artifact URL仅接受无userinfo的HTTPS `files.pythonhosted.org`，不跟随该URL。
- 使用排他目录/claim，至少1GiB空间，freeze前后SHA不变，失败原件保留，不覆盖旧模型准备记录。
- catalog只是官方制品metadata快照；不是已下载wheel字节证据、依赖解析完成、Linux兼容性或环境成功标记。Requires-Python、yanked及wheel tag原样记录，不在本阶段替用户改变选择。

NON-BLOCKING：

154个串行请求未必能在120秒完成。可接受如实保留部分catalog，但不能将其称完整，也不能据此自动开始第二单元；如需分批，另提交明确剩余成员与新单元预算。

本阶段不占远端CPU50，不影响正在运行的模型文件获取，不访问任何服务器、GPU或其他机器。目标artifact选择、下载、安装/补丁及验证分别另审。

QUESTIONS：无。

GATE_RESULT: {"gate": "G1", "scope": "one_local_official_PyPI_exact_version_metadata_catalog_after_G2_G5", "freeze_sha256": "12cc7ae16e15cb32a58d197b10c139df7d715a8c3eeb4246b77eebe5d4814b0f", "decision": "APPROVE", "blocking": 0}
