# EPD / 公平 PD 固定代码入口（迁移候选）

本目录收敛自实际 CPU87 源码 f1ff073、随后受审的 cleanup 修复，以及尚未实测的 numeric 缓存组件。**本次整体重构尚未通过 G2/目标 CPU；native36、selected360 的 controller 接线仍未完成，入口会在 GPU/claim 前拒绝。没有新的正确性或性能结果。** 旧87结果不能覆盖本次代码。

固定项目根 `/local/boyjiang/epd/`：`repo/epd/runtime/` 是唯一源码，环境/模型/图片/IPC库在 `assets/`；真实独立批次在 `runs/<cohort>/`。cohort 下沿用 runtime/unit 的原始证据和不可退款账本；不同unit共用同一总预算，不能换unit重置340分钟或claim。源码Git根和执行归属根分开；PID清理只认当前cohort原始身份，不能清理repo/assets或其他同UID项目。

```bash
python3 epd/runtime/entry.py plan
# 新机器有效CPU票、实际部署指定commit/逐SHA、独立新CPU scope和permit后：
taskset -c 50 nice -n 10 python3 epd/runtime/entry.py cpu --config <cohort-project.json> --permit <new-permit.json>
# 仅消费真实、SHA绑定的校准证据，不能从mock结果选择性能结论：
python3 epd/runtime/entry.py analyze --select <actual-bound-calibration.json>
```

CPU保持单核50/nice10/每进程1GiB/300秒＋30秒清理，父子/真实POSIX身份与零skip要求不变。新CPU scope为空时拒绝，不回退qjh000旧boot/预约/root；Git source manifest必须包括实际项目配置读取器和共享路径模块。

GPU入口只代理已有资格/校准协议，并保持实际Gates与预算；两项未接齐的numeric/selected阶段仍不可运行，因此不能越过它们做模型或正式实验。三卡完整副本/合理调优PD（E+P合并）/EPD的同预算比较尚未完成，不称DistServe实测。两项目共用主机锁防同机正式干扰，锁不代表预约权。

`project-scope.json` 为静态候选，缺host实际运行证据/UUID/预约/boot/CPU scope；没有执行许可。未来指定commit、source/asset SHA仅写实际cohort冻结配置，避免Git commit自引用；其他scope条件仍需Git锁定。`preflight-static.candidate.json` 仍是候选，不是批准。

[上游原README](README_UPSTREAM.md)仅供源码参考，里面的自动GPU选择/启动例子不是本项目复跑入口。实际新实验必须走本入口和完整独立审查；模型、环境、缓存和凭据不进Git。旧批次报告、Release、封包和实际源码SHA全部保留。
