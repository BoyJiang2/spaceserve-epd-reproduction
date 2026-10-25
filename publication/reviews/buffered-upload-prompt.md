G2/G5有限窄核：目前两个已批准worker还在各传EPD/Space，无覆盖。每连接约170–250KB/s。主执行者只读无认证TLS测得直连上传socket SO_SNDBUF=65536；临时新socket调至4194304且默认TLS hostname检查true，HEAD302成功，无系统设置改变。

拟upload_buffered_asset.py 30行在一个新直连TLS连接上设4MiB socket发送缓冲，实际传七包中尚未开始的reproduction-h20.zip（唯一固定name/SHA，79.9MB），不是另传测试垃圾。WORK进度隔离，ROOT/STATE同原，无create/delete/publish。默认TLS证书/主机检查不改，仅连接自身buffer，API连接不动。此worker与另外两个不同资产并行；各自原size/SHA/asset拒绝覆盖守卫不变。原父worker将来若遇其他starter依守卫停止，不接管；待全部结束，原七完整manifest重新核齐observed/实际下载/当前集合后才publish。

请只读G2核代码及G5核将不同资产并行限额从2至3这一流程；无源/原包/统计/文档数值修改，不改主机网络/驱动/GPU，也不停止任何现有worker或删除任何asset。仅新socket缓冲4MiB（非TLS禁验证）。批准后才运行。恢复/worker/实际结果元数据最终提交。真实Claude本周quota按既有证据接替。回APP/REQ/BLOCKING，不执行/读取凭据/联网。
