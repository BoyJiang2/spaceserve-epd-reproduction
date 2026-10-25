> GitHub阅读副本：仅修正链接；[封存原文](../../../../../../outputs/epd-profile-a/reviews/prompts/g2-profile-instrument.md) SHA256 56d340826821f79e4acec0dd02e30f322332f853836d6f1182bef2b731482b37。原数字及解释不变。

独立只读G2源码打点审查，不执行命令、不改文件、不访问GPU/凭据。项目根 D:/Documents/codex/2026-10-23/new-chat-2。
仅Read outputs/epd-profile-a/scripts/observe.py 和 instrument.py，必要时窄读 evidence/instrumentation.patch。共不超过4次读取，输出限1000中文字。代码只改 /local/boyjiang/epd-profile-a-20261023 的独立源码副本，旧环境/模型/build只读链接，不改通信。CPU测试已通过：off装饰返回原函数、不使用NVTX，sync/async平衡、补丁全部compile后统一写入、二次应用拒绝不改、真实FastAPI Request注入和disabled拒绝capture。
分别核查opt-in语义、异常/异步、CUDA捕获可关联的request/stage/marker、源码插入是否改变推理/采样/原时间戳；不要把future GPU预检当已通过，Nsight真实子进程kernel覆盖留G3。CPU范围不代表GPU完成；engine_common的同步remote_call范围只标提交，不标await完成。
只给此打点子范围G2结论 APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES、BLOCKING（文件行号与理由）、建议/疑点；启动/压测另审，不能因未读runner否决本子范围。
