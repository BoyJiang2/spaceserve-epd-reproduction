实际更新：十个独立新获取单元各一次全exit0，无自动重试；随后额外实际重读15model＋原metadata共16实体，全SHA匹配，15model共16,594,373,187B。[独立实际结果审查](actual/model-file-bytes-audit.md)通过，[完整额外实际SHA和30原件索引](actual/model-final-capture-index.json)可核。原Windows失败/partial未动。下文“尚未执行”是旧准备历史；环境/模型加载/目标suite/GPU仍未通过。

# Qwen 原固定权重的独立 CPU 获取准备

原15文件的name/bytes/SHA/逐文件Revision与现行pins和已恢复原download_manifest一致；两manifest编码不同，不能称文件原字节相同，语义比对证据单列。已落地五小文件仅SHA复用；剩余十件16,592,698,781B建立新的qjh003获取单元，旧Windows curl43与1.632GB.partial保留，绝不续传或重标成功。

[明确G1](g1-model-remote-acquisition.md)与[代码G2](g2-model-remote-acquisition.md)批准后，一次8项完全离线CPU-MOCK全PASS/0skip，0.040秒（父0.259秒），4f51/e643/9cf源码前后相同、temp空。不证明实际Linux TLS/CDN、完整权重、环境或GPU通过。

工具每个缺失文件单独fresh本人CPU准入、claim及排他partial；固定原ModelScope HTTPS repo/Revision/name，不Range/重试，最多3HTTPS跳转，默认TLS，socket最多30秒且不超过工作剩余。读前后及写前核deadline/证明/大小，完整200/size/流SHA+fsync后用同目录排他link发布仅本unit的新verifiedtemp，再实际target SHA及inode/UID验证后移除该临时名。不是对旧源建立hardlink；清理异常保留真实两个文件状态、不自动重跑。240秒工作＋120秒收口、API300秒、预约结束前120秒及原CPU50nice10/bootUID边界不变；继承CPU booking函数的1020秒完整覆盖要求更严格，不据此延长单文件工作。

URL记录仅原固定source URL和有效scheme/host/pathSHA，签名query/userinfo/cookie不记；外部异常只class/status/phase，不输出含URL的异常文本。原metadata/pins前后SHA核。成功只MODEL_FILE_VERIFIED，不CPU_STAGED、assets ready或GPU。环境安装另审，GPU0，不访问其他主机或增加预约。

[8测试原始结果](model-remote-tests.json) · [完整stderr](model-remote-tests.stderr.log) · [wrapper/只允许十个文件](model-remote-wrapper.py) · [真实命令约束](model-remote-argv-template.json)

当前尚未执行这十文件网络获取；G5/push/三端字节核与每文件fresh现场后才开始，任一失败停止整个后续序列。不会把五件已落地小文件重新下载。原pins/实验矩阵与旧raw/ZIP/Release不动。
