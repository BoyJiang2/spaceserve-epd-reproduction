# G2完整复跑补充续问原文

实际审查者：独立subagent `/root/fallback_g1_g2`；接替依据AGENTS3.2.1；Claude额度失败证据 `reviews/claude-availability-20261023.json`。下列原文由该agent从同一会话实际收到的续问逐字回传；不是事后补造的新提示词。结果见 `subagent-g2-full-replay-20261023.md`。

```text
补测正在运行，源7文件不再变。为最终交付的完整复跑命令补齐相同cache proof，我仅在canonical scripts/run_epd_h20.sh加四次check_rgb_cache调用：EPD第2epoch矩阵前/后、baseline三副本矩阵前/后，输出evidence/*-rgb-before/after.json；不改变infer/warmup/参数或现有补测脚本。本canonical文件不在当前补测执行路径。请只读复核这四行，给G2对完整复跑版本的补充结论。无需重审旧日志或数据；仍禁写文件/SSH/GPU/网络。
```
