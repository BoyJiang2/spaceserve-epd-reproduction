G2 REQUEST_CHANGES / BLOCKING 1。独立subagent /root/official_epd_runtime_review_1104真实意见：
唯一缺项是外层timeout终止client后的逐请求终态：默认TERM/KILL终止整个Python进程，worker finally与pool.map不保证执行；现有三个CPU场景未覆盖。建议runner保存真实client.exit后、原EXIT清理前，独立stdlib从四intent收口缺失terminal，标client终止/未完成，未知时间指标留空，保留已有响应及terminal；补受控超时CPU场景，给client调用/退出保存/收口代码，确认set-e不跳过。未批准v1 GPU。
本意见依据转送材料未独立读/hash。
