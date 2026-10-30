# CPU actor 引用修正与实测失败

本页属于 EPD CPU 生命周期诊断，不是模型、CUDA IPC 或性能通过证明。

## 实测与根因

qjh003 使用运行版本 `2d2f8018f3f9125ead3da169bf7ea8753141f5b9`，续约 CPU 11–16，单核 CPU50/nice10，CUDA_VISIBLE_DEVICES 为空，创建 actor 的 num_gpus=0。

实际已连接 `127.0.0.2:49174` 并取得 ready。actor_ready 单调时间 266191.418762776；父进程 GCS 完成查询 266191.478919132，状态 DEAD。原始 protobuf 死亡原因是所有 actor 引用被移除。源函数 scenario 只返回身份字典，唯一 actor handle 离开作用域，导致非 detached actor 在父进程 ACK 前被回收。随后 driver 的5秒 ACK等待超时。四场景完成0/4，原 terminal exit1 保留。

## 修正与验证边界

最小修正：scenario 返回 `(expected, actor)`，main 持有 handle 直到父进程 ACK；不延长超时，不改 lifetime，不改 GPU 后端。新增 weakref 用例在旧源码明确失败；修正后176项本地 CPU mock/单元测试通过。第一次全量调用漏设 EPD_CPU_TEST_TMP 导致36项环境错误，该日志保留；补齐测试目录后重跑通过。

当前此页仅记录本地修正，发布、部署和真实复测必须分别取得新回执，不能用176项测试代替实际 Ray 四场景验收。

## 证据

- [失败逐事件原件](driver-events.jsonl)
- [原 terminal](terminal.json)
- [完整捕获清单](capture-inventory.json)
- [旧源码反例](before.log)、[本地最终测试](tests.log)
- 本地完整失败原包 384875 bytes，SHA256 `5d9b2130bd6ab02c4a2706428d1cd6880b8c218619cdaf3531979a229f46906e`，尚未上传 Release，不能把候选下载地址当已发布。
