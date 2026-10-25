**G2：APPROVE；BLOCKING：0。本轮两处修改可进入补测。**

实际审查者：独立 subagent `/root/fallback_g1_g2`，仅只读复核。

- `run_cache_fix_h20.sh:58–68`：runtime capture 已移至 standard/C8 正确性检查之后、benchmark之前，解决此前启动顺序建议。
- `apply_epd_compat.py:65–71`：优先检查完整 `new_text` 并跳过，正确避免了 `old_text` 被包含在替换结果中时重复插入字段；首次替换仍要求旧片段唯一。
- `work/test_epd_rgb_patch.py:18–28,36–54`：测试连续应用两次并比较 API 字节一致；随后通过提取 AST 验证预载、原 lookup 与元数据路由共用20个实际 RGB 对象。测试只执行所选节点、使用图片加载替身，没有导入模型。

未发现改变全局20预热、100正式×3或缓存修复边界的内容。此前“基线正确性仅覆盖首端点”的记录范围提醒仍适用。

我未重跑测试；通过情况来自主执行者报告。此批准仅针对代码与补测启动，B1仍须实际补测及 G4 复审后关闭。
