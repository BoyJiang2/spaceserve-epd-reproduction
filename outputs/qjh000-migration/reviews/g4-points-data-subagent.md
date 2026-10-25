# G4：首六配置原始数据与统计

实际独立审查者/root/profile_instrument_review；范围g4-points-prompt.md，按同批Claude usage_limit_reached/AGENTS3.2.1接替。审查者只读本地CPU复算，未操作远端、GPU或marker。

结论APPROVE_WITH_NITS，BLOCKING0。仅首轮1/C1和4/C8共6配置；完整矩阵及G5未验收，rest还须报告范围通过。

- 1800formal+120warm完整、唯一、全部成功；每响应128 tokens、每图256视觉tokens。全部图片顺序、processedinput IDs和实际API端点配对一致。
- 18个重复的窗口、吞吐、样本SD及每重复/合并延迟分位数与raw一致。
- 22797份显存样本逐项核PID、GPU0、整数bytes/求和/容量/单调时间/foreign，通过；最大内部gap0.237257s、最大首尾gap0.108180s；先前失败批次未选用。
- 三组实际FP16组件、同物理UUID、MPS100%、库SHA相符；MPS server始终124699，API/worker/各case前后边界及采样身份一致。
- points双层清单覆盖实际120个regular files完整唯一集合；冻结660项、used-scripts49份及实际远端检查日志相符。199payload+1清单传输包SHA/唯一成员/CRC/EOF通过。审查时无G4 marker/rest。

独立吞吐复算：

| 组 | 1/C1 req/s | 4/C8 req/s |
|---|---:|---:|
| Native | 0.4456914 | 2.0137680 |
| Space | 0.4514446 | 2.1317959 |
| Mask | 0.4489036 | 2.1404305 |

输出IDs差异对native：

| 比较 | 全320含warm差异 | 正式300差异 |
|---|---:|---:|
| Space低 | 5 | 5 |
| Space高 | 82 | 79 |
| Mask低 | 8 | 6 |
| Mask高 | 85 | 81 |

抽查首次分歧低零起算13–66号、高5–83号token，仍描述同街景/摩托车/长椅人物。全差异输出未发现精确匹配另一个输入、却不匹配本输入的串图证据；高点59/82和68/85份差异能在native相同输入的其它请求中找到完全相同token序列。

NON-BLOCKING：高点同输入重复0对重复1/2，native有3/100、3/100不同，Space19/22，mask18/21；保留这些事实，不归因为FP16，不保证全量语义质量/完全排除路由问题，90固定案例G3与正式输出范围分开。高点吞吐/TTFT收益伴随TPOT P50退化，mask对unmask约0.4%仅本轮均值，不支持显著或全面改善；采样和边界无法排除任意瞬时外来负载或证明单因果。

QUESTIONS无。未重新运行生产统计脚本或GPU。Codex处理：全部差异及raw保留，报告限定/取舍文字已交独立G2/G4窄核；仅在另一G4报告范围也通过、远端分析/导出均结束后放行rest。
