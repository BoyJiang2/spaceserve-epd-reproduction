# EPD：CPU 生命周期验证准备（2026-10-30）

本页记录原生跨卡数值预检所需的 Ray 生命周期接线，**不是新增性能结果，也不代表 CUDA IPC 已通过**。本批不加载模型、不初始化 NVML/CUDA、不占 GPU；实际 Ray 四场景尚未执行。EPD 的性能对照继续见[项目内比较页](../../comparison/README.md)，旧方案 A、旧 53/60 批次分别保留。

## 当前完成与边界

| 项目 | 实际状态 |
|---|---|
| 资产路径修复 | qjh003 上 apply、verify 各一次，均 exit 0，并分别通过独立结果审计 |
| 修复内容 | 61份启动文件检查、56处路径修正、3个 Python 链接不变；flat IPC 库 RUNPATH 更新，原 nested 库不变 |
| verify 原始取证 | 122份物理原件＋1份生成 inventory；前121份原字节、SHA、UID、mode、mtime均未变 |
| Ray 安装源码 | 实际服务器17份固定源码 SHA 全匹配；仅静态读文件，未导入 Ray |
| 本地代码验证 | 166个不同 test ID 通过、0 skip；包含模拟、回环 socket、NTFS文件/硬链接检查，不能作为实际 Ray/POSIX/GPU证据 |
| 源码审查 | 初审及首次修订拒绝原件保留；最终 outcome 修订 G2 和独立失败路径复核均 BLOCKING 0 |
| 实际 Ray / native36 / 公平 PD | 未完成；源码通过不开放这些运行阶段 |

资产维护 helper 来自 `97a33d5287cfdca69956da0fdabe5bc68ea65d46`；当时 EPD 运行目录仍为 `a3f03b9dd5956db92add454f9b3afd5663f84609`。两者来源分别记录，不能把使用维护 helper 写成运行代码已部署到 helper commit。SpaceServe 的运行目录继续冻结 `24b441923119581ab1c5e3274eca7d654021675d`。

verify 包 `raw.tar` 为 **1,003,520字节**，SHA256 `97dc246c9b1e5f3e9f219043be2731e4df7de1d234803016870f26869f256374`。它包含环境启动文件及两个库的原字节，只在本地留存，不作为环境包提交 Git；本页提供逐文件 inventory、真实运行回执和独立审计。它不属于新性能数据或待下载的 Release 资产。

## 代码与本地复核

- [CPU父入口](../../runtime/numeric_cpu_lifecycle.py)：独立私有 head、四个单次场景、180秒工作＋120秒清理；pending、未知 PID 或释放未确认时失败。
- [CPU driver](../../runtime/numeric_cpu_driver.py)：连接已有私有 head，保留 Ray 官方退出 hook；不使用通用 shutdown/kill 接管。
- [有界 GCS 观测](../../runtime/numeric_gcs.py)：实际 ActorID/job/namespace 查询，单次 RPC 有界；DEAD 本身不等于 PID 已退出。
- [原子回执](../../runtime/numeric_cpu_receipts.py)：同目录写入、文件 fsync、原子且拒覆的硬链接发布、目录 fsync。
- [源码及 minimal 分支检查](../../runtime/numeric_cpu_ray.py)、[原父链登记](../../runtime/numeric_descendants.py)。

仅复跑本地 CPU 测试，可在仓库根目录的 PowerShell 执行：

```powershell
New-Item -ItemType Directory -Force .cpu-test-tmp | Out-Null
$env:EPD_CPU_TEST_TMP = (Resolve-Path .cpu-test-tmp).Path
$env:PYTHONPATH = (Resolve-Path epd/runtime).Path
python -m unittest discover -s epd/runtime/tests -p 'test_numeric_*_cpu.py' -v
```

测试不启动 Ray 或模型。Linux 的 pidfd、目录 fsync、Ray 进程行为仍须在指定 commit 部署后，由独立审查批准的 CPU 单元实测。以上不是远端执行许可；现有预约、独立 G5、部署核验、具体执行 G2 和实际 G3 分开检查。

## 四场景及防止误判

测试组合为 non_detached / detached，分别正常退出和构造窗口内受控退出。正常退出前父进程必须绑定当前活 PID 与 GCS 的同一 PID；构造窗口用 actor 实际单调时间记录，信号前保留两秒余量。

父进程区分“本来已经消失”和“实际成功发送 pidfd 信号”。detached 成功必须在 driver 实际退出后重新查询 GCS、重新读取活 PID，观察到 actor 存活，再由父受控释放；不能复用退出前的状态或把无信号返回算作释放。最终仍要求 GCS DEAD 与原 PID 确实不存在。迟到的未知进程只记录并使结果失败，不按名字或 UID 清理。

## 证据导航

- [本地166项测试原文](evidence/numeric-cpu-lifecycle-outcome-final-tests.log)与[源码清单](evidence/numeric-cpu-parent-outcome-candidate.json)。
- [设计 G1](reviews/g1-numeric-driver-lifetime.md)、[支持组件 G2](reviews/g2-numeric-cpu-lifecycle-support.md)、[最终父入口 G2](reviews/g2-numeric-cpu-parent-outcome.md)、[独立失败路径最终审查](reviews/numeric-cpu-parent-failure-audit-outcome.md)。
- 初审及修订拒绝：[初审四项](reviews/g2-numeric-cpu-parent.md)、[首次修订](reviews/g2-numeric-cpu-parent-revision.md)，保留问题与处理轨迹。
- [实际 Ray 源码静态核验](evidence/installed-ray-source-inspection.json)。缺少可选依赖与 minimal 选择一致，但尚未由实际 Ray 导入确认该分支。
- [资产 apply 实际审计](reviews/relocation-apply-actual.md)、[verify 实际审计](reviews/relocation-verify-actual.md)、[verify 真实回执](evidence/relocation-verify-terminal.json)、[逐文件 inventory](evidence/relocation-verify-inventory.json)。
- [官方来源与固定 SHA](source-evidence/CPU-lifecycle-extra-pins.json)、[核心来源](source-evidence/driver-lifecycle-source-pins.json)、[runtime_context 来源](source-evidence/ray-runtime-context-2.10.0.provenance.json)。完整官方原件保留在本地审查材料中，来源链接可独立获取。

下一步先完成精确源码发布、部署与真实 CPU 四场景验收，再接完整 native36 后端。三卡原生传输和公平 PD 的模型/性能验证仍各有独立门槛。本页未新增吞吐或延迟结论。
