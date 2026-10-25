# G5 私有仓库发布候选

独立只读审查，先读D:/Documents/codex/AGENTS.md及本次用户要求outputs/repository-setup/main-agent-upload-prompt.md。Claude本次weekly usage_limit_reached（work/repository-upload/g1-plan-claude.json），依3.2.1接替。你不改文件、不读取凭据/访问GPU、不实施commit/push/Release。可本地CPU只读核checkout/manifest/原包/检查结果。

当前用户明确授权提交main、Release和结果上传，最新补充要求根README尽量直接展示复现vs baseline。候选在work/repository-upload/checkout：四批原封存小文件原bytes；大证据由七原ZIP承载，固定SHA不重压缩，source-files.json逐文件精确Git或asset/member映射；docs/reading为有原SHA的阅读副本，只改相对链接和不可定位的历史本地链接标识；原文原bytes保留。根README直接有Space6吞吐/6延迟、EPD off2行及观测扰动、5历史表，G4已逐数批准。

请实际核：来源完整覆盖与原封存不变；Git文件没有>100MiB/权重/环境/缓存/秘密；强特征扫描全部source/ZIP/gzip和最终候选无命中（不是绝对秘密保证）；相对链接/图片、来源SHA和Release映射正确；源码脚本/patch/pin/review/图/raw导航齐；upstream LICENSE和来源准确。host/model/GPU预算/正式诊断替代/退化/输出差异/encoder-only/EPD高扰动受限用途/固定并发顺序与因果限制完整，不混排或新跑GPU。核G1/G2（4问题关闭+6CPU回归）/README G4来源有效。

批准范围应明确：先将完整可读候选commit/push main，此时publication/publish-state.json明确pending，Release URL只是固定目标，尚不宣称上传。随后在该commit创建draft Release；七asset逐个上传、服务器size/digest校验、实际下载字节SHA核准，proof绑定repo/release/tag/commit/asset身份及当前集合，才publish。发布后检查唯一tag解析预期commit、远端全部Git blob/main/README渲染/图片/asset真实链接和private。最后仅补真实审查/远端验收metadata及README已验证状态，第二次commit/push main，再核远端HEAD；无force/覆盖旧历史/tag/asset。若失败如实保留pending与证据，不宣称完成。原四目录/ZIP发布后再次SHA核对。

请给APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES、BLOCKING文件行号及最小建议、NON-BLOCKING、QUESTIONS和实际检查范围。不能将尚未执行的远端验收当已通过；可对上述有限条件收尾做明确审批。主执行者收到真批准后才发布，最终只按实际证据汇报。

实际候选：{"passed": true, "git_files": 2697, "git_bytes": 343363906, "source_files": 2545, "source_git_files": 2490, "source_release_files": 55, "maximum_git_file_bytes": 8957326, "all_staged_blob_bytes_match_checkout": true, "all_git_source_bytes_match_seals": true}
候选逐Git文件SHA/Blob清单在staged-files.json（work外置，避免候选自哈希循环）。checkout/publication/candidate-check.json为实际最终Git扫描/阅读链接检查；security-scan.json为全源/ZIP/gzip和候选扫描20,502,484,350bytes。误报只涉及两公开pstats函数名，证据/失败/修复/G2窄核均保留。所有后加文件已复扫无命中，原source-files2545全部有归档映射。

已真实核仓库{"id": 1433331669, "full_name": "BoyJiang2/spaceserve-epd-reproduction", "private": true, "default_branch": "main", "permissions": {"admin": true, "maintain": true, "push": true, "triage": true, "pull": true}, "size": 0}；当前仍空main，无任何commit/push/create/upload。G1/G2/G4真结论均在checkout/publication/reviews。G5通过后将补真实G5记录/原样提示、staged-check和候选来源元数据再复扫，属于允许的纯审查元数据，不改原文/统计/解释。最后实测上传/下载/远端后补验收与README实际状态第二提交。
