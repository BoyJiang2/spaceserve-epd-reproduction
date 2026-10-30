# 有限 CPU 父入口与 driver 两处接线：独立初审 G2

reviewed_at_utc: 2026-10-30T00:03:13Z

reviewer: 独立 Codex subagent `/root/fallback_g3`，按 AGENTS.md 3.2.1 接替 Claude 额度耗尽后的审查；本人未实现候选。

**REQUEST_CHANGES / BLOCKING 4。以下绑定初审实际读取的原字节；主导已收到B1并开始新版本修复，本报告不把正在变化的新源视为已审或已关闭。不得发布/部署/执行此版本CPU生命周期单元；不授GPU或native36。**

## 初审版本与证据

|源码|字节|SHA256|
|---|---:|---|
|`epd/runtime/numeric_cpu_lifecycle.py`|14391|`098e0bd11a88d65df03a991f3f5407f2e5661364da103d8ce0df756b9f0b5730`|
|`epd/runtime/tests/test_numeric_cpu_lifecycle_cpu.py`|6549|`53ea8999564d82e2af0a340ceab574ebb402fa39d078eec992dcac0a0afd6387`|
|`epd/runtime/numeric_cpu_driver.py`|7123|`1476e2c958510e8c0e082e45dcdf9e3113c66ae02973bf0a29ba255061326dfc`|
|`epd/runtime/tests/test_numeric_cpu_driver_cpu.py`|5948|`72a8dfa12474957a7980b05c4ec413d96a78a053effefbf0af4b795e19bed82e`|

已读完整父/driver/两测试、既有Node construct/registered-spawn合同、已审CPU source/GCS/descendant支持组件及本地原始日志。17份服务器静态源检查原件 observed_ms1793318168575（目录名1793318168026）逐项matches=true，与16项Ray pins+runtime_context pin相符；其scope明确只有原文件大小/SHA和optional dependency文件存在性，无Ray/optional导入/NVML/GPU。不能据此证明实际生命周期、minimal dashboard运行选择或待审父/driver逻辑无竞态。

## BLOCKING

### B1 — 排他创建JSON不是原子发布，两向握手均会读到半份回执

位置：`numeric_cpu_lifecycle.py:17–20,125–128,131–134,148–150`；`numeric_cpu_driver.py:17–20,61,82–83,115,119–124`。

原因：write/durable直接O_EXCL打开最终目标，目标名字此时已可见，随后才json.dump/flush/fsync。并发读取方以exists为完成信号，可能在完整JSON或fsync之前small_json/json.loads，触发正常调度下JSONDecodeError/错误拒绝。actor_submitted的先前WAL虽已fsync，不能使随后目标文件的发布变原子；反向parent-observed、constructor-entered/driver-ready也有相同窗口。已知pending会因此保守保留head，故不只是无关日志格式问题。

最小处理：共用同目录、owned/O_EXCL临时文件完整写入+fsync，随后用拒覆原子发布（例如os.link临时文件到最终名，再持久化目录/移除临时名），确保最终名一旦可见，字节已完整；原目标存在必须拒绝，不加业务重试。增加暂停于写入/fsync期间的有意义反例：最终名尚不可见，发布后字节一致，旧目标不覆写，fsync失败不发布。父/driver两向及constructor回执统一使用该合同。

### B2 — parent-observed没有证明当时的活PID，也未将GCS PID绑定到constructor PID

位置：`numeric_cpu_lifecycle.py:123,132–150`。

原因：self.poll会收集时点原件，但collector.known刻意保留已absent PID历史。随后known.get/字段相等仅证明曾登记，不证明ACK时当前仍活。normal分支只要求GCS state=ALIVE；GCS可暂时仍为ALIVE而原PID已消失，而且state.pid从未与constructor绑定的identity.pid核对。这样仍会写parent-observed，driver把它当“父已绑活PID”自然退出，与新握手的目标不符。最终DEAD+原PIDabsent检查不能补证此前ACK时活身份。

最小处理：在发normal ACK及声明绑定之前，对已登记identity重新取得实际前后稳定snapshot，核UID/start/boot/root/run/当前身份及GCS pid精确相同，期间消失或不符保守失败；仍保存known历史，不能通过删除历史来掩盖。增加known已absent但GCS仍ALIVE、GCS PID不符、两次snapshot期间消失/复用的反例，确保不发ACK。

### B3 — detached场景未经历survival/父释放也可能被报成功

位置：`numeric_cpu_lifecycle.py:151–163`。

原因：driver退出后，detached只有state=ALIVE才记录CPU_detached_survived_driver并由父terminate；但若第一次/最终GCS观察已DEAD且绑定PIDabsent，代码直接清pending并return，完全不要求actor_stopped或survival证据。这会把“detached意外随driver死亡/自行失败”当通过，四场景行为区分失真，也无法支持该取证单元为后续driver策略提供预期证据。

