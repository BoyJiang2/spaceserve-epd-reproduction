# 运行结束后的独立证据采集工具

本目录是新窗口候选采集工具，尚未运行；模型源码版本必须记录本窗口实际部署的精确 commit，运行中该部署目录冻结。采集阶段另外记录本工具所在的精确 commit 和 SHA，不能把后续工具 commit 追溯标成模型生成版本。

只在原controller和child实际终态、无自有遗留进程、GPU4正确UUID且零显存/空compute、private MPS100% stopped之后，使用单独的clean Git checkout执行；不更新模型运行期间的checkout或ROOT源码。

```bash
python -B <collector-checkout>/spaceserve/code/h20-window-20261028/tools/capture_phase.py model --start-sha <实际MODELS_STARTED原件SHA> --producer-sha <实际model-code-manifestSHA>
```

两个 SHA 必须来自本窗口实际观察；当前尚无本窗口的模型开始 marker 或 producer。命令前核实原件和实际 exit，不能沿用旧窗口常数。

采集器验证归档numeric source与当前model manifest分别通过身份；记录工具自身/identity helper SHA，保存真实成功失败文件、runtime设备目录、MPS intents与日志、终态资源/owner/booking快照及逐文件inventory。输出已存在时拒绝覆盖，资源未释放时拒绝大传输。采集回执不是模型G3或性能结论；必须另经独立审查。完整54单元还需本窗口实际 G3、formal G2 与201分钟入场条件全部满足。
