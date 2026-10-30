# CPU 父/driver outcome修订：失败路径复审

reviewed_at_utc: 2026-10-30T00:13:18Z
reviewer: /root/gpu2_report_g4

**APPROVE_WITH_NITS / BLOCKING 0，仅冻结本地CPU诊断源码失败路径delta。原两轮REQUEST_CHANGES保留；不代替fallback_g3完整源G2，不授发布、部署、远端CPU/Ray或GPU。**

候选 `numeric-cpu-parent-outcome-candidate.json` SHA `57dbae6669d22a87645b8a795f7e25304ad69d3b6281516829e8ed382493c582`，本人逐12文件实际大小/SHA全部匹配。关键parent SHA `a37684b1c6f7cfff26956dfbdcfa596d498c6bdc0584e1c154fee683c4b7ce30`，tests `25ad0cedc1e8bdb39bff9a2386115966030ef93ceab50232b1c796d7a420adde`；driver仍 `8d064960d39fbdd16e2dee4fb041a9ef86055a25ea43bebab66e89312f95f5e2`，其余support与前轮冻结manifest一致。本人只本地读取/解析/算SHA，未运行项目、测试、网络、SSH或GPU，未修改源码。

## B闭合

1. **detached意外死亡或GCS滞后不再假成功。** driver实际poll确认exit后，重新调用GCS reader，不能复用kill前state宣称跨driver存活。detached ALIVE还要GCS pid等于原identity，并经collector.observe/same_identity/stable真实当前PID双读，再记录包含GCS_after_driver_exit与before/after原件的存活证据。terminate返回实际outcome，仅controlled_signal_sent为True才actor_stopped。原本absent是明确False；final DEAD+原PIDabsent还必须actor_stopped，故旧no-signal通路拒绝并保留pending。
2. **controlled driver已自然退出/actor已DEAD不再当控制实验。** 控制前要求driver.poll None、GCS非DEAD且无driver-ready；terminate必须回报真实受控signal，否则失败，不能无条件stopped=True。进程在poll后自然消失也会absent/信号异常失败，而不是成功。controlled constructor真实timestamp+15秒/最少2秒余量与每次signal前window_check保持，原B2时间窗口修正未丢失。
3. terminate通过持有pidfd、实时身份检查后才signal，TERM/KILL成功返回才记录sent；已absent没有signal且outcome False。record/fsync在signal后失败会传播、保留失败而非签成功。该outcome只是“实际发送过受控信号”，不是“进程已释放”；最终仍须真实GCS DEAD及原PIDabsent，不将signal发送当终态。

新增反例确调用生产scenario循环：detached GCS ALIVE而当前PIDgone、detached absent outcome、driver absent outcome、driver自然退出、GCS控制前DEAD均拒绝。fixture driver controlled起始None，仅受控mock TERM后变-15；detached正例要求退出后新GCS ALIVE、身份取证、父actor release，再DEAD/absent。terminate本身保留独立稳定handle/absent拒绝等CPU fixtures。这些组合测试现在覆盖上轮mock恒poll0及无outcome导致的缺口，不声称真实Linux signal或Ray行为已测。

## driver/atomic/ACK接线保持

submitted、constructor、driver-ready、父ACK等复用同一atomic硬链拒覆helper；final名字在完整文件fsync之后才出现，不暴露半JSON，pending/target既有均拒绝。目录fsync失败可能留下已发布完整文件且writer失败，按失败原件保留，不重试覆盖。constructor receipt真实单调时间仍在15秒sleep前，父普通ACK只在GCS ALIVE/PID精确匹配及实际collector双读后发布，driver等≤5秒核exact expected。该ACK只限此CPU诊断，不改变GPU协议/原父唯一释放合同。

## 仍须实际Gate证明

日志 `numeric-cpu-lifecycle-outcome-final-tests.log` SHA `46af8961197f4dc9229a2de234ef5cf7048cebdf6764edf645cc9e97137b10c9`，本人核166个唯一测试ID逐项等于candidate，PASS/0skip，无重跑。它仍是Windows CPU fixtures、本机socket、NTFS发布顺序和mock Linux目录fsync，不是真实Ray、Node部分启动、父子/信号或GPU证明。

pending/无ActorID/未知identity/GCS DEAD但PID仍在时不清head；迟到scope只读inventory未知不杀，原失败材料不改。180/300秒合作式检查、Node/文件阻塞和未确认创建导致retain-head的实际预约边界仍须完整源G2与未来外层执行/清理审查；本delta没有证明能无条件300秒释放。没有新明显Ray API连线不存在的源码问题，但真实包pin/导入、worker PYTHONPATH、私有session、GCS状态与生命周期还必须在合法CPU窗口执行取证，不能以本审批准直接运行。

GATE_RESULT: {"gate":"numeric-cpu-parent-second-view-outcome","passed":true,"decision":"APPROVE_WITH_NITS","blocking":0,"prior_B1_closed":true,"prior_B2_window_closed":true,"prior_B3_controlled_exit_closed":true,"manifest_sha256":"57dbae6669d22a87645b8a795f7e25304ad69d3b6281516829e8ed382493c582","scope":"local_CPU_failure_path_delta_only","remote_CPU_execution_approved":false,"GPU_approved":false}
