# 临时空闲路径runtime G2

初审结论：REQUEST_CHANGES；BLOCKING2。reviewed_at：2026-10-29T05:11:57Z。仅本地runtime候选审查，不授controller/部署/CPU辅助scope或目标GPU启动许可。审查者未参与实现，未运行项目代码/测试、网络、SSH、GPU、signal或affinity操作；只读取源码、gitdiff、已有日志并核SHA，按请求保存本报告。

## 冻结证据

integrated-result.json SHA256d0c72372b3e81cea1a06c2a42335450f294cb864e4497108306c000b73caae05；当前7源逐SHA与该记录相同。原日志38PASS/0skip/0.143s、exit0，只是WindowsCPU mocks，不能认证实际GPU PID/MPS归属、线程监测时延或目标部署。source-files为84个唯一path，所列source均存在。

- reproduction_paths.py：9901fb6f43c094a6f298af360a289f8222f56443072c58ad5b7f92b8e6ed45cc
- tests/test_reproduction_paths.py：9811f89218a9a9d4d44957fd3bc0b7145887ab49c64e870510a319f4fb156f1e
- configs/source-files.json：8bc39663973ecb5c5f93f4250dd2c352ed79501422050cbeac1038d0c418678d
- scripts/temporary_gpu_use.py：3bcdb04671dd46fb6682017a0e302d7a989f9012a450d2fcade5f21313d469ba
- scripts/test_temporary_gpu_use.py：6dd1dd4f86fcc4c26df891ddb27be25e073bc1cd6c77ccecfc7aa5c29544bb4b
- scripts/booking_window.py：aeaf77876c935dcddd4b13533d38404e8d75233f8bbfeff5e44df08034cdbb45
- scripts/resource_guard.py：46d5e8a749256491a99ca25f29037f42c46a49554f66e2f58e1b747f04eeefc6

## 必须修正

B1：temporary_gpu_use.py:64–78的MPS归属闭包不足。当前只检查ENV的root/runid、token/pipe及state为starting/running，未核owner记录的PID/ctime/UUID、实际daemon身份及私有control端点inode。现有test_owned_identity_reuse_and_private_mps甚至以仅state/token的JSON作为可接受owner。这样不能称“真实私有MPS owner闭合”。最小修正：依据真实owner记录确认daemonPID/start/UID/UUID/token/pipe/control inode；GPU query若返回MPS server而非control daemon，还须核其实际父链到该已确认daemon，前后身份一致。缺字段、复用、错UUID/inode、无关server或无法读取一律unknown→只请求当前自有监督器停止，不能向queryPID或外部MPS发信号。加入逐字段错值及实际server/daemon区别的CPU-mock负例，勿放宽原mps_owner全局保守拒绝。

B2：temporary_gpu_use.scope:20与booking_window.require:57–60未拒混合scope。若同时存在非空booking及temporary_gpu_use，公共require_scope接受booking，booking_window却直接优先temporary分支，不验证ticket。这与“真实ticket/direct grant不混用、原booking行为保留”的设计不一致。direct路径应明确要求booking为None/缺失；两种非空scope同时出现应在任何查询/marker/线程/signal前拒绝。新增混合配置拒绝及原booking独立回归测试，不能仅依赖后续自签approval文件说明是哪种权限。

## 其他逻辑检查

已明确限制Space numeric/model、GPU2/UUIDc005/boot65f、CPU0–89、≤60分钟、原用户文字与G1/G2文件SHA、冻结config/source及独立TEMPORARY证据；formal/EPD无票临时scope拒绝，未伪造BOOKING_VERIFIED。start marker采用独占写及monotonic/wall最小剩余量，不由正常require调用续时；篡改deadline数学关系会拒绝。phase fresh idle证据独立保存，失败保留，不偷换成预约ownerPASS。

