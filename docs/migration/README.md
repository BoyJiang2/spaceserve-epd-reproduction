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