最小处理：每种场景显式检查其终态前必经事实。detached必须在driver实际退出之后记录同ActorID/已绑定活PID的ALIVE存活，再记录本次父身份绑定的释放intent/动作及最终DEAD+原PIDabsent；先DEAD等不符结果记录真实异常并失败，不自动转成功。增加detached直接DEAD、ALIVE但PID不符及未完成父释放的反例。non_detached的正常owner退出行为仍单独解释，不能把detached条件套给它。

### B4 — controlled分支仅以缺少driver-ready推断创建返回窗口，负证据不足

位置：`numeric_cpu_lifecycle.py:109,141–147`；`numeric_cpu_driver.py:61–62,85,114–115`。

原因：constructor延迟15秒、driver-ready不存在，不足以证明父发TERM时constructor/ready返回仍未完成。driver可以已从ray.get返回、正在处理/写ready之前被抢占；父仍看到没有文件并记录controlled exit，实际却是返回之后退出。actor-submitted/constructor-entered只证明提交/进入，未把受控退出点固定在未返回阶段。排他JSON原子发布修复也只解决半文件，不消除这个语义窗口。

最小处理：用有限CPU-only明确阶段握手/受控constructor栅栏，使待测返回前状态在父发出受控退出之前保持并有正证据；若未在该阶段完成控制则失败，不凭文件缺失认定命中窗口。保持固定预算、一次创建、零业务重试，不patch Ray生命周期hook。增加driver已返回但ready尚未发布的反例，及父未及时控制时不得冒称窗口命中的测试。

## 已认可的局部改进与测试边界

- pending在Popen之前的父WAL后加入，并要求ActorID/构造PID绑定后才考虑GCS终态；UNKNOWN/pending、DEAD但PID仍存在阻断head清理。稳定pidfd开后再复核身份，fsync intent失败不信号，直系Popen保留并poll/reap，均是正确方向。上述B不要求放宽这些检查。
- Node从首GCS实际--log_dir推导唯一session，再冻结collector；子driver的-I loader显式插入受控script目录；独立180工作/120清理边界与四种场景单次枚举保留。其真实超时、外层监管、CPU票/边界及失败残留交接仍须具体执行G2，不由源码名字“finite”自动证明。
- parent first原始日志10例中6OK/4ERROR，错误为Windows fixture调用真实/proc boot；final10OK/0.037s。fixture补Linux接口不等于弱化生产身份检查，但这10例没有执行完整scenario轮询/两个进程握手。driver-stage8OK/0.051s与parent-handshake8OK/0.048s为同一8个scenario/constructor fixtures；后者也没有实际跑driver main五秒等待环，不能把它们当新主握手并发证据。
- 日志SHA：parent-first `00b1e40f418a234e959b32799d524f9a451ee7f62cf5c68f7c43e62bc6633d4e`；parent-final `ae9f441c540e042d4c2c27a46a11b8db18fb54c46a4399f01295f2458885bab3`；driver-stage `5a4fa9366112310749ffc4626ff112bfddd562f7fbacd034273fabfdaed7e331`；driver-parent-handshake `4b9bc5af5da28182ec9d86ca337677f8ed11acf67ff37daeee6351fbf2daa912`。均为本地mock，无真实Ray、信号、GCS或GPU运行。

## NON-BLOCKING / 后续限制

1. 未知/pending拒绝head清理不等于已收口；外层必须保留真实残留/身份和有限监管交接，不能把FAILED_RELEASE_UNCONFIRMED当后续资源使用或无限占用许可。不要为通过测试改成按UID/名字/进程组清理，亦不泛用ray.kill。
2. 最后known PID列表不是完整未来quiescence证明。停止raylet后潜在未知后代/重挂父、所有源根/子身份、迟到创建和实际释放须在真实Gate持续取证；成功terminal不能只引用known absent而泛称全head闭包已证明。
3. record/文件读取/第三方初始化的合作式check不能单独保障所有阻塞调用300秒内返回；最终独立执行transport/父监督合同须绑定实际deadline、取消和已验证身份清理。端口/目录fresh、实际env/pth/解释器、17pins运行时重核与minimal分支仍是后续具体执行范围。

## QUESTIONS

无须用户变更实验设定。请提交新四源码/新增原子发布组件与反例的精确SHA和原始日志，再做delta复审；原报告、旧G2和真实失败保留。其他审查者发现的同类问题可合并修复，但不能把待改动视为本初审已通过。

本审仅用本地Node文件API读取/计算SHA，未运行项目或测试、shell命令、网络、SSH、GPU、信号或修改源码，仅写本初审MD/JSON。

GATE_RESULT: {"gate":"G2-numeric-cpu-parent","decision":"REQUEST_CHANGES","passed":false,"blocking":4,"findings":["B1-nonatomic-exclusive-JSON-publication","B2-no-current-live-PID-and-GCS-PID-binding-before-ACK","B3-detached-DEAD-can-pass-without-survival-and-parent-release","B4-controlled-window-inferred-from-missing-ready-receipt"],"scope":"original_parent_098e0b_driver_1476e2_only","remote_CPU_execution_approved":false,"GPU_approved":false,"native36_executable":false,"real_lifecycle_passed":false}
