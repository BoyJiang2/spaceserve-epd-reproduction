# qjh003 04:00–10:00 完整54单元准备

当前仅本地代码/配置及审查准备，未部署、未运行新批次，尚无新的正式性能数据。原模型、单GPU2预算、CPU0–89/OMP4、平衡顺序54单元（5400正式+1080预热）保持；OMP4不是总线程数4，encoder mask不等于decoder互斥。

本人主GPU票04–10、CPU04–11，后续GPU10–11不自动使用。每次实际阶段须fresh只读预约、实际boot/GPU2 UUID/NUMA/严格0MiB/apps空、指定commit/source SHA与独立phase审批。最后09:58停止工作并预留120秒清理，实际GPU释放须证据确认；formal201分钟门槛不缩减。

代码入口：[`control_space_window_20261030.py`](../../../tools/control_space_window_20261030.py)，服务端[`run_space_window_20261030.py`](../../../tools/run_space_window_20261030.py)，[配置](../../runtime/configs/qjh003-20261030-0400.proposed.json)。本地、GitHub、目标均须对应实际发布commit。配置中的source身份由prepare按指定部署commit实际生成，不预填自引用SHA。

控制端每次只一个phase：prepare、cpu、numeric、model、formal，不自动串联、重试或产生通过marker。调用格式：`python tools/control_space_window_20261030.py PHASE --commit COMMIT --approval APPROVAL_JSON --review REVIEW_MD --output NEW_EVIDENCE_DIRECTORY`。COMMIT必须替换为实际已发布版本，approval与review须真实独立审查且逐SHA绑定，不能把此示例或候选文件当运行许可。

阶段之间需完成真实CPU、numeric与归档consumer、输入重验/model manifest及G2、完整313实际G3、formal manifest/G2和模型consumer，才可进入formal。工具不自动完成这些审查步骤。04后服务器先部署指定commit并核Git与逐文件SHA；旧run和原封包不修改，不重用旧marker。观察UNKNOWN时跟原PID/创建时间，不以超时为重启理由。

本地测试命令：`python -B -m unittest discover -s tools -p "test_*space_window_20261030.py" -v`。目前9项窗口策略、6项服务端参数/末次准入、6项控制端构造/真实本地输入FD测试，不等于Linux/POSIX/Ray/GPU生命周期通过。初始预算G2阻塞与修复、Windows路径fixture原失败均保存。

本批GPU正式测量与EPD GPU实验顺序执行；旧48/54和旧GPU2 313预检分别保留，不能补拼为完整区组。最终报告、comparison图表与逐请求原始记录需实际G4/G5、Release及远端下载SHA验收。
