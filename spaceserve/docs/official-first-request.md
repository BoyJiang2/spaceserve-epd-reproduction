# SpaceServe 官方单请求：固定执行文件

状态：本地CPU检查及独立G1/G2通过；尚未部署、未GPU执行。本文件覆盖此前准备草案中的散落启动要求。

[源码与baseline审计](../comparison/20261103-native-baseline-source-audit.md) · [工具检查结果](../comparison/20261103-official-first-request-preparation.md) · [脚本](../tools/official_space_first_request.sh) · [收尾助手](../tools/official_space_processes.py)

## 运行前现场闭合

- 当前项目实际GPU预约、CPU授权/无冲突、boot、单卡UUID/NUMA0/占用、端口、自有任务、官方源码分支/HEAD/dirty、解释器及工具commit/逐文件SHA。原票为11月4日15–18，历史记录不代替刷新。已有正常任务只跟进，不重复启动。
- 不在服务存活期间切换源码。SOURCE_ROLE=native须HEAD d7ec548300d7950c1305231b2aaf970bab7569c1（tree与原生0408efc相同）；fork须66de079af4234b27f7f82ff91d238ef1351324ba。脚本只验证，不自动switch。当前分支仍fork，不能未切分支却指定native。
- 模型单H20/Qwen2-VL-7B-Instruct/FP16显式half/TP1/V1/eager，model CPU0–89 OMP4/监督CPU50沿用已批配置；必须实际选NUMA0卡，不默认旧GPU编号。EPD先真实请求，两系统正式测量串行，不增加GPU预算。
- 复用/local/boyjiang/SpaceServe-official/assets/models/Qwen2-VL-7B-Instruct软链接。图片只读复用同一COCO资产池/local/boyjiang/epd/assets/dataset/COCO_val2014_000000000328.jpg；不需启动EPD服务，不复制图片或权重。图SHA已冻结。

## 可复制调用

先把本页对应commit的脚本和助手按SHA部署到本项目已有位置，只有实际执行才建立/local/boyjiang/spaceserve/runs/下一个必要小run。HELPER为已审文件实际绝对路径，RUN为唯一新run；身份文件存在则拒绝重用。source_ROLE与所有资源参数必须来自当前真实G1/G2，不能由JSON或此命令自批。

```bash
# 现场绑定并审核：SOURCE_ROLE BOOK_START_EPOCH BOOK_END_EPOCH GPU_IDS PORT RUN HELPER
UNIT_START_EPOCH=$(date +%s)
export SOURCE_ROLE BOOK_START_EPOCH BOOK_END_EPOCH GPU_IDS PORT RUN HELPER UNIT_START_EPOCH
timeout --foreground --signal=TERM --kill-after=120s 780s bash "$RUN/official_space_first_request.sh" \
  >"$RUN/supervisor.stdout" 2>"$RUN/supervisor.stderr"
# 当前执行工具保存真实session/PID/exit并持续跟进；不裸nohup离开。
```

600秒导入/就绪、120秒单请求、120秒清理、60秒保存，共900秒；清理子命令最坏79秒，外层失联兜底900秒。helper pidfd只处理精确UID/root/runid/boot/start ticks登记的workload，保护监督器/祖先，未知身份不kill；GPU释放另核实际查询。stdout/stderr/实际模块路径、request/response和SHA、curl/HTTP退出、usage及进程/GPU终态均保留。

## 首错、机制与正式测量

可能触发CUDA的import/--help/ctypes只在合法GPU窗口。先实际确认模块/扩展加载；若编译模块缺失或ABI失败，保存首错再最小适配，复用已有binary不重装整套环境，不预先复制217MB。

只发一次/v1/chat/completions，COCO数据URI+Describe the image.、temperature0、ignore_eos、128目标输出；curl失败也写退出码，监听PID/服务状态请求前后均核。响应usage仅证明API报告计数，不能单凭200/128判语义或机制正确；buffered HTTP不当TTFT，视觉tokens未采集保持null。

fork默认按libsmctrl可用性自动调用固定mask，给无效LIB路径不保证关闭fallback；不能把此诊断当正式无mask组。真实无mask/有效mask三组控制还须按实际机制最小适配、独立审查。有限SM采样不要求全覆盖允许集合，不硬编码64/78，不称未验证decoder互斥分区。MPS/计算重叠均未验证，不接管或停止未知MPS服务。

原生baseline包来源有两处已查修改，采用固定native源码内容分支避免误标；这不证明历史数据全无效。完整三组性能需正确性、机制与冻结正式协议各自通过后另行运行；3小时预约不承诺覆盖两套完整矩阵，不缩协议冒充完整实验。
