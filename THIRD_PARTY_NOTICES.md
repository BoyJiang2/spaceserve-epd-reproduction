# 上游来源与许可

本仓库是复现实验材料汇编，不把上游代码、模型、论文或图像声明为原创，不给全部第三方材料统一重新授权。

| 来源 | 本轮固定版本 | 许可与保留材料 |
|---|---|---|
| [SpaceServe](https://github.com/gofreelee/SpaceServe) | 66de079af4234b27f7f82ff91d238ef1351324ba | Apache-2.0，[固定版本LICENSE](licenses/SpaceServe.LICENSE)；公开fork以vLLM0.7.2为基础 |
| [EPDServe](https://github.com/vbdi/epdserve) | 9b111f710dfb4724072b603d626a1e4dad93ef1f | CC BY-NC 4.0，[固定版本LICENSE](licenses/EPDServe.LICENSE)；原source/LICENSE另原样保留 |
| [vLLM](https://github.com/vllm-project/vllm) | 0.7.2（Space）；0.6.1/0.6.1.post2（EPD） | Apache-2.0，[0.7.2](licenses/vLLM-0.7.2.LICENSE)、[0.6.1](licenses/vLLM-0.6.1.LICENSE)许可证原文；实际运行包版本以各batch freeze为准 |
| [mysmctrl](https://github.com/gofreelee/mysmctrl) | 6ff57356968a3f04158b9273aa881ee6bdf04229 | 固定Git树未列独立LICENSE/NOTICE；[原README](licenses/mysmctrl.README.md)保留作者、论文引用及技术说明，不在本仓库额外授予许可 |
| Qwen/Qwen2-VL-2B/7B-Instruct、MiniCPM-V-2_6 | 各batch configs中的原revision/bytes/SHA pin | 不分发权重；应分别遵守模型官方许可。7B为逐文件revision记录，非虚构共同revision |
| COCO图片子集 | 原dataset manifest与图像SHA | 完整图集在原Release包内，来源/选图清单原样保留；图像权利归原作者，不重新授权 |

libsmctrl 原README要求引用 J. Bakita and J. H. Anderson, “Hardware Compute Partitioning on NVIDIA GPUs,” RTAS 2023, pp.54–66；完整BibTeX保留在上表链接。

所有补丁都是相对对应固定上游的实验兼容、数据记录或观测变更，非另写的原始系统：

- 首轮Space/EPD及原生vLLM补丁：[outputs/reproduction/patches](outputs/reproduction/patches)。H20 cache-fixed为合并版本，不与旧epd-complete重复叠加。
- 最新Space累计补丁：[SpaceServe-complete.patch](outputs/qjh000-migration/results/patches/SpaceServe-complete.patch)，与实际结束git diff字节相同；实际设备与SM观测补丁一并保存。
- EPD方案A：[instrumentation.patch](outputs/epd-profile-a/instrumentation.patch)及相应src/快照，只能按报告解释观测，不把CPU打点当GPU因果。
- 上游vLLM版本证据：[upstream-version-evidence.json](outputs/reproduction/configs/upstream-version-evidence.json)。

许可证原文于2026-10-25从上述固定Git提交/标签获取，下载来源与SHA记录在publication/upstream-notices.json。原封存文件及报告不因本次发布改写。
