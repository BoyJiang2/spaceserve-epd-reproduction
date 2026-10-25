> GitHub阅读副本：仅修正链接；[封存原文](../../../../../../outputs/reproduction/reviews/prompts/g2-rgb-followup-actual.md) SHA256 6b76dd25ba031e25ff337b8aa25c5614bb6bc6d1d50c8ba67d9295f7a4eef755。原数字及解释不变。

# G2收尾续问原文

实际审查者：独立subagent `/root/fallback_g1_g2`；接替依据AGENTS3.2.1；Claude额度失败证据 `reviews/claude-availability-20261023.json`。下列原文由该agent从同一会话实际收到的续问逐字回传；不是事后补造的新提示词。结果见 `subagent-g2-rgb-followup-20261023.md`。

```text
请快速复核你刚批准补丁的两个收尾修改，仍只读不运行实验：1) run_cache_fix_h20.sh 的runtime capture已按建议移到standard/C8正确性之后、benchmark之前。2) 用真实修改前API做CPU AST集成测试（work/test_epd_rgb_patch.py）时，发现既有apply_epd_compat输出IDs插入分支的old_text包含在new_text中，重复运行会再插字段；现仅将分支守卫由if old_text not in before/assert new in before改成if new_text in before: continue，后续旧片段唯一性断言保留。修复前幂等性测试失败，修复后对实际API连续两次应用、预载/原lookup/元数据路由共用20个RGB对象均通过，全程无模型import。请读这两处及测试源码，确认G2仍可APPROVE_WITH_NITS/APPROVE或列新BLOCKING；明确这轮小修改是否可进入补测。
```
