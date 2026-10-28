# 本机准备相同模型文件（尚未实际下载）

原机器CPU无许可、目标21点前他人占用。为减少迁移等待，本阶段只准备相同Qwen2-VL-7B的15个公开文件，总16,594,373,187B；名字/大小/SHA均与当前受审asset pins完全一致，固定ModelScope逐文件40位Revision。单curl、零重试、partial保留、总1800秒且北京时间20:50截止，预留5秒收口；不访问服务器/GPU，不执行下载代码，不安装环境。

[计划](local-model-preparation-plan.md)、[G1](g1-local-model-preparation.md)、[版本一致性补审](g1-local-model-preparation-addendum.md)、[源码G2](g2-local-model-preparation.md)分别保留。新增两个本机CPU工具并未修改两项目runtime、迁移工具、输入pins或G2快照。最终发布后重新固定一个commit和完整Git bundle，21点两目标使用同版本。

第一次5项CPU-MOCK测试为1PASS/4ERROR，fixture在AppContainer临时目录mkdir发生WinError5，未进入fetch业务函数；原始[失败记录](local-model-tool-tests.json)及[stderr](local-model-tool-tests.stderr.log)保留。经[独立环境纠正批准](model-test-environment-correction-review.md)，保持源码不变、使用workspace专属临时根并脱离AppContainer的一次新单元实际5PASS/0skip，测试0.042秒，[原始命令/SHA/exit0](local-model-tool-tests-corrected.json)及[stderr](local-model-tool-tests-corrected.stderr.log)保留，临时根终态为空。此为mock curl软件契约，不是下载或模型正确性证明。

实际下载尚未开始，要在G5/commit/push、fresh磁盘和路径核验后才执行[工具](../../../tools/fetch_space_model_cpu.py)。文件保存在本地work/assets/spaceserve，不进Git。模型download_manifest原字节仍不匹配现行pin，**不伪造该元数据，不生成CPU_STAGED/G3，不宣称整套assets可用**；环境/数据/框架/编译库及目标实际机制仍待验证。
