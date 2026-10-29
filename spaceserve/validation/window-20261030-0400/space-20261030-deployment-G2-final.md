# Deployment helper — 两B修正后的独立G2复审

reviewed_at_utc: 2026-10-29T19:05:10Z
reviewer: /root/gpu2_report_g4

**APPROVE_WITH_NITS / BLOCKING 0；初审B1/B2闭合。仅精确源码批准，不授发布/部署执行或GPU/runtime Gate。**

原space-20261030-deployment-G2.md REQUEST_CHANGES/BLOCKING2保留，不覆盖。实际最终源码tools/deploy_space_window_20261030.py SHA `d520c64ea18e6cbcb67e1aeae2b080bad713990c5f8bf2e2426bd58226674527`、test_deploy_space_window_20261030.py SHA `e92f90e5b5902ece8011bbb99a704ef96990578718aea814f460fdff05a40609`均独立重算，与final-tests.log/json一致。只读核完整最终两源码、原审、被委托的既有migration.command_output、final测试材料，未测试/项目执行、网络、SSH、GPU、凭据读取或改实现，仅保存本审查。

## B1闭合：Git突变复用现有有界自有进程收口

bootstrap最早安装TERM/INT仅记录cancelled的合作式handler；check在Git前后、资产guard前、stage创建前与逐检出文件循环核取消/240秒工作截止。具体Git变更command不再subprocess.run，而调用从固定旧Git730对象加载的migration.command_output，timeout为剩余工作内min45，cleanup总deadline为started+360。该已审函数持有实际Popen独立session、延迟启动期信号、真实PID/start与稳定pidfd，异常/TERM在finally收口并留output/cleanup身份，随后传播失败，不进下一条Git。

外层改240秒TERM/kill-after120，和240工作+120清理准入对应；不再用短于单Git timeout的30秒killafter。正常/失败原exit记录保留，不自动回滚/重试，不以reset/clean抹去partial。源核/清单等剩余check_output仍有10/15秒只读超时，并由合作式parent handler避免原默认SIGTERM直接杀Python的缺口；后续文件循环check可停止进一步验证。原始资产/旧run不受改动。

源中仍须将UNKNOWN和partial视为未完成，最后真正Git/自有PID终态须现场readback；若外层SIGKILL、内核或磁盘故障无法收口，不得据本G2承诺绝对释放。当前是复用已审机制，不是新真实POSIX信号已验证。

## B2闭合：补齐实际调用依赖及配置的三端原字节

local verified_file循环已包含tools/control_space_temporary_cpu.py与spaceserve/runtime/configs/qjh003-20261030-0400.proposed.json，并继续核deploy/controller/window三文件；API+Git对象返回值与工作区原字节相同才继续读取cfg并发送。配置不再仅凭window部分字段核验，实际imported git/verified_file/process_identity来源也纳入指定commit/GitHub字节比对。无凭据进入源/封包。

其余原审认可保持：existing clean730严格base、用户review SHA/phase deploy、04后fresh双lane及完整prepare360、actualboot/UID/CPU50nice10、GPU2严格0/apps空、新run不存在、旧Git730 PAM/SSH guard严格复用、排他bundle大小/SHA/fsync/verify/fetch/sparse/checkout、materialized文件逐Git原字节/required paths、真实FD和Windows PIDFILETIME、UNKNOWN不杀不重发。它不是CPU suite/GPU/运行成功marker。

## 测试证据与范围

final日志实际7 distinct测试OK/0.006s，JSON exit0及最终两SHA一致。3项构造/编译/注入拒绝；新增4项从生产生成脚本AST提取真正check/command函数，在CPU注入中核实际委托的argv/45秒/同一360deadline、取消前不spawn、240截止不spawn、command_output失败只调用一次且向外传播。这些测试覆盖B1的生产接线，而非重写同义实现。

未对真实Git/POSIX信号或整个bootstrap执行作验证；测试Mock不能证明被委托的cleanup在本host已发生，仍须后续实际部署与readback。原null-byte ERROR/首版source534f、3测试资料、before-signal-fix和原审保持可追溯，不将7测试追溯套给旧源码。

精确候选清单/G5/Git-first尚须完成，不能从旧2092发布状态直接执行新helper；实际服务器入口与独立execution review、04后新API和具体commit部署也仍必需。本复审不授任何远端操作或GPU许可，不改旧封存730批次版本。

GATE_RESULT: {"gate":"G2-space-20261030-deployment-final","decision":"APPROVE_WITH_NITS","blocking":0,"closed_findings":["B1-controlled-Git-command-cleanup","B2-full-local-GitHub-helper-config-byte-binding"],"source_sha256":"d520c64ea18e6cbcb67e1aeae2b080bad713990c5f8bf2e2426bd58226674527","test_sha256":"e92f90e5b5902ece8011bbb99a704ef96990578718aea814f460fdff05a40609","scope":"deployment_helper_source_only","GPU_approved":false,"deployment_execution_approved":false}
