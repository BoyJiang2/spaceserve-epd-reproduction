> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g4-full-data-subagent.md) SHA256 8a066f6266635c391e67f41d0e1b7881fa64395881c7895ecc5abf52ef0f5129。原数字及解释不变。

# G4 全量SpaceServe数据与归档

实际独立审查者：/root/profile_instrument_review。接替当前Claude明确usage_limit_reached，原失败JSON g4-full-data-claude.json，reset03:50。仅本地只读CPU独立复算/归档核验，未执行生产统计脚本、实验/GPU、写文件或marker。

结论：APPROVE_WITH_NITS。BLOCKING：0。覆盖18配置数据与证据，不替代报告G4、G5或最终ZIP验收；此前points批准保持有效。

实际独立核验：

- 5400formal＋360warm，共5760行、54重复完整无重复，全部成功、128输出、每图256视觉tokens。逐重复吞吐、三均值/样本SD与合并300请求的TTFT/TPOT/E2E分位数均独立重算一致。
- 三组图片序、processed IDs、RGB、端点、实际模型参数与FP16/TP1/eager/缓存/采样配置公平一致。
- 58294显存样本逐项核PID、唯一GPU0、bytes求和、容量、时间顺序和foreign。最大内部间隙0.237257秒，最大窗口首尾0.124610秒，均通过守卫。
- 六角色会话同物理UUID及私有MPS server124699；实际worker组件、100% MPS、库SHA和边界相符。
- 三份实际源码检查日志各完整660项，49 used-scripts匹配冻结SHA。原points120文件逐字节未变，双层manifest及G4 marker原bytes一致。
- 全量包415payload＋1清单的外层SHA、完整唯一集合、逐payload本地/归档SHA、gzip CRC/EOF通过；SHAd7d75ef664e750ba87b3810ba43ccc3b06ff0f159814d28cba59a8ac9f0e6814。
- 实际终结finished/child_exit0，COMPLETED 2026-10-23T15:02:44Z；结束GPU表为空，MPS同token running→stopped，boot/两repo固定版本相同，最终diff与交付patch字节相同。旧采样失败320行/77文件另包保留、未入选。

输出差异全部key/计数独立重算：

| 图/C | Space：含预热/正式差异 | Mask：含预热/正式差异 |
|---|---|---|
| 1/1 | 5/320；5/300 | 8/320；6/300 |
| 1/4 | 62/320；58/300 | 49/320；47/300 |
| 1/8 | 54/320；50/300 | 60/320；54/300 |
| 4/1 | 0/320；0/300 | 0/320；0/300 |
| 4/4 | 93/320；88/300 | 96/320；90/300 |
| 4/8 | 82/320；79/300 | 85/320；81/300 |

抽查差异文本仍描述对应街景、玩具熊或长椅人物；首次分歧及同实现跨重复变化已检查。未发现精确匹配另一输入却不匹配本输入的串图证据；不能保证全部语义正确/排除所有路由问题，不归因FP16。

Space/native吞吐−6.32%至＋5.86%，mask/native−7.52%至＋6.29%。新增四点mask/unmask−7.33%、−6.98%、−1.09%、−2.94%，不能用首两点约±0.5%概括全矩阵。

NON-BLOCKING：

1. final-summary.md中320分母宜称含预热配对，正式分母为300。
2. 保留固定顺序、时间漂移、采样边界、输出不完全一致和因果未定限制。机制生效不证明mask收益。

QUESTIONS：无。

主执行者：采纳分母措辞建议，明确含预热0–96/320、正式0–90/300；其余限制保持。文字delta请同范围窄核，不改raw、统计或设置。
