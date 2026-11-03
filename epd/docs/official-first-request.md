# 官方 EPD 单请求：固定执行文件准备

状态：CPU助手及固定执行文件已独立G2 APPROVE/B0；四工具已部署既有assets/build并通过目标机10项CPU检查，未GPU执行。此前散落命令不作为运行入口，保留在before-frozen-file备份，原审查失败未删除。

## 唯一执行入口

[固定执行脚本](../tools/official_epd_first_request.sh)，配套[进程登记/收尾助手](../tools/official_epd_processes.py)。保留既定官方E1:P1:D1 / MiniCPM-V-2_6 / FP16 TP1 / 单图 / 128目标输出 / greedy；0.65显存与swap1仅本次诊断，不作为正式性能设置。官方checkout仍基线9b111f710dfb4724072b603d626a1e4dad93ef1f，不迁入旧repo补丁，不改模型源码。

权重入口/local/boyjiang/epdserve-official/assets/models/MiniCPM-V-2_6，真实文件仍在既有资产目录，0复制。CPU_PY=/usr/bin/python3，模型PY=/local/boyjiang/epd/assets/envs/epd/bin/python。固定COCO000328图片SHA cc5ceef6348a3d73d5742fc2fe8b3ad3636de1cdaa8b7ca18e5fee83335e93d6；单图问题Describe the image.，按官方offline.py apply_chat_template现场渲染prompt，保存实际payload及SHA。

## 派发前必须现场闭合

- 新鲜只读预约、CPU授权/冲突、GPU UUID/NUMA/占用、boot、官方分支/HEAD/dirty、已有任务、实际解释器/工具SHA与端口。已有正常任务只跟进，不重复派发。
- 已知预约是boyjiang/qjh003/GPU bk-20261103T1013-51486279，11月4日15:00–18:00 +08:00；该历史记录不代替派发前刷新，不授权11月3日GPU。没有冻结GPU IDs/CPU/端口/工具commit及部署SHA，不表示执行G1/G2已批准。
- 此动作只需要本单元900秒余量，不要求先具备完整正式矩阵长窗口；不足900秒不启动。不改变正式协议、不卡201/340分钟门槛来阻止独立短诊断。

## 完整启动命令

在本项目既有runs下创建本次唯一必要小目录，将已审固定脚本和助手按指定工具commit/逐文件SHA部署；不复制模型/环境。RUN必须为/local/boyjiang/epd/runs/内新run，身份文件已存在则拒绝重用。脚本只读源码Git状态，不以其中JSON自行批准预约。调用参数全部来自现场G1/G2，而非脚本默认猜测。

```bash
# 先在合法窗口中绑定：BOOK_START_EPOCH BOOK_END_EPOCH GPU_IDS PORT RUN HELPER
# 再对工具commit、源文件SHA、NUMA/CPU与实际booking原件完成本次运行审查。
UNIT_START_EPOCH=$(date +%s)
export BOOK_START_EPOCH BOOK_END_EPOCH GPU_IDS PORT RUN HELPER UNIT_START_EPOCH
timeout --foreground --signal=TERM --kill-after=120s 780s bash "$RUN/official_epd_first_request.sh" \
  >"$RUN/supervisor.stdout" 2>"$RUN/supervisor.stderr"
# 由当前执行工具保存真实session/PID、开始/结束及exit，持续跟进，不裸nohup离开。
```

脚本从UNIT_START起把导入和tokenizer渲染计入600秒就绪；工作最迟720秒，收尾助手60+5秒，两次GPU查询各5+2秒，收尾子命令合计最坏79秒，小于120秒预算；另留60秒保存证据。外层780秒TERM/900秒KILL作为失联兜底，cleanup中忽略重复TERM避免中断收尾；CPU助手的目标机TERM/KILL及身份保护已有10项测试通过；整份脚本的模型/HTTP及外层截止运行链仍未实测，不能外推为已通过。

## 证据及通过边界

脚本记录实际模块路径/版本、tokenizer及prompt、请求SHA、server stdout/stderr、curl退出码/HTTP/完整response、生成事件/timestamps、登记PID/boot/uid/startticks、TERM/KILL及GPU查询终态。监听就绪须可见listener PID全部属于刚登记同run；不使用不存在的/health；父进程退出/首traceback/超时均立即收尾，不自动retry。请求前后均复核server及listener，curl失败也保存退出码。

8个本地Linux CPU测试已通过，包括真实TERM、忽略TERM后的KILL、foreign fixture不被杀、错身份/boot拒绝、live拒读不发signal、助手继承tag也存活、优化Python拒绝；此外，目标机同一工具版本的10项CPU检查也已通过；仍不等于整份模型脚本收尾或模型G3。语法检查只证明Bash/Python可解析。

HTTP200、128事件或terminal exit0均不单独代表语义正确/通信机制通过。buffered HTTP不当客户端TTFT；脚本只写actual_generation_events，不冒称重tokenize为原始生成token ID。输出须与固定图人工核验，再检查embedding/KV、小并发和重启；这些不伪装为已完成。

终态known-none只表示已登记非僵尸workload（不含监督器及祖先）消失；未知/不可读身份保留且不kill，GPU释放另核原始查询。不动第三方任务。证据只按本run明确普通文件清单回收，逐文件SHA对齐；不递归ray-tmp、跟随符号链接或复制模型/环境。失败、缺失及中断照实保存。正式性能另阶段、同机串行。
