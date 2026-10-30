# CPU 父/driver整合：第二视角失败路径审计

reviewed_at_utc: 2026-10-30T00:02:47Z
reviewer: /root/gpu2_report_g4

**REQUEST_CHANGES / BLOCKING 2。仅只读第二视角，不替代 fallback_g3 的完整源G2，也不授权远端CPU/Ray、GPU或部署。**

实际读到的parent `epd/runtime/numeric_cpu_lifecycle.py` SHA `098e0bd11a88d65df03a991f3f5407f2e5661364da103d8ce0df756b9f0b5730`，driver SHA `1476e2c958510e8c0e082e45dcdf9e3113c66ae02973bf0a29ba255061326dfc`，parent tests SHA `53ea8999564d82e2af0a340ceab574ebb402fa39d078eec992dcac0a0afd6387`，driver tests SHA `72a8dfa12474957a7980b05c4ec413d96a78a053effefbf0af4b795e19bed82e`。仅本地读源/原件/日志并算SHA，无项目/测试执行、网络、SSH、GPU或源码修改。若后续源变化，本审只约束这些真实字节，需新复审而非覆盖本报告。

## B1：detached actor意外死亡也能成为场景成功

parent scenario约151–163行：driver退出后，只有state=ALIVE且actor_stopped=false才记录 `CPU_detached_survived_driver` 并由父terminate actor；随后无条件检查final.state=DEAD及原PIDabsent，并移除pending、记录成功return。

所以 detached actor如果在driver退出时就已经DEAD/PIDabsent（例如错误owner-GC或其它异常），从未跨driver存活、也未由父受控释放，仍满足最终分支，被判定与正确detached生命周期同样成功。这恰好吞掉本探针要辨别的错误行为；四场景表面完成不证明detached独立生存。

最小修正：detached成功必须先观察driver已退出时该actor实际ALIVE、绑定原PID且仍存在，并记录存活证据，再由父受控释放；未观察到该路径就失败，不以DEAD反推曾存活。最终DEAD+PIDabsent前额外要求该必经状态成立。补真实production分支CPU反例：driver已退出、首个state/final均DEAD、原PIDabsent，不得清pending/报成功；正例仍需父terminate之后才成功。不要用仅构造expected列表或mock整个scenario的测试替代此分支反例。

## B2：缺少driver-ready文件不能证明仍处于受控constructor延迟窗口

controlled分支约142–147行只检查 `driver-ready.json` 不存在，就按 `CPU_controlled_driver_exit` 终止driver。constructor-entered虽然先fsync再sleep15，但原件没有进入的真实单调时间/最早完成时刻；父也未核距构造进入的时间。如果父调度/GCS查询/进程盘点延迟超过15秒，constructor及ready可能已完成，而driver尚未写自己的ready文件，此分支仍会把事后退出当成创建返回窗口退出。文件缺失是负证据，不能承载此因果时序结论。

最小修正可在constructor-entered记录真实同host单调时间，父在pidfd TERM前再次核仍在15秒最早完成之前并留有余量/保存时间证据；越界就失败保留原件，不能默认成功或缩短延迟。也可使用其它严格、较小且可审的实际同步证据，但不能仅增加另一个缺失标志。补父被延迟到15秒窗口之后而driver-ready仍缺失的反例，以及窗口内正例，核真实production决策而非重写测试镜像。

## 已闭合与仍有边界

- create前pending先入父集合；尚无ActorID、未返回identity、场景未收口时finally先拒绝head cleanup。constructor自报身份必须与collector原父链known匹配，未知不按名字收编；无业务重试/额外inspector。这些路径没有看到误签释放或杀未知进程的代码。
- GCS DEAD但原PID仍存在不会完成场景；finally同样拒绝head收口。普通driver非零退出失败；fsync失败/身份复用/pidfd后身份变化拒绝信号，稳定handle关闭。已知pid的cwd缺失但PID仍在不当作absent。这里判据偏保守，可能留失败，不是错误释放。
- Node部分启动保存真实Popen；未注册活子进程先拒绝清理。已注册且没有未决actor时，collector再取证、raylet先停止以防新worker，再逐原身份清理，最终已知PID存在则失败。保留head的失败不是预约延长许可；实际执行审批必须有可行的边界/失败处理，不能把本报告当能在300秒无条件释放承诺。
- 180/300秒check是合作式检查；Node构造、文件fsync等并不因定义self.end自动可中断。source本身没有setitimer启动300秒硬定时器，取消handler只记状态。未来实际执行仍须经审外层监督/绝对截止与受控失败收口；外层直接杀父可能丢失子进程清理，不能据进程退出伪签整批释放。reader.close/terminal写出等finally尾部也不构成已验证硬上限。这里未运行真实POSIX/Ray，不能给该预算实际G3。
- parent未把GCS ALIVE回报pid显式与constructor原PID比较；建议在存活证据中精确核pid相同，state与自报进程都属同一个实际actor才有完整说明力。任何不一致应失败而非忽略。

## 测试覆盖的实际含义

读到final parent日志10项Windows fixtures PASS/0.037s；first10项中4ERROR是未mock Linux /proc boot读取的fixture问题，已保留，不重标为真实Ray失败。parent测试验证terminate和run finally若干拒绝路径，但 `test_four_distinct_scenarios_no_business_retry` mock整个scenario，其余ParentTests也替换scenario；未覆盖上面B1/B2生产scenario分支。整合150测试日志不改变此缺口。driver新增submitted独占回执及普通ready≤5秒父ACK属于新delta，旧组件G2不能覆盖其整合生命周期。

只看源没有发现Ray2.10命名API明显不存在；driver显式existing-head/init、父raw GCS读取与actor/driver身份接口方向一致。但实际导入/任务分发/私有session/真实GCS与创建收口尚未执行；不能把接口可读与fixtures过当运行就绪。

GATE_RESULT: {"gate":"numeric-cpu-parent-second-view-failure-audit","decision":"REQUEST_CHANGES","blocking":2,"parent_sha256":"098e0bd11a88d65df03a991f3f5407f2e5661364da103d8ce0df756b9f0b5730","remote_CPU_execution_approved":false,"GPU_approved":false}
