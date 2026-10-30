# NumericChannel字节framing组件 — 独立G2

reviewed_at_utc: 2026-10-29T19:36:20Z
reviewer: /root/gpu2_report_g4

**APPROVE_WITH_NITS / BLOCKING 0，仅小型有界字节framing源码；不授envelope/父backend/driver/GPU或部署。**

独立实际重算epd/runtime/numeric_channel.py SHA `3719731d885f9a92838485d2a6b8d11cdea8350267ac740d91eea44f1cd656a8`、tests/test_numeric_channel_cpu.py SHA `ec91ea6d04da5d760247dfaafd093a7292ba8536ab2cadc369062e3f681332dd`，与numeric-channel-final-tests.json准确一致。只读核完整源/测试、v3精确G1和final日志/JSON；没有执行测试/项目、网络、SSH、GPU或改实现，只保存本审查。

## 认可实现

构造时拒blocking socket。send先核有限单调deadline/取消，再以ensure_ascii=False/allow_nan=False编码UTF8 JSON object，按实际编码字节限制1..1MiB，4字节network-order前缀；receive先exact4字节前缀，长度合规才读限定body，不读取至EOF才决定大小。

_transfer每轮以_remaining检查failed/check回调/有限deadline和当前monotonic，select上限50ms，select后再次核时限；send/recv均nonblocking且每次最多65536字节，实际count推进offset。BlockingIOError/InterruptedError只续当前帧剩余字节，不重发业务operation。recv空块/send0为EOF；半帧、背压或数据不足仍有机会检查截止与取消。收齐后再查deadline，receive解析之后亦再查deadline，避免已超时仍返回结果。

严格JSON拒重复key、NaN/Infinity常量、浮点溢出1e999、非object、无效UTF8及尾随JSON。send编码/长度错误、receive帧/解析错误和任意BaseException均将channel锁failed并关闭socket；failed状态再调用不发新帧。没有Ray/Torch/NVML导入、进程操作、WAL/ACK假造或GPU权限。

这满足v3 framing设计中的非阻塞机制，较旧Connection poll/recv方案实际收窄了半帧/背压风险。

## 实际测试原件

final日志实际10项distinct tests OK/0.164s，JSON10/0fail/0error/0skip/两SHA一致。本审没有重跑。测试使用真实本机Windows socketpair：短send3/recv2通过薄wrapper仍调用实际socket；1字节分帧线程发送；无人读取的1MiB级send背压到deadline且failed不能重发；partial header/body EOF；0/超限prefix；duplicate/NaN/1e999/array/无效UTF8/suffix；部分帧中取消；错误send值/非有限或过期deadline；blocking拒绝。不是Mock poll的同义复刻。

这些只证明本机字节IO及错误处理，不证明实际Linux继承fd、独立进程/信号、Ray/actor/IPC生命周期；所存GBK测试文件编辑错误是本地读取工具错误，final JSON如实说明，不能称一次目标测试失败或GPU运行。

## 非阻塞限制与后续接线条件

1. 本组件不核run/nonce/seq/action/payload精确键或父WAL，也不创建业务ACK。后续envelope必须严格绑定，WAL fsync且再次workcheck后才send；不能把收齐JSON当业务成功/36完成。发送前仅接受内部有限metadata/纯JSON值，禁止把任意自定义Python对象或巨型结构交给json.dumps；wire上限不是任意调用输入在编码前的绝对内存/CPU限制证明。
2. 私有socket的nonblocking属性在使用期间必须保持，不能由别的拥有者切回blocking；实际父/driver继承端点/无未知连接由完整接线验证。本构造拒blocking时未接管/关闭该输入socket，调用者仍须在失败finally关闭自己的端点，不能据本G2宣称无FD泄漏。
3. framing失败关闭channel不证明driver、已发送create/copy或CREATING已经quiescent。父依赖/WAL/known必须独立保存，partial actor/未知pending按v3真实证明或FAILED_RELEASE_UNCONFIRMED；不得据socket关闭/driver EOF/NVML暂空签released或停head。
4. 当前测试没有整个业务transport/client server或真实进程取消，仅字节层；后续实际CPU-only Ray和GPU入口继续failclosed，完整backend/官方Worker/probe/生产dispatch/Git-first另审。Space HEAD3a3/已审bundle/main不动，不并行正式GPU。

未见此精确transport组件阻塞；本批准不缩减整体目标或把组件当native36已实现。

GATE_RESULT: {"gate":"G2-numeric-channel","decision":"APPROVE_WITH_NITS","blocking":0,"source_sha256":"3719731d885f9a92838485d2a6b8d11cdea8350267ac740d91eea44f1cd656a8","test_sha256":"ec91ea6d04da5d760247dfaafd093a7292ba8536ab2cadc369062e3f681332dd","scope":"bounded_local_byte_framing_component_only","GPU_approved":false,"native36_executable":false,"deployed":false}
