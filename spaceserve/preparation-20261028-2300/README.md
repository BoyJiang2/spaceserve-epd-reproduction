# SpaceServe：2026-10-28 23:00 窗口的 CPU 准备

**环境复制与 CPU staging 检查已完成；本窗口 GPU 尚未启动，正式 0/54。没有新增 baseline 或性能结果。** 既有性能数据仍见[本项目对照页](../comparison/README.md)，新窗口不能与旧48/54跨窗拼接。

| 检查 | 实际结果 |
|---|---|
| 服务器 / CPU | qjh000 / UID2147 / CPU50 / nice10 |
| staging 源码版本 | `8520791abda731e855e1aebb26661a5383d9aada` |
| Git tree | `00dcc5efc5f7cb09111d37f0a2c3dc69f2d3db2a` |
| 代码与配置 | 61 项 SHA 匹配，checkout tracked clean |
| CPU staging 用例 | 5＋2＋5＝12 PASS，零失败、零跳过 |
| 冻结输入 | 32,643 项，23,735,714,281 字节；源未变，目标文件与链接已核验 |
| 输入清单 SHA256 | `504760aae3c903cb090b766c7937640c2afdd8ea693a516da8c1a9733ff3357c` |
| boot | `c57aee5b-05dd-4c39-81fc-4c76b492d3d6` |
| 收尾核对 | 新 root 内无自有活动进程；该核对未查询 GPU 或发送信号 |

[原始检出回执](evidence/GIT_STAGE_CHECKOUT.json)、[12项测试日志](evidence/)、[复制回执](evidence/CPU_STAGED.json)、[准备后核对原件](evidence/CPU_PREPARED.json)均按下载字节保存。[SHA 清单](evidence-files.json)可核验公开副本。CPU_PREPARED 是 CPU 准备记录，不是 GPU G3 通过。

服务器直接连接 GitHub 先后发生 TLS 中断和连接超时；两次失败未启动实验。随后从已推送的 main 生成完整 Git bundle，经 SCP 传输后在新 staging checkout 检出同一8520791，bundle SHA、commit/tree和61文件校验通过。没有用工作目录压缩包代替 Git 版本。完整 bundle 只是部署传输件，代码已在仓库可读，故不重复上传 Release；权重、环境和缓存也未上传。

CPU staging 源 root 为 `/var/tmp/boyjiang-spaceserve-revision-20261027`，新 root 为 `/var/tmp/boyjiang-spaceserve-window-20261028-2300`。环境和模型复制独立，未使用共享可写硬链接。stage清单和部署工具留在[候选代码目录](https://github.com/BoyJiang2/spaceserve-epd-reproduction/blob/ecad958fdc9f09f8f3d39e3eef7c08d43db634df/spaceserve/code/h20-window-20261028/README.md)。后续辅助工具修复和版本独立记录，不能将后续提交追溯标成此次 staging 的执行版本。

## 今晚执行边界

本人 GPU 票 `bk-20261028T0700-987277c5`：北京时间10月28日23:00至29日08:00，实际 API 归属及起止须开窗重查。仅 GPU4，Qwen2-VL-7B/FP16/TP1/eager；native、编码器解耦、解耦＋有效 encoder mask 三组。19:00–23:00无本项目预约，不做远端操作。

开窗后仍须刷新预约、boot、GPU4空闲状态，完成指定commit部署、完整目标CPU验证、数值实际G3、唯一313模型预检及实际G3，再按formal G2与201分钟入场门槛执行54单元。07:58前受控收尾，身份不明不清理，不触碰他人。未验证decoder互斥时，不称完整SM分区。12项staging通过不能替代这些条件。

[计划](https://github.com/BoyJiang2/spaceserve-epd-reproduction/blob/ecad958fdc9f09f8f3d39e3eef7c08d43db634df/spaceserve/code/h20-window-20261028/plan-20261028-2300.md) · [G1/G2复审](https://github.com/BoyJiang2/spaceserve-epd-reproduction/blob/ecad958fdc9f09f8f3d39e3eef7c08d43db634df/spaceserve/code/h20-window-20261028/reviews/g1g2-final-codex.md) · [辅助工具修复审查](https://github.com/BoyJiang2/spaceserve-epd-reproduction/blob/ecad958fdc9f09f8f3d39e3eef7c08d43db634df/spaceserve/code/h20-window-20261028/reviews/g2-current-review-links-result.md) · [返回SpaceServe](../README.md)
