# 结果资产索引

## Release完整封包、大小与SHA256

已发布并验收：七个完整原包均已从GitHub实际下载，大小与SHA256逐包匹配；用户已于2026-10-26将仓库调整为public；首次private验收为历史状态。验收记录见[publish-state.json](publish-state.json)。

| 批次/用途 | 下载文件 | 大小（bytes / MiB） | SHA256 |
|---|---|---:|---|
| qjh000单H20/7B最终封包，含CUDA trace | [spaceserve-7b-h20.zip](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/download/experiments-2026-10-25/spaceserve-7b-h20.zip) | 947,439,150 / 903.55 | `27101c16596d1db7e4d3f08eaf86b0456264fa370876ee813cbaace251c43eee` |
| qjh003 EPD方案A受限最终封包，含nsys/SQLite | [epd-profile-a.zip](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/download/experiments-2026-10-25/epd-profile-a.zip) | 236,452,469 / 225.50 | `f7a35baf1c7e0e13ea1b1df65d4436efff199c5b21c876198289fbbfb2a1c094` |
| 首轮4090/L20 Space及双H20 EPD最终选用封包 | [reproduction-h20.zip](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/download/experiments-2026-10-25/reproduction-h20.zip) | 79,894,392 / 76.19 | `3d12536a846208e3202b67650adeee2f424cc4da1bb0a6cc28c67a494941be38` |
| 首轮数据的只读后续离线分析 | [epd-followup.zip](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/download/experiments-2026-10-25/epd-followup.zip) | 1,043,008 / 0.99 | `d155537944ea9095f2b1eecbd3780f57a611100aa9701b5e5617f4137d38a3f9` |
| 历史首版，非当前正式选用结果 | [reproduction.zip](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/download/experiments-2026-10-25/reproduction.zip) | 67,954,214 / 64.81 | `4ca04873975832309377feaea281b71b214b9badfbae488be80eda6a43474c7d` |
| 历史待审快照，非当前正式选用结果 | [reproduction-review-pending.zip](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/download/experiments-2026-10-25/reproduction-review-pending.zip) | 77,535,470 / 73.94 | `a661a300df154bcd0767c2dfd9a111e082e9d3f5b27b48047e4a60bfb7e4bba4` |
| 历史通信/诊断快照，非性能结论 | [reproduction-peer-diagnostic.zip](https://github.com/BoyJiang2/spaceserve-epd-reproduction/releases/download/experiments-2026-10-25/reproduction-peer-diagnostic.zip) | 69,361,661 / 66.15 | `b4b950ce36918b2a46f536f7725861cf592aa3665b0d43bc77a045909e606c25` |

逐文件精确恢复位置与原SHA在[source-files.json](source-files.json)。每条record的asset/member是原ZIP中的真实成员；Git中的原封存SHA256SUMS需完整恢复后校验。七包低于2GiB，无分卷。
