实际更新：第一单元72.112秒结束，前89/154项HTTP200及原JSON SHA通过，第90项URLError/HTTPstatus未知，已按规则停止；不能据此认定具体网络根因或完整catalog。[原始终态](catalog-first/terminal.json)、[已取89目录](catalog-first/catalog.json)、[270原件SHA索引](catalog-first-index.json)保留。旧89项不会再GET。

[续接G1](g1-catalog-remaining.md)/[G2](g2-catalog-remaining.md)只批准一个remaining65新单元：先核旧270原件每SHA与旧3摘要/严格89prefix，再把严格余65写独占remaining子目录，不改旧原件。原失败第90项明确重取一次，其余64首次。新一次7HTTP-MOCK全PASS/0skip0.003秒（父0.340秒），e9eb/9405前后等、temp空。实际续接仍待G5/push/源码核，120工作/180父及首失败停保持，不自动第三单元；不下载或安装artifact，不服务器/GPU。

下面为初始准备历史。

---

# Space 环境的官方制品目录准备

原freeze逐字节保留，3,140B、SHA12cc7ae16e15cb32a58d197b10c139df7d715a8c3eeb4246b77eebe5d4814b0f，共154个exact name==version。仅版本锁不是wheel字节锁；此阶段在本机Windows读取官方PyPI版本JSON，为后续Linux制品选择保留URL、tag、bytes、SHA、Requires-Python和yanked信息，不下载/执行wheel/sdist，不安装环境或修改protected pins。

[G1](g1-environment-catalog.md)和[G2](g2-environment-catalog.md)后，一次6项HTTP-MOCK全PASS/0skip，0.001秒（父0.289秒），bc107/12436源码前后相同，temp空。它们不是实际HTTP、依赖解析、Linux兼容或环境通过。

G5/push及指定commit校验后，工具只允许一次154条串行官方exact-version GET，拒绝redirect，每响应≤2MiB，socket min10秒/工作剩余，120秒工作预留5秒终态、父180秒，零重试、首失败停，排他environment-catalog目录/claim，原response及失败partial/状态/SHA保留。即使因时间或版本不可用只取到部分，仍保留真实断点，不自动开始第二单元。原freeze前后不变，不访问服务器、GPU或其他机器。

[原始6测试](catalog-tests.json) · [完整stderr](catalog-tests.stderr.log) · [精确原freeze](space-freeze.txt)

当前实际GET尚未执行；目录只是将来来源资料，不是已下载artifact字节证据、完整依赖解析或CPU_STAGED。Linux artifact选择/下载、目标安装、官方fork兼容补丁与actual CPU/GPU各另按具体方案受审。
