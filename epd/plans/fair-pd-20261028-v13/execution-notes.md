# v13 CPU 单元执行说明（G1 第 2 轮之后，补充而不改写已审计划）

已审计划 qjh000-cpu-20261028-plan.md（SHA256 98b39014ca623f33f65d1d7975b45b04e5256a8b51bd148df4c05345799dff44）保持原字节；G1 第 2 轮的非阻塞建议与执行细节记录在此。

## 编排脚本

[orchestration/](orchestration/) 保存实际使用脚本的字节副本（实际从本地 work/claude-continuation-20261028/tools/ 运行，脚本内路径以该位置为准）：

| 脚本 | SHA256 | 作用 |
|---|---|---|
| deploy_v13_remote.sh | 0a20e9460151bec5909da9bc59d4ac07e7ef8a7a4c535ac73f5e2b4d4f4cb64a | 新 root 稀疏检出指定 commit，逐 SHA/clean 核验，写 deployment.json |
| remote_host_probe.py | 25a4e0ac46c3a638b258c680ef45d786b4e1c77ee5055db5caee274caa3a9bd7 | 只读 /proc 的 host probe |
| run_cpu_unit.py | c518a09f324cc31f7e998d651a11f7353fd369d18b38f77f420c51f42703cc45 | 采集 fresh 输入、组装 permit、唯一 runner 调用、下载原件 |
| make_v13.py | efae5f78ef32847429c87ee9f85d029d5d1a804fa45e3c7490c8b8f4ce3ac078 | 由 v13-a 机械派生 v13 |
| write_gate_original.py | 683e25c14447d7c166b3a2617b2222d06418bdd0805e4aca077555e8a87b1e20 | 把审查原文封装为 G1/G2 JSON（现场复算 scope 摘要） |
| stage_v13_commit.py | d459fccf59268273cd8433b1a7d2b4dcca532a3ee19ea5e4f40c5cdfb482c41e | 只暂存发布路径并自检暂存 blob 与 manifest |

## host probe 中“CPU50 冲突进程”的定义

只读预演发现 CPU50 上固定有 cpuhp/50、idle_inject/50、migration/50、ksoftirqd/50 和若干 kworker/50:*。它们是每个 CPU 都有的内核线程（`/proc/<pid>/stat` flags 含 PF_KTHREAD，父进程为 kthreadd），不是占用该核的任务。若把它们算作冲突，probe 会永远拒绝。因此 `cpu50_conflicting_pids` 定义为：**PF_KTHREAD 未置位、且 Cpus_allowed_list 恰为 50 的用户态进程**。只读 status/stat，不读他人 cmdline/environ。昨天同一次开机上的 v11 probe 结果也为空列表，口径一致。修正后对已消耗的 v11 root 预演：冲突为空，并正确识别出该 root 已有的 claim。

## G1 第 2 轮非阻塞项处理

- N-a：只读准备（claim 检查、部署记录、GitHub GET、时钟偏差）成功后才建立 attempt 目录；从预约快照起的任何采集都计入三次上限。
- N-b：服务器时钟慢于本地（负偏差）时，上传后先等待到本地经过时间超过 |偏差|＋3 秒再启动，仍守 200 秒门槛；|偏差|>60 秒直接拒绝。
- N-c：SSH 中途断开或无 RUNNER_EXIT 标记时，绝不重跑；只读轮询（最多约 7 分钟）直到 runtime 下出现 CPU-receipt.json 或确认没有 claim，再下载原件，必要时再次只读下载。
- N-d：计划中“runner 在 claim 前拒绝”一条，按“claim 前任何拒绝（runner 或编排脚本）”执行。
- N-e：本 EPD CPU 单元及结果下载须在 19:00 前、且在任何 SpaceServe 夜间窗口代码 push 之前完成；v13 push 后到 runner 启动前不向 main 推送其他 commit。
- N-f（可选）：不修改已审 grant；主执行者提问的上下文已记录在 reviews/g1-cpu-unit-round1-subagent.md 的处理记录中。

## 远端预演记录（对应 Q-a）

- 2026-10-28 约 11:39（北京），在 qjh000 的独立目录 `/var/tmp/boyjiang-deploy-gitcheck-20261028`（不是本单元 ROOT）用 main 85619cfcf553796ab3b3501e4a386f4a867f1801 与 v11 路径预演 clone --sparse --no-checkout、sparse-checkout set、fetch 指定 commit、detach checkout：HEAD 精确、66 个文件、tracked clean、cpu_target_runner.py SHA 前缀 d785264a 与 v11 manifest 一致。验证后约 11:42 删除该目录。本单元 ROOT `/var/tmp/boyjiang-epd-cpu-qjh000-20261028` 未被创建或触碰。
- 约 11:50 与 11:52 两次以只读方式对已消耗的 v11 root 运行 host probe（修正前后各一次），未写任何文件、未发信号、未查询 GPU。
