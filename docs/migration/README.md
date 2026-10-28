# 2026-10-28 实际最新状态

三个raw复制单元全部exit0并通过[独立完整性审查](asset-bytes-audit.md)：23,080,280,259B，24份原始回执/完整清单31,285,351B已下载并逐SHA验证。两旧写前失败保留。成功仅RELOCATION_PENDING，环境路径、IPC库依赖与目标suite/GPU均未通过；旧源不得删除。

Space数据集已复制；[八份精确小素材恢复](../../spaceserve/migration/asset-recovery/README.md)本地4CPU-MOCK过，实际上传尚待G5/push与fresh准入。原Qwen下载清单10,162B已精确恢复，完整环境与权重仍待取得。EPD库raw副本在assets/build/epd-cuda/，runtime期望assets/build/，后续须显式处理路径及原RUNPATH，不用链接掩盖旧依赖。

以下为逐阶段历史，当前状态以本节及实际回执为准，不重复已完成代码/资产单元。

---

最新：两个data前置守卫失败均发生于写前，原件和[系统PAM/SSH身份恢复记录](pam-recovery/README.md)完整保留。两代码repo已迁移；资产复制成功仍0，模型/环境单位尚未启动，GPU0。

当前补充：原始资产data首次执行因系统PAM服务cwd不可读在写前停止；[窄恢复及原始证据](pam-recovery/README.md)单独保存。尚无资产复制成功，环境/模型未启动，未运行GPU。

# 实际迁移状态（2026-10-28 22:14）

qjh003两个固定repo在21:21实际部署a3f03b9dd5956db92add454f9b3afd5663f84609；[独立代码部署审查](asset-materialization/deployment-audit.md)已通过。Space98/EPD78实际检出文件覆盖原G2源85/62，Git clean、完整fsck及六原件下载SHA通过。此结论仅代码完整性，不是环境或GPU G3。

[后续原始资产物化](asset-materialization/README.md)已有本地软件测试，实际远端复制仍待准入执行；环境兼容、目标套件及GPU0。新目录是/local/boyjiang/spaceserve与/local/boyjiang/epd，旧源保护。下文是此前准备阶段记录，不能当作当前尚未部署或需要重新部署的指令。

---

# 两项目代码迁移的共同CPU准备

SpaceServe固定源码已发布07358c8，EPD固定源码已发布aae5c8b；两者分别通过本地G2和代码发布G5。**目标部署尚未执行；本次Space/EPD套件未执行，资产未迁移、新GPU请求0。** 源码README内“尚待G2”是受审快照中的较早措辞，实际代码审查已通过，不能因此改写该历史快照SHA。

部署工具 [`tools/migrate_code_cpu.py`](../../tools/migrate_code_cpu.py) 仅支持两个固定qjh003项目根的CPU prepare/deploy，不含环境/模型安装、GPU、旧目录删除或自动重试。

[独立G1](g1-cpu-deployment-plan.md)和[工具G2](g2-cpu-deployment-tool-final.md)通过后，实际在本机Ubuntu-22.04 WSL以 -I/-S/-B 完成一次5测试，0失败/0skip，源码前后SHA不变；包括真实自有子进程与helper超时终态，以及失败原始输出保存。[原始stderr](local-deployment-tool-tests.stderr.log)与[命令/退出码/SHA回执](local-deployment-tool-tests.json)保留。它们不是Space/EPD套件或GPU机制证明。

21点前只本地准备。本人CPU/GPU qjh003预约21:00至次日09:00；前一时段属于他人，不能提前迁移。开窗后fresh CPU票/实际hostUIDboot/CPU50和原目录核验，再用本工具代码的最终已发布完整commit和完整Git bundle部署。新辅助工具/文档提交不改变07358c8的Space受审源或aae5c8b的EPD受审源；目标逐文件仍须与两个G2快照全等。

操作顺序：

1. 本地记录最终已push commit、完整bundle SHA/bytes、工具两文件原始SHA；再只读fresh API及目标CPU准入。
2. 验证本地工具字节等于指定Git blob，SSH通过相同字节（先decode/hash核验再执行）在CPU50/nice10运行prepare，仅新建两项目固定根和空目录。保留原始argv/字节SHA/回执。
3. 将bundle传入Space/staging/source.bundle，不覆盖任何已有不同字节；保留传输exit及远端实际SHA/bytes。
4. 刷新5分钟内API观察，运行deploy，外层900秒/受控清理最多120秒。每条Git命令前仍检查同一API快照；**超过5分钟会失败并保留partial，不能原样自动重试**。具体断点必须先盘点再审查恢复。
5. 两repo稀疏检出各自runtime和共同tests，完整历史在Git对象中；实际逐blob/bytes/SHA、两个G2快照、HEAD/tree/clean/fsck及下载后SHA核验，再独立实际部署复核。
6. 资产先只读形成精确成员清单、shebang/.pth/库依赖可迁移性与空间预算，再另审。qjh000 19–23无源CPU许可，本阶段不访问；缺失Space环境/7B明确记未完成。目标验收之前不清理旧源。

[完整CPU部署范围与限制](cpu-deployment-plan.md) · [Space独立迁移](../../spaceserve/migration/README.md) · [EPD独立迁移](../../epd/migration/README.md)

旧报告、封存raw、七ZIP、四Release13资产均不改；[本次实际API与已发布快照逐字段对照](releases-unchanged.json)证明资产元数据不变，没有重复下载大包。
