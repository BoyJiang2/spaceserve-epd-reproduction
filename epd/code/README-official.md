# epd 官方源码快照

[浏览源码](official/README.md) · [逐文件来源与排除清单](official/PROVENANCE.json)

固定官方运行源码 commit：`9b111f710dfb4724072b603d626a1e4dad93ef1f`。保留文件与该 commit 逐字节一致；排除 87 个官方已跟踪缓存及构建产物文件。结果仓库采用源码快照，不包含官方 Git 历史，发布 commit 与运行源码 SHA 分别记录。权重不入 Git。

服务器适配目录：`/local/boyjiang/epdserve-official`。`origin` 指向本复现仓库，`upstream` 保留官方地址。新目录模型入口是指向既有权重的符号链接，未复制或移动权重。

当前仅完成路径、依赖元数据和源码检查；新官方目录尚未完成真实 GPU 请求。不要把此源码同步视为模型或机制已通过。启动、结果和 baseline 对照见[项目首页](../README.md)。
