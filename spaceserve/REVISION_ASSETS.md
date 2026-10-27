# SpaceServe补充批次原件与校验

[SpaceServe项目](README.md) · [实际部分G4与终态](../outputs/spaceserve-revision-20261027/report/publication-status.md)

**已实际发布，并于发布前及发布后分别实际下载两资产，bytes/SHA全部匹配。** 本批为48/54部分结果，4800正式＋960预热，六项未执行；完整54和总目标仍未完成。包内共2333文件，小体积2321文件可在Git浏览；六份大trace与六份精确绑定数值库/探针只在完整ZIP中恢复。权重、环境、缓存及访问凭据不提交。

| 文件（真实下载地址） | 大小 bytes | SHA256 |
|---|---:|---|
| [spaceserve-revision-20261027.zip](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/download/spaceserve-revision-2026-10-27/spaceserve-revision-20261027.zip) | 367957059 | `caec10f545beb3cd2dbfa9574e086a978a1743c5e5b2a9f8e412c1b9cb363255` |
| [source-files.json](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/download/spaceserve-revision-2026-10-27/source-files.json) | 533383 | `63805c0c7b8b8dd35f1af3675d57718990ec984190a1d6f173d4fb9ab3812044` |

下载ZIP并核SHA后解压，将与仓库outputs/spaceserve-revision-20261027同路径的所有成员合并为新专属副本；使用source-files.json逐文件核bytes/SHA。Git中缺少大trace/二进制时不能宣称已恢复完整G3绑定。恢复只读离线证据不授予GPU运行许可。

[新Release](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/tag/spaceserve-revision-2026-10-27) · [真实发布与全量远端验收回执](../publication/spaceserve-revision-20261027/publish-state.json) · [实际下载SHA](../publication/spaceserve-revision-20261027/download-verified.json)。精确数据commit与tag绑定不因后续文档提交改变；旧Release、七原资产及EPD修正Release/两资产核验未变。包内候选/待发布字样是创建时历史状态，本索引记录实际后续验收；完整54和总目标仍未完成。
