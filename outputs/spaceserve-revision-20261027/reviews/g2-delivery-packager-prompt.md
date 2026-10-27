# G2 Space固定证据打包工具
沿用AGENTS3.2.1，只读本地，不网络/凭据/GPU/改文件。
新增work/revision-phase/prepare_space_delivery.py、test_prepare_space_delivery.py。由已审prepare_epd_delivery.py保留同一扫描/路径/无覆盖/ZIP成员SHA/Git副本校验逻辑的Space独立副本，只增加build顶层/plan和handoff顶层文档、六个精确path+SHA二进制例外（3实际二进制各canonical与numeric-producer历史副本），一律Release-only；其他权重/env/binary仍拒。
三个SHA分别libsmctrl529e2502...36e7c5、service_sm_probe3be03cf8...4b3a1b、probe_sm_mask1b1c095e...2c29a；请对原G3_NUMERICAL_APPROVED和consumer347归档绑定、实际六文件都核全SHA。不能仅文件名例外，字节有变化即拒。大型trace>8MiB及sqlite仍Release-only；gzip大小写均解压流凭据扫描。未知source类型、越界symlink/junction、重复候选输出拒绝；JSON/ZIP/Git原字节不改。不运行/导入ELF。
8CPU PASS：沿用原6（跨chunk假密钥、secret路径不泄露、gzip/sqlite大小写、无覆盖/原字节/cache、权重拒）+实际6份已核二进制全Release-only+改名/改字节拒。所有包仅临时fixture，未打正式新Space包/上传。
额外源说明：evidence/upstream-mysmctrl-README.md原字节复制已公开repo licenses/mysmctrl.README.md，configs/mysmctrl-notice-source.json记官方commit/source/SHA，无额外许可授予。上游README来源SHA与旧publication/upstream-notices.json一致，原作者/引用/build限制保留；不要把自己编译叫原创库。SpaceServe Apache LICENSE既有补丁交付中保留。此轮仅打包代码审查，正式包G5、资产审核及远端验证另做。
输出APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES与BLOCKING/NONBLOCKING。明确不是正式数据G4或发布批准。
