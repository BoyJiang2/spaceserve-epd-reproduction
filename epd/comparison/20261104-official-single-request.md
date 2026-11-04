# 11月4日：官方EPD首请求实际跑通，原收尾失败后恢复释放

本次为MiniCPM-V-2_6、FP16、TP1、E1:P1:D1的单请求诊断；不是正式性能对照。运行源码仍为官方 `9b111f710dfb4724072b603d626a1e4dad93ef1f`，模型代码未修改。

| 检查 | 实际结果 |
|---|---|
| 官方模块和扩展 | epdserve来自官方checkout；Torch2.4.0+cu121、vLLM0.6.1.post2及_C实际加载 |
| 角色放置 | 日志E/P/D分别local GPU0/1/2，与run绑定的三张H20物理UUID一致 |
| 精度 | 运行日志明确Casting bfloat16 to float16 |
| 单请求 | HTTP200，curl退出0，128生成事件，work_exit0 |
| 图片内容 | 固定COCO000328 SHA cc5ceef6348a3d73d5742fc2fe8b3ad3636de1cdaa8b7ca18e5fee83335e93d6；三名军装人物、长椅、帽和书与响应主体相符 |
| 初次收尾 | cleanup_exit1、outer_exit1，原件保留，未改成通过 |
| 恢复释放 | 原身份助手再次stop退出0、known_live空、三张GPU显存0 |

[请求/响应、终态与恢复原件](../validation/official-single-request-20261104/evidence.json) · [角色原始行号及完整日志SHA](../validation/official-single-request-20261104/placement.json) · [独立G3范围](../validation/official-single-request-20261104/g3-review.md)。完整日志仍在服务器 `/local/boyjiang/epd/runs/r1`，manifest列大小和SHA；仅必要小证据同步，未复制模型或环境。

第一次诊断使用较长run目录，在ray.init遇AF_UNIX路径超过107字节，未完成请求；[原错误与释放证据](../validation/official-single-request-20261104/first-error.json)保留。独立审查后仅将第二次诊断目录缩为r1，原脚本/官方代码不变，随后实际启动Ray并完成请求。

第二次原收尾在stat与environ读取之间发生进程退出竞态，PermissionError中断，原始查询仍有GPU占用。用同run身份助手继续受控stop后释放；未kill未知身份或他人任务。修复候选只允许“同birth且已Z”处理为退出，活进程不可读或PID重用仍拒绝；发送信号前跳过Z。[补丁](../validation/official-single-request-20261104/exit-race.patch)、[真实CPU结果](../validation/official-single-request-20261104/exit-race-cpu.json)、[可重放fixture](../validation/official-single-request-20261104/test_exit_race.py)、[G2](../validation/official-single-request-20261104/exit-race-review.md)可核。

修复代码见[助手](../tools/official_epd_processes.py)及[启动脚本](../tools/official_epd_first_request.sh)。服务器原版不覆盖，后续选 `/local/boyjiang/epd/assets/build/official_epd_first_request_candidate.sh` 与 `HELPER=/local/boyjiang/epd/assets/build/official_epd_processes_candidate.py`，按此commit工具SHA核对；首请求900秒预算与现场准入仍适用[执行说明](../docs/official-first-request.md)，运行目录须足够短且不复用。该说明的旧工具commit对应原版，本次修复版本为本页所在commit，不能混称同一版本。

强制ignore_eos/128目标输出导致响应尾部出现特殊token及无关文本，原始响应完整保留，只批准主体语义核查。尚无完整模型输出一致、多图/并发/重启或embedding/KV数值一致性证明。迁移事件只支持事件链观察；decoding_begin接近末token，不能当整段decode起点。buffered HTTP不是客户端TTFT。CPU50继承绑定仅为诊断，不能用本次时延作正式性能或baseline加速比。

下一步先使用已审修复版保障收尾，再继续SpaceServe真实请求；EPD完整模型/PD/EPD同三卡公平性能仍待后续，不与历史方案A或53/60批次拼接。


## 2026-11-04官方在线IRP配置更正

本页EPD官方在线批次传入CLI `--intra-request-dp 0`，但源码/真实方法CPU复现表明该参数未接通，请求工厂默认True；不能称有效关闭。单请求完成/输出/释放原件不变，不将这些诊断解释为关闭IRP机制已通过。仅适用于所列官方在线版本，不外推其他历史fork。详见[四图诊断与参数修正边界](20261104-four-image-diagnostic.md)。
