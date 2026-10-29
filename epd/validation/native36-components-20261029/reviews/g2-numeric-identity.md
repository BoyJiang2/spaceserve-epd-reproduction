# G2 — numeric identity 最小接线源码审查

- 审查者：`/root/epd_pd_followup`；独立只读。
- UTC：2026-10-29T07:07:45Z。
- 结论：**APPROVE / BLOCKING 0**，仅当前身份parser/worker桥接与CPU-MOCK测试源码范围，不是完整numeric backend或实际head证明。

## 精确源码

| 路径（相对checkout/epd/runtime） | 本轮实际 SHA256 |
|---|---|
| production_identity.py | 8af60cd898eae281546e0cb21e8b695521524309debf229c6ed22da1276dc608 |
| tests/test_numeric_identity_cpu.py | 0d3b31a6e9104ad43bcfa519bddbbf7e13a939f103eba4e3baf6d5f6b9a6d4f2 |
| tests/test_production_identity.py（既有HTTP回归，只读） | 52fcd9a029de7177757955f17fc5de9e6ff125f8a06613dd43187ebda51359ad |

实际git diff限定environment的新numeric分支、worker DECODING约束和HTTP publish/assemble入口护栏，原普通HTTP URL、source/root/profile/UUID及ownership校验保留。未改模型、IPC、预算或清理。

## 关键检查

- numeric flag仅接受0/1；模式1仅接受canonical `gcs://127.0.0.1:<port>`。netloc全等拒绝userinfo、其它host、非规范端口写法，urlsplit.port拒绝非法/越界端口，额外path/query/fragment拒绝；HTTP/ray协议拒绝。普通模式仍只接受原HTTP loopback。
- numeric请求diagnostics不能启用，返回env保留numericflag且输出diagnostics0。requests_enabled沿用原缺省0语义；backend启动环境应显式给0，不能声称本parser要求该环境键必须存在。
- numeric非DECODING在torch导入/身份采集前拒绝；实际UUID仍来自device properties并对批准三UUID检查，不拿Ray rank当UUID。DECODING本身不证明未加载模型；无模型Worker policy由既有numeric_cache及后续backend负责，本补丁未作此越权证明。
- publish_service/assemble_services在任何写入/sidecar汇聚之前拒绝numeric（及非法numericflag），避免GCS标签被当HTTP服务。普通HTTP分支保留。
- 新6项CPU源码使用受控EPD_CPU_TEST_TMP，mock CUDA属性/sidecarcapture，无Ray、Torch、NVML真实初始化；覆盖地址/诊断/source拒绝、普通HTTP拒GCS、HTTP服务无写入、非DECODING前置拒绝、observed UUID与GCS标签传递。既有9项HTTP测试仍覆盖实际profile/CLI、UUID、TP1 localbaseline、route和manifest ownership。

## 原始测试日志如实区分

此审查未运行测试。只读取主线程已有两份日志：

- `numeric-identity-cpu-tests.log` SHA256 `efb5d13128a2b4f75f5b2f441540bfb0b949f0e813e1243d0b4db66437265cab`：15项，14 PASS、1 ERROR；报错位于HTTP assemble_services的sidecar owner检查。保留，不改写为通过。
- `numeric-identity-cpu-tests-v2.log` SHA256 `a58da18cbb8eb136289bae9a401d1ae4415a6093b34264b330697e61c7a5ce50`：同6新+9原15项，全OK，0.052s。主线程报告launcher将Windows模拟getuid从2147改为本地fixture st_uid；日志及源码diff不显示production ownership约束被放宽。本审没有独立重跑或独立证明launcher的具体执行命令，只核实当前原始日志结果和源码约束。

这些是本地CPU-MOCK结果，不是Linux/Ray/POSIX/CUDA/NVML或实际GPU验收。

## 明确尚缺的生产证据

owned-head原件与GCS地址匹配、supervisor/daemon身份闭包、映射WAL先于copy、36vector与claim、按依赖有界释放及真实生命周期Gate均属后续backend接线。本parser不能通过自填env签actual head proof；完整生产入口仍须failclosed。预算与0HTTP请求不变，selected360仍待接齐。暂不commit/push、不改变Space730/main/bundle。本审未改实现、未测试/编译、未网络/SSH/GPU或发布。
