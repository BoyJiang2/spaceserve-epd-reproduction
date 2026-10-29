# 04点部署恢复：窄user-service源码 — 独立G2

reviewed_at_utc: 2026-10-29T20:27:04Z
reviewer: /root/gpu2_report_g4

**APPROVE_WITH_NITS / BLOCKING 0，限新窄例外与精确deployer接线源码；不批准部署重试、CPU phase、GPU或formal。**

独立实际SHA重算四文件与guard-tests.json一致：
- tools/space_user_service_guard.py `48fe3fc2bf9d4070f48db6b60b44671c40761850014f650a0f54b82678c357fd`
- tools/test_space_user_service_guard.py `ad3e238d2c62f6774cd569916b92a7b9b39e141ae7dba675eaaa17dcfd80d8e8`
- tools/deploy_space_window_20261030.py `376611bf221b63196b97f7311800d6b377f3eb21af9e78ab598aafd63412f956`
- tools/test_deploy_space_window_20261030.py `470dcb3e292bef7aadaa3498bfca1fb4c99345feb80624c445a0092230b43f66`

只读核四源码、space-0400-deploy-recovery-plan/G1、原失败与后续unknown-cwd-diagnostic、旧730 materialize.guard_processes/PAM/SSH分支及两组测试材料。没有测试/编译执行、网络、SSH、GPU、凭据读取或改实现，仅保存本审查。

## 认可的精确结构范围

新read_identity只读取选定proc身份；folder实际st_uid先核，再从stat最后右括号后的字段正确提取PPID/start_ticks。comm只去末尾空白，cgroup完整原文/换行与cmdline SHA精确核。snapshot要求PAM child→UID2147 user systemd parent→固定root PID1链；父exe成功resolve且恰/usr/lib/systemd/systemd，child/root exe不是必需字段，与诊断实际PermissionError和G1明确必需范围一致，不虚构取得它们的exe。

validate核boot65f、child/parent UID2147、精确comm/cmdline SHA/cgroup、PPID实链，parent PPID1/exe，PID1 UID0/PPID0/comm/start856/cgroup/cmdSHA固定锚。child/parent PID为正整数>1且不相同、start为整数且child>=parent>=856，允许同tick不额外假定间隔；snapshot前后全结构一致才返回原结构和确定性SHA。必要读取失败、属性不符、PID复用/字段变化均无吞错fallback。

诊断中的3831927/3831926/PID1上述UID、hash、cgroup/parent exe与源码常量吻合；这支持结构候选，不证明未来现场通过。原3818273已gone，仍UNKNOWN，不追认为PAM，也不把第一次失败重写成功。结构例外不是按名字或任意UID/PermissionError豁免。

## cwd扫描及源码接线

新guard_processes临时保存并绑定assets.pam_exception：优先旧固定PID例外，只有其返回None才尝试新精确结构；assets.guard_processes保持旧扫描，finally恢复原callback。旧扫描只有cwd.resolve真实PermissionError分支调用PAM例外，可读且项目内cwd仍先抛Project cwd active，未知非PAM仍按原SSH例外/未知拒绝，原SSH条件不变。

callback绑定是显式属于新发布工具的程序接线，不是服务器磁盘私改旧730模块；不能声称旧730逻辑完全未变。deployer三处（写stage前、fetch后变更checkout前、最终检查）明确调用新guard包装，旧730 module仍由Git对象内存加载，新guard从指定新commit原件base64经已审FD完整wire绑定提供；local API逐原字节列表包含新guard，server不从任意路径导入未审文件。

deployer仍严格clean730 base/newrun与stage不存在、actualboot/UID/CPU50nice10/GPU2严格0/apps空、fresh双lane/full360、单次排他bundle/claim、已审command_output受控Git变更和240+120、不reset clean、不删旧run/资产/系统服务。新source及bundle须单独G5/指定新commit后执行，不能套旧3a3/04efa执行审批。

## 测试原件实况与未外推范围

guard-tests.json/log记录11本地结构/回调fixture PASS，四精确SHA相同；existing-tests记录28既有本地tests PASS。fixtures核精确结构、child/parent/root关键字段异常、boot、两读改变、原结构/SHA返回、非PAM None、callback success/failure后恢复、可读项目cwd仍拒及invalid exe不能豁免。没有实际/proc或服务器调用，本审未重跑。

未单独构造read_identity解析真实proc树、必要字段读取PermissionError、旧PAM成功后不触新分支或实际SSH回退的集成fixture。源码明确不吞这些异常，故不作为当前源码B，但实际执行前须在现场重新双读核，并在部署实际审计中保存完整exceptions；不能将11+28本机结果当这些真实身份已经验证。

## 后续条件

仅允许按已审G1准备新恢复源码发布。精确G5/Git-first/新bundle、新独立执行审批及fresh实际票/源/boot/idle/baseclean/新run stage不存在后，才可批准一次恢复；本G2不代替执行Gate。不改系统服务/驱动/预约、不信号不明进程，不自动重复旧命令。再失败/partial/UNKNOWN保留并重新评估，不循环重试。

原首次stderr/exit/readback、gonePID UNKNOWN与当前诊断均保全。06:37前具备formal201门槛以及全新CPU/numeric/313/Gates仍保持，不为恢复缩减；此源码批准不授GPU或整体目标完成。

GATE_RESULT: {"gate":"G2-space-0400-recovery-source","decision":"APPROVE_WITH_NITS","blocking":0,"guard_sha256":"48fe3fc2bf9d4070f48db6b60b44671c40761850014f650a0f54b82678c357fd","guard_test_sha256":"ad3e238d2c62f6774cd569916b92a7b9b39e141ae7dba675eaaa17dcfd80d8e8","deployment_sha256":"376611bf221b63196b97f7311800d6b377f3eb21af9e78ab598aafd63412f956","deployment_test_sha256":"470dcb3e292bef7aadaa3498bfca1fb4c99345feb80624c445a0092230b43f66","scope":"narrow_user_service_exception_source_only","server_recovery_execution_approved":false,"GPU_approved":false,"formal_approved":false}
