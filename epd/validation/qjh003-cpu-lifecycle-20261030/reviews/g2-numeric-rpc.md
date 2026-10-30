# NumericRPC envelope组件 — 独立G2

reviewed_at_utc: 2026-10-29T19:42:59Z
reviewer: /root/gpu2_report_g4

**APPROVE_WITH_NITS / BLOCKING 0，仅父/driver envelope与单次metadata RPC源码。无完整backend、Ray/进程生命周期、部署或GPU许可。**

独立实际重算epd/runtime/numeric_rpc.py SHA `8c6ebd3c75e67662e8eed7bf0a7d15482c74f0f0cd82e4620125afa96b971816`、tests/test_numeric_rpc_cpu.py SHA `e0b737fe851000c541e4401dbb5d17a8873124ad973615c3666f47e4761a903c`，与numeric-rpc-final-tests.json一致。只读核完整源码/测试、v3 G1、已审channel和final原件，未测试/项目执行、网络、SSH、GPU或改源，仅保存本审查。

## 认可实现与范围

构造限制role parent/driver、非空受限run_id及64hex nonce。message exact keys/run/nonce、整数seq（明确拒bool）、固定action create_actor/call；parent reply还须同action、ok is True、dict result。seq只在完整响应及最终record/guard成功后前进；duplicate/错序/错ACK关闭channel并terminal FAILED，不能重发业务operation。

parent request先guard，再记录driver_request_started原始metadata，通过record返回后再guard，才channel.send；收reply后scope匹配、record finished并再次guard后返回。journal失败或耗时跨deadline均不发送新帧；reply后journal失败也不会返回业务成功。这里record是回调，尚不是实际父backend WAL接线。

driver收到严格请求后校验有限requested绝对deadline不超过调用方hard deadline，再guard、调用handler(action,argument,requested,check)、guard并要求dict metadata才发ok ACK。handler异常不发success ACK；socket/格式/scope/取消等异常均abort锁RPC+channel failed/关闭socket。close不由这个RPC调用，不篡改父release/known或停head。

每endpoint一把非阻塞Lock拒并发；拒绝并发会abort整个endpoint而不排队/重试，原在途调用随后guard失败或channel错误，符合保守failclosed设计。当前并发拒绝不是取消已提交actor的证明，父仍须依真实状态收口。

## 实际测试材料

final log实际11项distinct tests OK/0.042s，JSON11/0fail/0error/0skip与两SHA相符。本审未重跑。真实本机socketpair+fake handler覆盖两轮seq/WAL事件次序、record异常无帧、record跨时限无发送、错run/nonce/seq/action/额外key、driver不能延hard deadline、错reply后拒重试、真实EOF后terminal失败、duplicate不重执行handler、handler失败无成功ACK、并发拒绝、nonce构造拒绝。

这些不是Ray actor/真实独立进程/实际父backend registry。旧初10项与去除无意义external registry断言的资料保留；最终EOF测试只证明协议不重发，不证明外部registry已经持久化或driver死亡后的父清理已接线。

## 非阻塞限制及后续必要Gate

1. argument/result当前只要求dict，内部操作/字段尚未具体冻结。完整driver handler必须仅固定create_actor及allocate/prepare/copy/sync所需exact schema，不能把call字典当任意方法名/代码调用；真实Worker/source/profile/UUID/identity仍须独立核。
2. record和handler是同步回调，组件自身无法中断一个不返回的fsync或Ray handler；传入deadline/check及调用后guard不是任意回调已经有界的证明。具体父WAL/driver Ray call必须用剩余timeout/取消机制，真实CPU生命周期Gate验证，不能据本envelope声称整个RPC/actor执行有界。字节IO由已审NumericChannel限deadline处理。
3. 本record只有request started/finished，不能代替父create前CREATING和copy前NumericRelease.mapping_possible/fsync及其再次workcheck。对ACK丢失/返回后record失败仍需保留真实pending/依赖，不能回退ledger或重建actor。唯一36账仍在原execute，不新增授权账。
4. channel关闭/driver EOF/failed不等于CREATING quiescent、IPC mapping消失或PID/context释放。父release/head/NVML/WAL独立状态及真实失败收口必须按v3完成，未知pending不能据瞬时NVML空签released。
5. 此源未发布部署、完整backend/官方Worker/真实进程未接齐，native36 executable=false。Space3a3/已审bundle/main保持，未新增远端或GPU范围；后续Git-first/代码与实际Gates分别完成。

没有发现此精确envelope组件阻塞；APPROVE只对应上述局部范围，不把fake handler通过当生产生命周期证据。

GATE_RESULT: {"gate":"G2-numeric-rpc","decision":"APPROVE_WITH_NITS","blocking":0,"source_sha256":"8c6ebd3c75e67662e8eed7bf0a7d15482c74f0f0cd82e4620125afa96b971816","test_sha256":"e0b737fe851000c541e4401dbb5d17a8873124ad973615c3666f47e4761a903c","scope":"singleflight_metadata_envelope_component_only","GPU_approved":false,"native36_executable":false,"deployed":false}
