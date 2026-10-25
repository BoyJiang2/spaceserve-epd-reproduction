> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/epd-profile-a/reviews/g4-notification-analysis-subagent.md) SHA256 d005c14b78ac240513d20978c90b8e299ed74a707949b43960d25c44bc366236。原数字及解释不变。

# G4：新增通知间隔与受限报告

实际审查者 /root/profile_instrument_review，只读，Claude额度接替依据同本批；提示prompts/g4-notification-analysis.md。
最终结论：APPROVE_WITH_NITS，BLOCKING0。独立核7适用SQLite，未修改文件或访问GPU；G5两项需另复审，不宣布交付完成。

- 48请求6096/6096间隔、每配置2032、未匹配0。endpoint/rid、128worker阶段顺序与128API输出、原始时间戳一致，worker/关联GPU均在对应marker前。
- 全6096行CUDA kernel/copy/memset并集、补集、CUDA外API与未解释余量/target step及分布独立重算一致，未重复加和。
- 低EPD2016稳态+16首→次；baseline各2032D通知，其中高21与他请求prefill CUDA相交，为子集。
- 16低EPD handoff rid唯一，P/首D活动在capture内，全部有contextcopy。P末→首D均值/P50/P95 6.6071325/6.9602095/8.3404523ms，copy仅时间重叠。
- 高baseline指定例155.988019ms，CUDA并集120.667839ms，他prefill110.499053ms已包含在全并集，未解释35.320180ms，不重复相加或证明因果。
- marker/API间隔差最大绝对值216.228073us，分布正确；7SQLite前后SHA不变，源码/测试SHA匹配；003测量/000分析正确。
- baseline无disconnect不是API耗时0；空白不当物理idle；高EPD只路径存在，未伪称缩窗完成。

NON-BLOCKING落实：报告/生成器已进一步写明同endpoint/rid内128worker与128output顺序+阶段/完成时序匹配，没有显式stepID或依赖链；原阶段表kernel边界与新handoff kernel/copy/memset边界不同，所以两处间隔不是统计矛盾。仅文字澄清、raw/统计不改。QUESTIONS无。
