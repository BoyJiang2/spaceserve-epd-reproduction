# DeepSeek交接：单场景 CPU Ray smoke

本次只验单场景smoke，不能外推四场景、GPU或EPD性能。主线程已核实际EPD为2f4f777及其e0fada6祖先；SpaceServe为b48a5a339ecd41a1d30c955fb8ce0dd25bbff2a0、工作树clean，b48仅只读导入和核diff五文件，未据历史18项测试声明当前GPU通过。e0三文件此前已合入9a63及后续版本，无回滚。

## 入口与交接审计

主线程已有受审入口是venv解释器 /local/boyjiang/epd/assets/envs/epd/bin/python，先由-c loader插入runtime，再runpy执行；driver用同一sys.executable及loader。实际历史运行已connected、actor ready和parent ACK，故不沿用“连接失败”结论。交接的直接-I文件调用缺sys.path、系统Python无Ray是其两次启动调用问题，不是本主线程这些已运行批次的现因。

原run_smoke3.sh仅作为交接原件留本地，未执行：秒级目录配mkdir-p会复用并覆写config，最后echo可掩盖真实失败码；随机选核和未校验booking/version/pins不适用当前固定配置，残留检查吞OSError也不能证明none。采用现有受控入口，固定CPU50/nice10、空CUDA、独立root/run/端口49180，明确--smoke。保持UID/host/root/affinity和pidfd安全检查，未放宽scope。

handoff所指12:44 cpu-child-exit残留属于本主线程run214228，已按真G1/G2清理并由G3 945184确认10原PIDabsent/scope空；未动其他run。首次SSH取证超时及只读恢复原件保留。

## 本地修正与验收边界

正常ACK后，在原30秒场景deadline内等待持有的driver Popen真实退出并reap，之后恢复GCS/collector；controlled路径不改，非0/超时仍失败。parent只有读到本次真实driver连接事件且唯一、address/session/owns_processes/时间字段均正确，才把原事实连同driver原时间和provenance转存lifecycle.jsonl；不能从配置合成连接成功或补写旧证据。201 numeric加既有4 policy共205项本地测试通过，仍不代表真实smoke通过。

五项实际验收缺一不可：
1. 实际调用退出码0。
2. terminal.json exit_code为0且smoke为true。
3. parent lifecycle.jsonl中的真实connected_existing_head.address为127.0.0.2:<本批port>，并能回链0/driver-events.jsonl原事实。
4. 原事件顺序为submission_observed→normal_live_actor_bound→scenario_terminal_observed→CPU_known_processes_absent。
5. 本run的严格遗留核验为none；不可读未知PID不能被静默当空，未知不获清理权限。

本页发布前，新的smoke源码尚未部署/真实运行。本轮不运行完整四场景、不启动GPU/MPS/模型/正式矩阵；原full4失败全部保留。源码入口为epd/runtime/numeric_cpu_lifecycle.py --config <新批次配置> --smoke，必须使用固定venv与loader，并完成本批版本、预约和身份准入；不要在旧目录重跑。
