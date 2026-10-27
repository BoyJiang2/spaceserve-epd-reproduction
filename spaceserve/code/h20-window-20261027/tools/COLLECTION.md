# 运行结束后的独立证据采集工具

这四个源/测试是已审工具的原字节副本，不修改模型或静态61项。模型运行记录的源码commit仍是83edff6608fc9db33ea90c3d04ce091705ee643f，运行中该部署目录冻结。采集阶段另外记录本工具所在的精确commit和SHA，不能把后续工具commit追溯标成模型生成版本。

只在原controller和child实际终态、无自有遗留进程、GPU4正确UUID且零显存/空compute、private MPS100% stopped之后，使用单独的clean Git checkout执行；不更新模型运行期间的checkout或ROOT源码。

```bash
python -B <collector-checkout>/spaceserve/code/h20-window-20261027/tools/capture_phase.py model --start-sha <实际MODELS_STARTED原件SHA> --producer-sha <实际model-code-manifestSHA>
```

两个SHA来自本批实际观察，不用旧批常数。本批唯一模型接续实际开始markerSHA为959a2b853658ad9ac01336e2c34e2f006d0664b96ae13bb4447763f96388a29d，producer为d542d1acbf078ee2cebe466df732a6f1f0c618851931960a3597845eab49a138；命令前再次核原件和实际exit，不能仅凭本文执行。

采集器验证归档numeric source与当前model manifest分别通过身份；记录工具自身/identity helper SHA，保存真实成功失败文件、runtime设备目录、MPS intents与日志、终态资源/owner/booking快照及逐文件inventory。输出已存在时拒绝覆盖，资源未释放时拒绝大传输。采集回执不是模型G3或性能结论；必须另经独立审查。本窗口不启动54项正式矩阵。
