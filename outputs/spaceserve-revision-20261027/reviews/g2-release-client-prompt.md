# G2 Space独立发布客户端与只读下载transport
沿用AGENTS3.2.1只读subagent接替Claude限额，不网络/GPU/凭据/改文件。
新增work/revision-phase/publish_space_release.py、test_publish_space_release.py、verify_space_assets_curl.py、test_verify_space_assets_curl.py。
源于已审并实际用过的EPD客户端/Windows curl只读替代，但保持独立源，不改已完成EPD任何工具。固定同public repoID1433331669；独立WORK spaceserve-delivery-final-20261027，scope Space-revision-publication，tag spaceserve-revision-2026-10-27，两个asset名字spaceserve-revision-20261027.zip/source-files.json，Space/Qwen7B/单H20说明，complete/blocked以真实G5批准决定。
保留G5精确commit/bytes/SHA绑定、newtag/newdraft only/不覆盖现有asset、实际下载SHA proof、发布前current IDs/digests/tagcommit复核与拒-O；另明确拒旧Release423520704及EPD新Release424838375。没有delete/retag/forcepush操作。当前正式raw尚未抓回/无实际G4/G5/无asset清单，客户端未执行网络，不创建Release。
Space curl替代只换import，仍fixed API assetID / TLS HTTPS /首参--disable禁默认config/最终302/signed URL内存及stdin/no auth CDN/流式真实bytesSHA回原guards，不下调任何安全检查。
7纯mock publisher测试+4curl CPU测试PASS：无G5/changed bytes/外来proof/changed assetID or tagcommit/旧Release状态拒；新增“有效Space scope确实走到mock新draft POST”排除提前失败假绿、两个已发布Release即使tag/commit伪装匹配也拒。最初从EPD模板拷贝的测试scope/name残留已在审查前修正为Space，以上数字是修正后通过，不将早期假绿充作覆盖。
请核namespace/旧Release保护/actual proof绑定与正文不夸大、测试是否到达目标分支。只G2代码批准，实际final package/G5/remote acceptance另做。
回复APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES与blocking/nonblocking。
