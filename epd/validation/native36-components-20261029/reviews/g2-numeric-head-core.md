# G2 — Numeric head 构造原语

审查者 `/root/epd_pd_followup`；UTC 2026-10-29T07:43:44Z。

**REQUEST_CHANGES / BLOCKING 1**，仅实际Node启动原语范围。不是完整backend审查，未执行测试、编译、实际Ray/进程/信号、远端或GPU。

| 对象 | 实际SHA256 |
|---|---|
| checkout/epd/runtime/numeric_head.py | 64f9190881a14a2016d91eb242bea4ab985bc3dc9beb0e967bb5aa8d92fd31d0 |
| checkout/epd/runtime/tests/test_numeric_head_cpu.py | dd9e61754e811bb146b5b4b8e3ca7dc1904c745288205822e8316a449e0e5899 |

## B1：当前线程sigmask不能单独保证Popen到登记不被Python信号异常打断

registered_spawns:42–67只要求main_thread，并在该线程pthread_sigmask阻TERM/INT/ALRM，随后Popen→append→register。Ray可能已有GCS/辅助线程；进程定向信号可交给其它未屏蔽线程，Python信号handler仍在主线程执行。默认SIGINT或调用者会抛异常的TERM/ALRM handler因此仍可能打断super().__init__返回到processes.append之间，或者打断Popen尚未返回而真实child已创建的区间。当前原语不安装/要求/核验受控handler策略，main-thread检查不是全进程信号屏障。

9个mock把mask模拟成进程全局集合，没有后台线程或在Popen内部已创建child时触发Python handler，故不能证明“controllable signal不打断登记”。后续caller有可能采用只置flag的handler，但当前接口/合同并未实现或强制这个前提；不能把它默认为安全。

最小修复：为该原语明确并落实一套受控TERM/INT/ALRM只记录取消、不异步抛异常的handler契约，在Ray初始化/构造前生效；只在Popen对象加入外部processes且register完成（或登记失败已保留对象）后由check传播取消。可以由极薄supervisor负责、原语显式要求/验证该契约，或由原语有限上下文安装并恢复；无需屏蔽全部线程、无需新框架、不要依靠遍历线程改mask。保留child恢复原mask+官方SIGINT政策，避免父handler策略污染child执行后语义。恢复handler/mask/ConsolePopen与部分失败所有权均需finally。

新增确定性CPU源码反例：FakePopen已创建child但尚未返回时触发受控TERM/INT/ALRM，handler不得抛出导致child未登记；登记/持久化完成后check取消，外部processes仍持有对象且无自动kill。真实新CPU Gate需另用真实POSIX后台线程与进程定向信号确认该路径；mock不能作为该Linux行为通过。

## 已认可

- load_runtime三官方原文SHA与2.10.0严格核，参数在导入前比较exact模板；实际address/kernel_fate_share后核，Node显式noexit/noReaper。
- services原文ConsolePopen的自定义init仅Windows分支；Linux__init__ identity检查与固定源码门槛支持当前最小subclass替换。
- child_preexec恢复oldmask后再执行官方preexec，修正父屏蔽TERM/ALRM传播问题；不修改原command/fate_share。
- callback登记失败/Node后续构造失败时外部processes已有真实Popen，finally恢复服务类与父mask；无自动Node.kill_all。SIGKILL/OS故障不承诺恢复。
- 原语清楚声明不做授权/私有目录/端口/curatedenv验证，也不做完整agent闭包或清理；这些仍必须由future supervisor在原Claim/Gates后落实。当前不能直接生产执行。

## CPU原件

只读日志：v1实际8项OK/0.004s，SHA256 `380c73a81151efbf7e2fb2967baa3e04764dc60282127d9bd95b5c47a7c5f6f9`；v2实际9项OK/0.003s，SHA256 `6038268a68a89eca9218eb23adf4b06b1be357bfeeb0381c317a8c9901afcab9`。未重跑，不外推为真实Ray/POSIX/信号行为。Space730/main/bundle不动；没有commit/push或额外预算。
