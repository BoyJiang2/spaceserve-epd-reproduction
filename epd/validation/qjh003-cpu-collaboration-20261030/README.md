# CPU 协作修改集成

DeepSeek 的服务器分支 fix/epd-smoke-leg，commit `e0fada6b435917e065bc4e7ab9a41dfb66c0b156`，在运行版本2d2上新增单场景 smoke 入口。主线程的 actor 引用修正在 `6550b48ae8d80588ccd73db5e1f97828fff06a3d`，已经发布、尚未实际部署。

首次部署在 HEAD 前置检查处退出1，未创建新 staging、未执行 Git 写入；现有协作分支与修改保留。随后以两个 commit 为父集成，保留 DeepSeek 三份代码原字节；只为新增 terminal 的 CPU 元数据补齐 Windows 测试 mock 与断言。本批入口不传 --smoke，仍为 CPU50/nice10、180秒工作+120秒清理、原顺序四场景，不用放宽 CPU 配置分支。

集成测试：176项 numeric 单元测试及4项协作 policy 测试通过，共180；早期5个错误来自新增 Linux CPU 观测在 Windows mock 不完整，原日志保留。没有用这些测试替代实际 Ray 验收。

此前真实 IP2 失败与清理保持原样。清理实际exit0/1.400188秒，仅证明原11登记PID全部消失、本run scope为空，不代表四场景通过。本页发布前，新集成尚未部署或真实复测；后续分别记录固定commit、物理文件清单和实际G3。
