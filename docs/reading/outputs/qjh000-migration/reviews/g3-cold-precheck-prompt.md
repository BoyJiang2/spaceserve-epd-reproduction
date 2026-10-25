> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g3-cold-precheck-prompt.md) SHA256 631edfed51b6b53abecba7666a1d258b69d7942c75e246e47d42e02c02216f6b。原数字及解释不变。

# G3预审：qjh000 7B三组冷启动机制（重启仍进行中）

先读D:/Documents/codex/AGENTS.md。只读，不改文件/不跑实验/不访问GPU/不发外部消息。Claude实际usage_limit_reached(reset22:50)证据见epd-profile-a/reviews/g4-cuda-report-claude.json及000 split G2 JSON，依3.2.1接替。
最新goal：000 H20、7B FP16 TP1 eager，同GPU0/privateMPS100，对齐原生vLLM0.7.2、fixed Space66de、有效SM库6ff。同设备放置/真实CUDA overlap/actual encoder stream SM、正确性cold+restart后才formal。原生SM及bit布局G3已批准，本次必须服务内实证，不得以原生替代。

cold PID3878609实际完整退出0，3role均COMPLETED，MPS stopped/GPU清理，code SHA与二进制核对通过；restart PID4055241正按相同冻结代码运行，结果未完成，不提前批准全部服务G3/SM_EFFECTIVE。
本次预审先核cold，结果抓回outputs/qjh000-migration/results/preflight-cold/及results/runtime-devices/preflight-cold-{baseline-space,space,space-mask}/、results/patches/和evidence/7b-native-reference.json（若本地尚在解包请等执行者补确认）。原始tar work/preflight-cold-complete.tar SHA39752f18b94b828f7b0bca1a8861c289479ef8d59c81b9e6b6879f53f6441f67，448MiB。所有此前失败试次归档results/model-attempts-before-export-fix.tar.gz SHAcea883b8cd17a511e7a11e418d7a17043d1d0e08793c9079664bdfce6e07309e，不覆盖。

核查：
1 标准7+C8 8正确性每role，native引用、image routing/实际processed IDs、输出长度/图像RGB；profile20warm+16requests为诊断而非正式。所有FP16参数实际CUDA0、encoder/LM同物理UUID/MPS（正反边界client身份/runtime/NVML），非仅设置字符串。
2 core创建actualstream前后sm probe与first-encoder-execution同pid/stream；unmasked78全部无lib；masked实际78->64、zero78、reapply64、first64。对同MPS原生布局、实际二进制SHA与libsmctrl loadedlibrarySHA保持一致。官方仅限制encoder stream，decoder mask注释，不称互斥分区、TPC个数或64/78算力比例。
3 每role export-complete按真实workerPID、gzip CRC完整；原HTTP ack不当完成。fork两PID trace由baseTimeNanoseconds+ts对齐，实际kernel种类/同物理卡/非辅助probe（probe发生correctness/startup，profile在后）和overlap证据。cold自动结果unmasked encoder活动重叠比例.3554179718、masked.6975472742，仅采集片段观测，不是加速或正式性能。
4 cold cleanup/signaling exactidentity/无残留、MPSowner stopped、codeSHA绑定实际used-scripts。此前pidfd和过早导出失败均保留，相关G2修复已批准，不能隐瞒或当成功。

给cold事实预审结论/具体BLOCKING/NON-BLOCKING/QUESTIONS，明确仍需restart实际证据完成最终G3。不写未见的restart通过，不授权formal或创建marker。
