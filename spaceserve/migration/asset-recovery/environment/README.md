# Space 环境的官方制品目录准备

原freeze逐字节保留，3,140B、SHA12cc7ae16e15cb32a58d197b10c139df7d715a8c3eeb4246b77eebe5d4814b0f，共154个exact name==version。仅版本锁不是wheel字节锁；此阶段在本机Windows读取官方PyPI版本JSON，为后续Linux制品选择保留URL、tag、bytes、SHA、Requires-Python和yanked信息，不下载/执行wheel/sdist，不安装环境或修改protected pins。

[G1](g1-environment-catalog.md)和[G2](g2-environment-catalog.md)后，一次6项HTTP-MOCK全PASS/0skip，0.001秒（父0.289秒），bc107/12436源码前后相同，temp空。它们不是实际HTTP、依赖解析、Linux兼容或环境通过。

G5/push及指定commit校验后，工具只允许一次154条串行官方exact-version GET，拒绝redirect，每响应≤2MiB，socket min10秒/工作剩余，120秒工作预留5秒终态、父180秒，零重试、首失败停，排他environment-catalog目录/claim，原response及失败partial/状态/SHA保留。即使因时间或版本不可用只取到部分，仍保留真实断点，不自动开始第二单元。原freeze前后不变，不访问服务器、GPU或其他机器。

[原始6测试](catalog-tests.json) · [完整stderr](catalog-tests.stderr.log) · [精确原freeze](space-freeze.txt)

当前实际GET尚未执行；目录只是将来来源资料，不是已下载artifact字节证据、完整依赖解析或CPU_STAGED。Linux artifact选择/下载、目标安装、官方fork兼容补丁与actual CPU/GPU各另按具体方案受审。
