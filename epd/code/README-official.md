# EPD官方源码与最小适配快照

[源码](official/README.md) · [来源/逐文件SHA/排除清单](official/PROVENANCE.json)

固定官方基线 `9b111f710dfb4724072b603d626a1e4dad93ef1f`；服务器适配commit `06fbcb6f3f3b931950077077c9a040e9c238deee`，tree `892de3169db28d0b866f50aeb727c0d823267aa7`。服务器唯一开发目录 `/local/boyjiang/epdserve-official`，origin为自有复现仓库，upstream保留官方。

最终仅五个源码文件有变化：三个API入口逐路径加载图片；AsyncLLM将在线CLI请求内并行设置传给实际请求；Orchestrator记录创建后的有效flag。直接构造默认行为True保留，工厂显式采用CLI0。True分片路径的浅拷贝污染已复现但未修，本阶段保持关闭。

复跑源码从官方9b依次应用[三API图片补丁](../patches/20261104-multiimage-routing.patch)及[在线参数传递补丁](../patches/20261104-online-irp-wiring.patch)。已撤回无改善的E同步诊断，相关反事实补丁仅历史证据，不进入该复跑串。结果仓库不包含适配commit历史对象，不能在此直接checkout服务器运行SHA；发布SHA与运行SHA分别记录。

[CPU回归测试](../tools/test_official_online_irp_wiring.py)及[原执行/发布版独立执行记录](../validation/official-entry-20261104/online-irp-cpu.json)仅检验真实方法和工厂的传参，模型/GPU配置以stub替代，不是推理证明。新测试结果以独立文件保存，旧原件保留。

[四图配对诊断](../comparison/20261104-four-image-diagnostic.md)保留原语义失败、原清理失败及同步反事实无改善。**当前参数修正版本只有CPU验证，尚未取得GPU四图通过**，旧G3不能继承。basename缓存碰撞仍未修，测试数据需唯一basename；87项官方缓存/构建产物排除不变，权重及环境不入Git。