resource_guard在code_identity后包裹supervise；model的phase参数正确传递，原host/projectlocks及finally/MPS停止未删除。后台监测独立于blocking请求，process_rows有.5秒超时并保存partial/error；foreign/unknown/授权失效将记录触发，只os.kill当前自身PID。正常context退出stop/join，join失败不签PASS。代码未向nvidia-smi返回的foreignPID发信号。

监测raw日志、查询超时和failure列表的mock可支持基本接线，但不能证明真实/proc读取始终有界或MPS启动过渡可识别；join2秒后仍存活daemon线程应按原失败/有界controller收口，不得继续下一Gate。CPU部署wrapper尚未接线，fresh原始用户授权/新scope/CPUprofile/Git闭包、当前GPU2idle、实际线程监督与完整新numeric/313G3均未成立，不能凭本报告启动目标任务。

G1对直接用户条件授权覆盖本地本人票限制的判断不变，不额外推导管理员审批；本次请求修改的是实现闭包，而非撤销已明确用户授权。固定GPU2没有空闲即停止，不扩卡、不改他人任务；他人仍在GPU0/1运行时只能做机制预检，不产正式公平性能结论。原GPU0PASS不转授，formal不在临时路径范围。

GATE_RESULT: {"gate":"G2-temporary-idle-runtime-source","decision":"REQUEST_CHANGES","blocking":2,"reviewed_at":"2026-10-29T05:11:57Z","runtime_candidate_only":true,"target_execution_authorized":false}

## B1/B2关闭与最终源码结论

复审reviewed_at：2026-10-29T05:14:01Z。**最终G2：APPROVE_WITH_NITS；BLOCKING0，仅runtime候选源码及本机mock证据。** 初审两项B及对应旧失败保留，不追溯改写。

B1已关闭：MPS现在仅接受完整running owner，核daemonPID/ctime/UID/name、固定UUID、pipe/token/root/runid、CUDA_VISIBLE_DEVICES及control inode；查询server须有真实祖先到该daemon，daemon/server用新的Process对象再核ctime。缺字段、错ctime/UUID/pipe/inode、无祖先及PID复用均拒绝。全局MPSstart保守拒绝未改，监测仍只signal自身控制器。新增缺metadata反例在旧实现真实FAIL（RuntimeError未抛）；该反例现在保留，完整daemon/server正例和错值/父链负例加入CPU-MOCK。

B2已关闭：scope在任何查询/marker/monitor前明确要求config.get('booking') is None，非空booking与temporary混合即拒绝。旧实现的混合scope反例真实FAIL（ValueError未抛）；修后负例进入整合suite，原booking路径仍保留。

当前7源逐SHA与temporary-use-local/fixed-result.json相同，receipt SHA2563e40c233c6c35494aa0f36f918552e802eec7a89566533a6eeb51a6d90bb4867。实际日志38PASS/0skip/0.147s、exit0，仅Windowsmocks。最终temporary_gpu_use.py SHA256aa88be9acf01db9de7268ef949b4a63952f23bad4ceb4eed61c99f1907de4468；test_temporary_gpu_use.py SHA256b20ce420fa128d593316aa9ff159687c1cf0b7b8f8b0ba153ef00ce813ce9216。其余5源维持初审上列SHA，84成员闭包不变。本审查未重跑这些测试或执行项目代码。

剩余边界不变：真实MPS parent/proc权限及监测时序尚未经目标验证，严格拒绝可导致实际启动安全失败，不能为通过而放宽未知归属。CPU辅助授权/部署wrapper尚未实现和审查，本次不批准整条controller、不授部署或当前GPU执行。后续还需G5/Git-first/精确目标source与CPU验证、freshGPU2idle及实际新numeric/313独立G3；绝不伪造BOOKING、继承GPU0PASS、扩卡、清理外国PID或启动formal。

GATE_RESULT: {"gate":"G2-temporary-idle-runtime-source-final","decision":"APPROVE_WITH_NITS","blocking":0,"reviewed_at":"2026-10-29T05:14:01Z","runtime_candidate_only":true,"full_controller_or_target_execution_authorized":false}
