# G2 有限并行上传

独立只读 /root/profile_instrument_review，APPROVE，BLOCKING0；G5有限范围APPROVE_WITH_NITS。

worker仅固定Space名称/SHA，WORK只隔离manifest和进度，ROOT/STATE原来源同draft，只有upload调用，无create/delete/publish，不全局改HTTPS类。原private/tag/commit/本地size/SHA/既有digest守卫不变；starter失败不接管。两worker结束后必须原七manifest补齐observed，verify/publish不得用子manifest。保留退出/asset身份记录。未执行/联网。
