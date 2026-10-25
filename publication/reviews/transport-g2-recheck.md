# G2 传输delta复审

独立只读 /root/profile_instrument_review，APPROVE_WITH_NITS，BLOCKING0。全局替HTTPSConnection的super兼容阻塞已关闭：仅注入release_assets.UPLOAD_CONNECTION，标准库原类不变。

CONNECT不带GitHub Authorization，目标固定uploads.github.com:443、默认TLS证书/主机校验保留。API连接、七包内容/SHA、不得覆盖asset、下载proof/publish守卫不变。真实构造器记录已读；代理两次SSL EOF一次302，不能证明大包稳定或加速。

恢复前再核精确PID/创建时间/命令并等原session结束，仅按既定条件处理asset675536023；若已uploaded则校验后保留，其他身份/状态停止。后续仍需服务器digest及实际下载SHA。审查者未运行探针、停止、删除、联网/凭据/GPU。
