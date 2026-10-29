# G1 补审 / G2 复审 — Node 启动取消协议

审查者 `/root/epd_pd_followup`；UTC 2026-10-29T07:49:39Z。

**G1补充 APPROVE；G2复审 APPROVE / BLOCKING 0。** 初审B1在本启动原语范围关闭。原G1 v3中“暂阻TERM/INT/ALRM后登记”的实现选择由当前非抛异常取消协议替代；不修改旧计划/初审原件，不批准实际执行或完整backend。

| 精确对象 | 本轮实际SHA256 |
|---|---|
| checkout/epd/runtime/numeric_head.py | d05db0fb496f4308b667f22a00bc2f3e295a2a7f08b41416dae91717da3a4811 |
| checkout/epd/runtime/tests/test_numeric_head_cpu.py | a79f83dbb814912ab12ed961b43735f063d66bba343d6e887f0eed3e98286a06 |

## B1 闭合

construct_node在load_runtime之前进入deferred_signals，为TERM/INT/ALRM安装只向集合记录信号的remember；后台线程转交Python handler也不在Popen内主动抛异常。RegisteredPopen返回后先加入外部processes、register绑定/持久化，再controlled_check传播取消。callback失败时真实Popen仍保留。controlled_check还拒绝受控handler被替换；调用者已有TERM/ALRM屏蔽则启动前拒绝。服务类和原handler在finally恢复。

不再改变parent/child mask，也不包官方preexec；实际Ray的SIGINT策略保留。此改动比跨线程屏蔽更小，解决初审Popen已创建但被异步handler抛异常中断登记的具体问题；不声称处理SIGKILL/OS不可恢复故障。后续完整supervisor仍须在构造前后保持连续、只记取消的受控handler和统一check/收口，不能把本局部上下文恢复旧handler后就当整个unit信号生命周期已完成。

G1设计层认可这种替换：直接Node/noexit/noReaper、固定版本/源SHA、实际Popen归属、后代闭包、1680+120/故障终态和原预算都不变，不改native IPC，不新增控制框架。

## 先失败后通过的原件

只读主线程两份原始日志，没有重跑：

- `numeric-head-background-regression-before.log`，SHA256 `1c71c0860c98dcafd99706750822c2964eb18784af25eb78d8b8f1078de2b3e7`：1项实际FAIL，FakePopen已created1但processes为空，保留原失败。
- `numeric-head-cpu-tests-v3.log`，SHA256 `2e8cdbb8bd574d05c5328c17a5ba8af82c55a3dea2bd51fde3b32ae6ac67e765`：10项CPU-MOCK、0.004s、OK。新反例在FakePopen内部、构造已发生且尚未返回时直接调用受控handler；之后processes及registered都保留该对象，服务类/原handler恢复。此模拟重现Python回调交付时机，没有声称真实POSIX后台线程已测。

## 范围与发布边界

认可仅本地启动原语及测试源码。没有实际Ray/POSIX子进程/信号、Linux运行时源码SHA门槛、NVML/CUDA或GPU证据；原Claim准入、curatedenv/私有目录端口、实际身份callback、supervisor/daemon后代与pidfd/IPC清理、完整36生产分派仍未接齐，不能称可运行native36。

用户新授权适当上传代码，独立`epd-native36-preparation`分支发布这些已审准备组件及真实日志/局限的方向在设计范围内；**本审不代替该branch精确tree的G5或实际push/API字节验收**。main/Space730及已审bundle不动，不新增执行许可。审查者未修改实现、测试/编译、网络/SSH/GPU或push。

## G2 fixture 最终一行增量 — 2026-10-29T07:51:42Z

**APPROVE / BLOCKING 0**，最新test_numeric_head_cpu.py实际SHA256 `fbdde2bed29261efe8f3149cd4023cf5be940b9c13a7ad70fbfb1cd6fe10c617`。本轮把当前文件仅反向替换`Path('/CPU-MOCK-n36')`为旧`Path('C:/CPU-MOCK-n36')`后在内存重算SHA，准确得到上一轮`a79f83dbb814912ab12ed961b43735f063d66bba343d6e887f0eed3e98286a06`，证明确实仅此一行字节增量。该路径只传给参数验证/FakeNode，不创建根目录；新写法避免Linux把C:当相对路径再拼cwd造成过长。

numeric_head.py仍实际SHA `d05db0fb496f4308b667f22a00bc2f3e295a2a7f08b41416dae91717da3a4811`。主线程新原件numeric-head-cpu-tests-final.log实际10项/0.004s/OK，SHA `2e8cdbb8bd574d05c5328c17a5ba8af82c55a3dea2bd51fde3b32ae6ac67e765`（内容与前一10项日志同字节，分别保留，不凭同hash合并为一次执行）。本审未重跑，未实际Linux验证。

此增量不改变上文组件/Gate边界。精确publication tree须交另一独立G5审查者；本审不签发布tree、不执行push，main/Space730不动。
