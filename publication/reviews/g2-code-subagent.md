# G2 发布工具初审

独立只读审查者 /root/profile_instrument_review，接替本次真实Claude weekly quota错误。未执行builder、读取凭据、联网、操作GPU或发布。

结论REQUEST_CHANGES，BLOCKING4：

1. build_repository.py扫描通过后还复制顶层元数据、AGENTS和生成阅读文本；根README后加，不能证明最终Git候选全部扫描。须统一最终候选扫描并命中阻止发布。
2. github_api.py默认重定向；download首次asset URL未验证。须在附加凭据前校验HTTPS授权origin/repo路径，API重定向安全，补初始HTTP/外部URL/API跨origin假凭据用例。
3. publish只比较name/SHA的本地旧proof，未绑定repo/release ID/tag/commit/asset ID/size/digest及当前集合。新create拒绝或清理旧状态，publish重查。
4. create不查同名已有tag，Release可能实际指向错误commit。必须拒绝冲突tag并create后/publish前验证实际tag，禁止移动旧tag。

NON-BLOCKING：建议精确枚举七资产与固定SHA，避免glob未来加入未知ZIP；流式上传、逐asset服务器SHA/size、实际下载SHA、-O拒绝及canonical包逐成员映射方向合理。

主执行者均采纳：完整候选verify_checkout、API NoRedirect、首次精确repo/asset URL、绑定proof/当前asset复核、旧状态/同名tag拒绝与前后tag校验、七固定ZIP SHA；6项离线回归全过，guard-test-result.json。修复后另请复审，尚不视为关闭。
