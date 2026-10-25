# 平台与存储选择

本次已核对GitHub官方[普通Git限制](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)（>100MiB阻止，>50MiB警告）及[Release说明](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)（单资产低于2GiB、最多1000资产）。七个原包均低于2GiB，无分卷。

强特征扫描覆盖全部选择文件及ZIP成员，gzip展开内容流式检查；不是对任意未知秘密或opaque格式内部语义的绝对保证。第一次命中为已独立核对的公开vLLM函数名，证据与修复审查保留，未改原件。最终Git候选在所有新增后复扫。
