**远端单文件获取源码G2：APPROVE，BLOCKING 0。允许一次8项离线CPU-MOCK测试。**

审查者：`/root/space2300_review`
reviewed_at_utc：`2026-10-28T15:30:48.291789+00:00`

核验要点：

- 每文件独立claim、排他partial、无Range/自动重试；完整200响应、大小、流式SHA及发布后SHA全部满足才成功。
- HTTPS最多三次跳转，拒绝降级与userinfo；签名query不进入location记录，外部异常仅保存类别/status。
- 读前后检查工作期限和fresh证明，socket超时受剩余时间约束；240秒工作、原预约收口条件保持。
- 发布使用同目录排他hardlink；仅两名称inode/UID/大小/mtime及最终SHA相等才移除本unit临时名。异常保留实际final/partial状态。
- 八项测试覆盖所述正反例及EOF关闭fp情形，不调用main/executor或实际网络。生产Linux行为仍需实际结果验证。

绑定SHA256：

```text
fetch_space_model_remote_cpu.py
4f511ceda75bcaf1e73277c7bfac09c514cbe2b01689b03443eaa282a822068b
test_fetch_space_model_remote_cpu.py
e64341d81b60d39911d5f634b7e20894077369140ab4f4934240a2016a99febd
migrate_code_cpu.py
9cf2b505f671954a08fddeae65ab52a2cdf288f0757e663e4d2ddce49698b405
```

允许workspace专属临时根中一次8项离线CPU-MOCK，保存命令、exit、原始日志、源码前后SHA及temp终态；失败不自动重复。

实际网络获取仍待结果复核、新G5/push、三端字节和精确wrapper/argv审查。实际命令必须限定G1批准的十个缺失文件；五个已有小文件只验证复用，不据此扩大为十五文件重新获取。原metadata/pins前后不变、目标/partial/claim排他、每文件fresh准入和失败停止条件继续落实。

成功仅单文件原字节验证，不代表CPU_STAGED、完整环境、模型正确性或GPU通过。NON-BLOCKING：无。QUESTIONS：无。此次只读，未测试或访问网络。

GATE_RESULT: {"gate": "G2-remote-pinned-file-fetch", "decision": "APPROVE", "blocking": 0, "max_local_offline_CPU_mock_test_units": 1}
