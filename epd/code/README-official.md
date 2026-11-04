# EPD 官方源码与最小适配快照

[浏览源码](official/README.md) · [逐文件来源与排除清单](official/PROVENANCE.json)

固定官方基线：`9b111f710dfb4724072b603d626a1e4dad93ef1f`。
当前服务器适配commit：`d63cc3e8f15920c2e83653a5dca5b68bfa75346f`，tree `f37860be1149c90913737f51174ef1fc21880931`，分支adapt/qjh003-v1，提交后clean。

输入适配为三个API入口各一行：按每个输入路径顺序加载图片，修复把第一张图片重复成整组的问题；EPD、PD、完整模型入口一致修改。其余保留文件仍来自固定官方基线，原87项缓存/构建产物排除清单保留，不发布完整官方历史、权重或环境。

[最小补丁](../patches/20261104-multiimage-routing.patch) · [CPU错误复现与修复检查](../validation/official-entry-20261104/multiimage-routing-cpu.json) · [独立G2](../validation/official-entry-20261104/multiimage-routing-g2.md)。CPU检查只是路径语义验证，不是真实图片、并发模型或KV正确性证明；basename缓存碰撞仍未修改，诊断输入需使用唯一basename。

官方基线9b上的EPD、PD和三个完整副本单请求已有[真实结果](../comparison/20261104-official-pd-single-request.md)。**本适配commit尚未GPU验证**，不能继承旧单请求G3或正式性能通过。既有单请求启动器仍绑定旧9b，运行新HEAD前必须更新并审查对应入口，不能绕过版本检查。

服务器唯一适配目录 `/local/boyjiang/epdserve-official`；origin保持自有复现仓库，upstream保留官方。结果仓库源码快照的发布commit与服务器适配commit分别记录。模型入口复用已有权重软链接，未复制或移动权重。


当前另有一行E缓存写后CUDA同步，作为[四图差异](../comparison/20261104-four-image-diagnostic.md)的正确性反事实诊断，尚非已确立修复。P路径未改，不自动纳入正式性能。[单行补丁](../patches/20261104-encoder-completion-counterfactual.patch)及[范围审查](../validation/official-entry-20261104/encoder-completion-g2.md)。结果仓库不包含适配commit历史对象，不能在此直接checkout服务器运行SHA；可按官方基线与已列补丁恢复源码。
