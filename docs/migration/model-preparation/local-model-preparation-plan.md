# 开窗前准备相同模型文件（仅本机CPU和公网下载）

本阶段不访问qjh000/qjh003，不占GPU、不安装环境、不运行模型。用户要求尽快迁移，源qjh000当前无CPU许可、目标21点前他人占用，因而提前在本机D盘准备相同Qwen2-VL-7B公开文件，减少开窗后等待。实验模型、精度、请求和GPU预算均不改变。

实际D盘空闲54,626,537,472B，15个模型文件总16,594,373,187B、最大3,898,649,896B。仅一个curl进程串行，下载成功后同盘rename，不复制大文件；至少预留模型总字节＋8GiB，目录为本项目固定本地资产根 `work/assets/spaceserve/models/Qwen2-VL-7B-Instruct`，不进入Git。原封存/ZIP不动。

来源是已发布Git的 `spaceserve/configs/h20/qwen7b-model-manifest.json`：repo Qwen/Qwen2-VL-7B-Instruct、固定ModelScope公网端点、每文件完整40位Revision。15项名字/大小/SHA256已全部与当前受审 `spaceserve/runtime/configs/asset-content-pins.json` 匹配。不得查询latest、换模型、量化或混入不同revision。实际下载后每项bytes/SHA再次检查才能原子rename为最终文件。

新增一个小的本地下载工具和CPU-MOCK测试源码，独立G2/G5、commit/push后才实际下载。每文件单次curl、零重试、独立partial保留；异常/超时保存原始stdout/stderr/exit与断点，不自动重新取文件。总wall最多1800秒且不得超过北京时间20:50，curl max-time与Python timeout共同绑定剩余时间；到期受控结束自有curl、保留partial，不影响21点接续。工具不读取凭据、不执行下载的代码、不import torch/ray、不用shell拼接命令。

默认拒绝已有不同字节、软链接、越界路径；如果已有完全匹配的本项目文件，只校验不重下。所有实际下载命令、source/pins SHA、每文件开始/结束/字节/hash及失败原件保留在同一资产根旁的本项目日志。磁盘不足或输入pins不匹配时必须在首次网络操作前拒绝。

本地原download_manifest元数据与当前stage pin未匹配（CRLF转LF也不匹配），**不能伪写对应成功文件或替换metadata pin**。此次只报告15个公开模型文件准备情况，不创建CPU_STAGED/G3或声称整套资产可运行；原下载manifest仍需合法源读取/真实恢复或单独受审调整。环境/框架/两编译库/数据集未准备，不由模型文件下载替代。

验收：固定15文件成功/失败逐项有实际证据，成功文件均匹配现行受审pins、失败保留；无服务器/GPU/模型请求，无旧原件修改。工具纯CPU契约测试不代表模型正确性。该阶段不得改变f35中两项目受审runtime、迁移工具和G2源快照字节。若新增下载工具的发布形成新main commit，须在独立G5核实这些受审字节全部不变，重新固定同一最终commit及完整bundle；本地/GitHub/21点目标两checkout统一该commit，旧f35候选bundle只保留真实来源记录、不再用于部署。下载不使用服务器，不因此扩大CPU/GPU准入或操作范围。
