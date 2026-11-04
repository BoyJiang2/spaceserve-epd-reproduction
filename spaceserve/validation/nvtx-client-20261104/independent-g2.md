# NVTX请求窗口组件G2

独立审查者subagent /root/official_epd_runtime_review_1104；2026-11-04，只读转送源增量与实际CPU HTTP回归，不独立访问文件/GPU。

请求：6238B客户端SHA7fc7aa483682a0825fb30667b36d7ea65df55d03f1396b2225ad34f19da162a6，沿用原四请求client，仅ctypes调用既有NVTX库，在线程建立/提交/等待外包主线程range并保存window元数据。真实fakeHTTP normal/500/short/timeout四场通过；未启动模型/MPS/Nsight。模型driver/profile runner尚未实现，不能授权整套运行。返回原文：

NVTX客户端组件 G2 **APPROVE / BLOCKING 0**，限所列6238B客户端及对应CPU回归版本。

增量仅在原四请求任务段外包裹主线程NVTX范围，未改变payload、索引绑定、采集、超时或finalizer语义；四项真实fakeHTTP回归支持该有限修改范围。

后续解释需保持：

- 此范围包含线程建立、提交和等待，是客户端请求任务窗口，不是单个GPU算子的范围。
- CPU调用成功不证明Nsight采到了事件。
- 超时后不能把profiler合成的收尾边界当真实Pop；应结合实际完整NVTX记录、客户端退出及window原件判断窗口可用性。

完整MPS模型driver、profile runner、注入环境与导出收口尚未获G2批准；本结论不授权新GPU，也不允许缩短1200秒准入预算。

以上仅依据主执行者转送代码及CPU结果，未独立读取文件或重算SHA。
