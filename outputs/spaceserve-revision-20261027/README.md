# SpaceServe H20顺序平衡补充

**最新状态：正式控制器已按900秒剩余时间门槛退出，48/54单元有效，4,800正式＋960预热，六项未执行；GPU4及私有MPS已实际释放。全部原件已抓回并逐SHA校验；[部分矩阵候选报告](report/formal-terminal-reviewed-candidate/report.md)及[原始点图](report/formal-terminal-reviewed-candidate/raw-observations.png)已通过独立实际部分G4；[终态与审查导航](report/publication-status.md)。不是完整复现或总目标完成。下方启动段为历史记录。**

[配置名称与实际attempt1部署映射](configs/executed-model-config-map.md) · [补丁恢复、版本与离线复跑入口](patches/README.md) · [整批分析G2](reviews/g2-formal-analysis-subagent.md) · [三配对与报告生成G2](reviews/g2-report-renderer-subagent.md)

[事前冻结方案](plan.md)经独立G1 APPROVE/BLOCKING0，预算单H20/Qwen2-VL-7B三组、六负载三次54单元，5400正式＋1080预热。负载内位置平衡、全矩阵两两先后9:9；三次负载内2:1残余混杂保留。

CPU复制经独立G2批准并实际完成：32643项、23735714281 bytes，源前后SHA/目标内容一致，旧源未变。仅复制集合内部绝对软链接转换为newroot相对链接，外部非解释器拒绝；[输入摘要与链接转换](configs/input-pins-summary.json)、[实际CPU回执](evidence/CPU_STAGED.json)、[Linux六项CPU测试](evidence/cpu-tests-link-relocation.log)。第一次安全拒绝日志保留，未创建目标/GPU。

数值入口G2与实际数值G3已APPROVE/BLOCKING0：FP16通过，独立probe三轮SM集合78→64→78→64，实际exit0、私有MPS已停止、GPU4快照已释放。模型与正式请求仍0；实际服务encoder stream/并发/模型G3尚未运行；CPU_STAGED不表示CUDA/模型/SM机制验收。代码候选未全部审查，不直接运行其中GPU入口或复制历史marker。迁移初始快照见configs/relocated-helpers.json和relocated-guards.json（不是最终代码清单）；当前实际numeric部署以configs/numeric-code-manifest-v2.json为准；完整正式配置仅schedule-v2，旧schedule未运行候选禁用。

已完成numeric对应G2、目标真实TERM/ALARM finally、fresh预约/boot/卡身份与实际数值G3。下一步按next-stage-handoff.md实现/审查模型313预检入口；正式54单元仍需实际服务/模型G3，不自动继承数值许可。实际服务SM必须严格子集/clear恢复/reapply一致/同stream，正式无probe/profiler；未验证decoder互斥不称完整分区。

EPD已明确受阻收口，完整C未完成，独立保留53/60结果；两者不混。当前预约实际截至09:00，08:58受控清理，启动前仍须重查实际预约。时间不足留断点不缩验证、不增加预算。GitHub新批尚未发布，总目标未完成。

数值原件：[三轮集合与FP16/build日志](results/numeric)、[独立G3](reviews/g3-numeric-subagent.md)、[原退出](evidence/numeric-exit.json)、[释放快照](evidence/numeric-resource-status.json)。这是独立数值stream，不是模型服务机制或性能收益；模型候选脚本尚待另G2。

## 模型预检attempt1的历史启动记录

首次模型启动在MPS前拒绝numeric stop遗留的自有socket，exit1/0推理请求，原目录、原53源码与批准都保留。经独立G1/G2批准增加精确stopped owner/inode/UID/PID消失验证的单socket清理；目标21CPU和实际57部署SHA通过、fresh预约/空闲后，唯一attempt1已实际运行。

当前模型producer57 SHA6782b5a1578c9d890f03bcc2368a36c3ab69663d7479f7b55b5af0c6f03141a5；controller456563/ctime1793048424.41/ID03a034209d28481eabb093d68ec83992，child456566。原313预算不变，正式0，不自动第三轮。实际进度见evidence/current-status.json和model-attempt1-progress-snapshot.json，原日志位于远端evidence/models-attempt1-controller.log；尚无完整模型/stream G3，不把marker或局部数据当验收。

实现限制已核：模型preprocessor默认min/max像素并非200704，vLLM日志说明传入尺寸kwargs被忽略。实际本批COCO20图全部448×448，已产生的四图诊断processed IDs均为1024视觉tokens（256/图），固定尺寸来自输入图片。报告必须保留该事实，不称kwargs设置本身已生效。

## 正式矩阵已启动（尚未验收）

模型313已实际完整结束并经独立G3通过，219文件/十trace核验，GPU终态已释放；正式另经G2/consumer G3、部署15/57/18与目标26CPU和fresh预约/空闲检查后05:58:07启动。当前formal controller677986/ctime1793051887.29，child677991，producer15 SHAa1f79489ec38e14b76f2ae53b6ac6ba9e1f9ac14d33dbb397dbcfa05efca92eb。原54/5400+1080顺序不变；07:01:34实际快照已18单元、block0完整，018进行中，后续以带时间的current-status及远端原日志为准，尚无G4/完整CI。

本批实际decoder保留visual675759104+language_model7615616512参数，另encoder visual675759104；不能称decoder language-only。实际encoder stream mask不代表decoder互斥，诊断trace不作为正式off关键路径。正式已关闭profiler/SM诊断；任何缺项保留，不缩矩阵或改采样门槛。源码和当前断点见next-stage-handoff.md。
