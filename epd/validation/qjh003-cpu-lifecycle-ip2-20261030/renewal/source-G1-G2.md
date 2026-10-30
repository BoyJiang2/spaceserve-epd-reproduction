# G1/G2最终窄复核：纯CPU11–16续约

结论：APPROVE_WITH_NITS；BLOCKING：0。G1续约范围与G2本地源码均通过，仅源级；未授具体发布、CPU执行、Ray实际运行结论或GPU。

实际审查者：独立subagent /root/fallback_g3；2026-10-30，只读实际源码/candidate/预约和测试日志；没有运行测试、项目、网络、SSH、GPU或信号。初审reviews/g1-g2-numeric-cpu-renewal-source.md/.json及其B1原件保持不变，reviewSHA6ac423d38c7eb20b5740056a9b7c10313a3a5affb993346fd184c5f211a2cbdd。

## 精确冻结范围

final candidate outputs/pd-baseline-proposal/numeric-cpu-renewal-source-candidate-final.json，真实SHA a25fe05defa80cde4a9661abceac4a5995866b3234e5c77d0304ef618943219e；实际逐文件bytes/SHA与其匹配：

- tools/epd_cpu_renewal_20261030.py，1937B，821f6d48b27a83fa02c608b34b39cf2f61cd69b979dfd2e186f8449350a24d49。
- tools/test_epd_cpu_renewal_20261030.py，2842B，74e65ff68227fc402bc85a0142916cb88e8abca3a9ad7f88fde86d7382f7c710。
- run_cpu_ip2_renewal_remote.py，5514B，70d5f897d2b30cd8033ebf467cdfca5d2c796165bf2a38a193d153d0e8603118（与初审相同）。
- config19f333b99a9a9795bf97e29d278cf1947ad9484d69ca66a133b11bb32673dbb8保持；runtime_commit仍2d2f8018f3f9125ead3da169bf7ea8753141f5b9/117物理成员，未将新helper冒充runtime HEAD。新control_commit仍须Git-first精确发布并在最终审批中绑定真实值。

## B1闭合证据

helper第25行的foreign CPU/whole-node冲突检测已从row.start_ms<finish改为row.start_ms<finish+120000，工作与尾120使用同一覆盖区间；原精确新票/结束前尾120/有界seconds/fresh/错owner/CPU与整机冲突全部保留，单独GPU lane不触发CPU冲突且GPU_approved=False。CPU与whole-node共用这条检测条件。

新增cleanup-tail反例在旧实现真实失败，numeric-cpu-renewal-tail-before.log SHA98d7a32b138abe22f72f2de71ea88e6352aa0e74208bef36296f2fcc2a0cdc48，7 tests / 1FAIL。最终numeric-cpu-renewal-tail-final.log SHA9a0434b40ff5dc5659cbd2de84a34aaea3faa6f85dc11aec2b1eb1bdf4ab4eab，7独立test IDs全部PASS/0skip。日志内容与源码边界一致；本审查者没有重新运行测试。旧6PASS与初审拒绝均保留。B1已解决，无剩余blocking。

## 许可边界

仅使用用户最新明确CPU续调授权及真实本人CPU11–16票bk-20261030T0311-c71b1c22（1793329200000–1793347200000）；预约原件SHAc156dab6e7f06e7bee53d5a13722877ffd0f0ea74cd06aa9fd48aee2545bd2d1只作本次审查来源，执行仍fresh<=300秒。当前kuoli11–20 GPU合法，不能信号或使用其GPU。本批只恢复原未启动的IP2一次四场景CPU Ray诊断；无GPU/模型、无旧P0重跑、无旧PASS复用。30准备/180工作+120收口、外360+30/480观察、初360+尾120/贴main300+尾120、UID2147/boot65f/CPU50 nice10及原身份监督/UNKNOWN不重发不减。唯一run/raybaseb/port49174与config不改，若已有claim/活动/UNKNOWN先核同实例，不能另开。

双来源审批必须分别绑定实际control_commit+helper Git blob SHA和runtime2d2+真实117物理部署G3原文/manifest/terminal SHA；wrapper已绑定approval和reviewSHA、booking_guardSHA、control_commit，并对实际runtime HEAD/clean/物理源核验。发布G5和具体execution G2仍分别需要真实commit/tree/argv/payload/最终controller/FD及完整sourceproof；源G2不代替它们，也不代替真实Ray/GCS四场景生命周期G3。CPU/whole-host新冲突停止，禁止与Space model/formal并发；夜间Space完整新cohort G1及原件不改变。

NON-BLOCKING：后续可从claim或完整input原件直接追runtime/control两个commit与guardSHA，避免单commit字段歧义；无需因此修改本冻结源。QUESTIONS：无用户待答。仅本精确最终源通过，未授远端或GPU。
