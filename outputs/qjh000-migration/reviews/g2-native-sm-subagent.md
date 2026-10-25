# G2：qjh000原生SM与有限运行时探针

实际审查者：独立subagent `/root/profile_runner_review`。接替原因：Claude明确usage_limit_reached，先前原始错误保存在reviews/g2-profile-runner.json等。只读审查；未运行代码、实验或GPU。

首审结论REQUEST_CHANGES，1项BLOCKING：新入口没有REPRO_RUN_ID，父runner异常退出留下原生probe/runtime后代时，host supervisor可能提前放锁。NON-BLOCKING建议显式清理继承的MPS环境。

Codex落实：supervisor仅为child注入root:supervisor:uuid；native TERM/INT进入EXIT清理；native/runtime入口清空继承MPS环境；新增CPU实际orphan持锁/第二任务等待/外来身份保留用例。证据evidence/cpu-lock-test.log，manage离线psutil7.2.2证据evidence/install-manage.log。

复审原文：

> 复审结论：APPROVE_WITH_NITS。唯一BLOCKING已关闭，剩余0项。
>
> 已核对：supervisor仅向child注入唯一root前缀runID，原生探针、runtime及后代可被残留检查识别；native driver增加TERM/INT退出清理，并显式清除继承的MPS环境；新runtime入口检查G2及环境READY，取得host锁、清理环境、固定GPU UUID并拒绝覆盖已有结果；实际CPU日志证明孤儿存活期间持锁、第二wrapper等待、外来进程保留，manage离线安装记录为psutil7.2.2。
>
> 本次批准仅覆盖qjh000原生SM及有限FP16 runtime探针。native SM成功仍不代表服务内stream机制有效；模型服务与formal须另行G2/G3。远端bash-n及py_compile成功目前仅有主执行者转述，本次未读到独立日志。
>
> 未执行代码、修改文件或访问GPU。

非阻塞落实：补存实际远端syntax-check.log，未将本批准扩展到7B服务/正式测量。
