# CPU放置窄审

reviewed_at：2026-10-29T03:11:24Z。仅本地源码、固定上游缓存及既有原件读取/哈希；未执行测试、远端命令或GPU操作，未改源码。仅按请求写本审查文件。

结论：现有GPU启动链确实会把外层CPU50的亲和性继续传给服务和负载进程；代码没有显式扩大/重置该集合。**这是源码层面的继承结论，不是旧worker亲和性的实测，更不是已测出的CPU瓶颈。** 旧软件/机制G3不因此改写，正式性能仍0/54。新正式批次应先明确并审核CPU放置政策，再冻结新配置；本审查不批准资源扩张或实现变更。

## 已确认的启动链

- 实际历史`gpu-http-model-command.json`保存了`taskset -c 50 nice -n 10 timeout --foreground ...`，即GPU模型入口也从CPU单元的单个**逻辑CPU50**限制启动。`run_space_numeric.py:74`调用`migration.validate_executor()`，后者显式要求当前affinity为`{50}`及nice10；所以父监督器的限制是有意执行的准入条件。
- `run_space_numeric.py:29`的Popen只设置新session和受控environment，没有CPU放置操作；`helper.child_environment`也没有affinity操作。创建session或替换environment不会自行解除Linux的CPU亲和性。
- `entry.py:48–52`通过execve进入冻结run中的launcher；`model_launcher.py:41`再Popen原run_models；`run_models.py:39–60`复制环境并启动bash/start_server。上述层均未见`taskset`、`numactl`、`sched_setaffinity`或psutil affinity重设。`start_server.sh`最终exec服务Python，也没有放置重设；通常fork/spawn/exec后代继续继承受限集合。
- `run_models.py:140–150`启动的benchmark、捕获及其他子命令同样没有重设CPU集合；正确性HTTP客户端本身运行于run_models父进程。因此继承风险不仅针对GPUworker，也涉及API、图片/token处理、客户端、监控和MPS启动链。专有组件/原生库可能自行改变线程放置，不能仅凭这条Python链排除这种情况。
- 当前外部helper只允许numeric/model，**尚无其实际formal分支或本批formal执行证据**。已有`formal_launcher.py:41`、`formal_service.py`、`run_formal.py:73,116`也没有亲和性重设；如果正式沿用相同CPU50外层入口，服务、benchmark、monitor会有相同继承风险。这里不把预案推断写成formal已执行事实。

## 线程环境并不等于CPU预算

`env.sh:15`显式设置`OMP_NUM_THREADS=4 TOKENIZERS_PARALLELISM=false`。这是服务bash分支的环境；OMP4是线程并行度设置，**不是四个CPU核配额**，不能解除CPU50限制。解耦encoder/decoder分别运行时，还可能各自有线程池而共享同一逻辑CPU。

该env.sh在服务子bash中source，不会回写run_models父进程的environment字典。benchmark/monitor由父进程直接Popen，不能据此说它们也明确收到OMP4或TOKENIZERS_PARALLELISM=false。helper受控环境未设置MKL_NUM_THREADS、OPENBLAS_NUM_THREADS、OMP_PROC_BIND或OMP_PLACES；也未做NUMA memory binding。源码没有足够依据把这些库的最终线程数量/绑定状态当成已知。

固定SpaceServe上游缓存的`multiproc_worker_utils.py:290–306`只有“未设置OMP时降低Torch线程数”的默认逻辑，不扩大CPU亲和性。找到的`csrc/cpu/utils.cpp`中的sched_setaffinity属于CPU后端支持，不是这条H20 CUDA路径显式解除CPU50限制的证据。仅凭上游缓存也不能代替实际wheel及所有原生线程的运行记录。

## 旧原件能证明什么

对完整成功run的现有JSON结构键扫描未找到实际`affinity`、`cpu_affinity`、`Cpus_allowed_list`、OMP/MKL/OpenBLAS线程环境、CPU百分比或线程数记录。现有worker记录包含PID、CUDAUUID、dtype、组件、MPS和SM库等信息，不含CPU亲和性；`capture_runtime.py`只采指定GPU环境/argv/版本，未调用cpu_affinity。历史CPU验证阶段另有控制器affinity50记录，但它不能证明之后所有GPUworker/TID的实际放置。

因此：实际启动argv证明外层要求CPU50；代码证明默认继承路径；**缺少旧worker/TID亲和性及CPU利用率证据，不能宣称旧服务实测全部在CPU50、更不能宣称CPU50已导致吞吐下降、某组受益/吃亏或具体性能瓶颈。** 既有NUMA/topo原件仅支持GPU0接近NUMA0、其CPU affinity范围0–89；不能据此任意占用该范围，也不能把逻辑CPU50当成已证明的独占物理核。

## 对新正式批次的最小建议（尚未实施/批准）

CPU50/nice10最初是迁移/CPU单元安全准入，当前launcher明确沿用；未找到把“所有GPU服务与客户端共用单逻辑核”作为正式性能设计选择的独立论证。**它对监督器身份/收口是既定控制，对服务放置不是技术必需条件**：现有后代归属依靠PID/start/UID/nonce/root/runid，而不是要求每个服务后代也必须CPU50。

最小可审改法是保留父监督器/维护CPU单元的CPU50/nice10检查，仅在一个GPU工作负载启动边界显式应用经批准的固定CPU集合，并记录实际值；无需改模型、benchmark或另建框架。三组的API/encoder/decoder必须共享同一个总CPU集合/NUMA政策，不能每个worker额外扩一份配额。客户端及monitor的CPU集合和是否计入总预算也必须固定，三组一致。nice及线程环境一并冻结，不能只给某一角色扩大CPU或线程预算。

集合的具体CPU ID、逻辑/物理核口径和大小须基于有效资源授权与fresh拓扑/占用另审；不建议直接放开0–89、整机所有核或照搬未知历史设置。如果选择与既有OMP4相称的小集合，也只是候选，绝非本审查授予额外CPU。若坚持单CPU作为有意实验控制，也应明确写入新正式设计/报告并经G1接受，不能把受CPU限制的结果概括为一般GPU机制性能。

新批次至少在实际服务启动和测量边界记录API、encoder/decoder、benchmark/monitor的PID/start/UID、实际affinity/nice/线程数及相关OMP/BLAS环境；必要时记录线程级Cpus_allowed_list，防止只记录父进程设置。记录CPU时间/利用率才能进一步判断是否饱和，不需为本窄审额外启动模型。放置调整后须新配置/新cohort及适用实际Gates，不修改旧raw、旧结论或拼旧性能。

关键受审源码SHA256：run_space_numeric.py `c8c767faa430ff6375474f917d7be98cfeed8a59e7ecf68753ba0b94bfb02973`；validate_space_cpu.py `c9d895c8567fac7f2248c8af63996e6eb4b60080edf493b51002c1c4da4a641b`；env.sh `f66bcce83d0da805a7a7ef4bdbc819139bb3f6b0c307789cc53343b0c6848ee2`。
