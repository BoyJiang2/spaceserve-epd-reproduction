# Space实际完整模型/机制G3

独立只读，不修改文件、不访问GPU/远端/凭据。先读AGENTS、plan.md及本批reviews实际G1/G2。Claude额度耗尽接替已授权。

实际attempt1 producer57 SHA6782b5a1578c9d890f03bcc2368a36c3ab69663d7479f7b55b5af0c6f03141a5，controller456563/ctime1793048424.41/ID03a034209d28481eabb093d68ec83992，exit0；六单元全部COMPLETED，7reference+90target+216diagnostic=313。attempt0原MPS startup exit1/0生成及源码53保留，不抹除、不重复累计。

本次raw全量已抓回results/preflight-models-attempt1，共219文件/385460834bytes；evidence/model-attempt1-files.json逐SHA原清单。evidence/model-attempt1-terminal.json实际核model57/numeric18均不变、boot838160b3...、GPU4 UUID79214...、零显存/compute空/owned空、MPS stopped/controller终止，限快照。numeric41归档/consumer43独立G3继续保留。

检查全部reference/六组correctness JSON和逐提交/HTTP原文journal，15targets=7标准+8C8异图路由，实际输入IDs/输出长度/语义或多图reference不足时逐token一致，冷启重启均足。六组20warm后start仅16profile请求，HTTP成功、128输出、4图1024视觉token。预处理警告真实存在：kwargs min/max200704被vLLM忽略，模型processor默认3136/12845056；但本COCO20实际448×448（进度快照/PIL源hash可核）、processed IDs256/图，不能称kwargs已生效。

逐组device-records worker params实际设备/FP16/encoder-vs-language组件、CUDA UUID/MPS身份、imports.json原生wheel路径与fork路径、实际loaded lib SHA；actual encoder stream SM记录：无mask前后/首次不变，mask严格subset/clear恢复/reapply一致/首次同stream，不能只看数量。四解耦组overlap.json和十件trace-export原gzip的PID/CRC/SHA/baseTimeNanoseconds/实际kernel重叠关联；源诊断kernel在profile前，不能用host并行替代CUDA重叠。

如通过，范围仅模型正确性覆盖/设备放置/实际encoder mask/并发，未验证decoder互斥，未证明性能收益。后续正式新controller仅关闭profile/SM诊断且维持同源/同MPS/同模型/同参数，仍须独立G2和consumer适用性，不直接授权正式54。

输出实际G3 APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES、BLOCKING带路径/行号或原数据位置、NON-BLOCKING与QUESTIONS。不从exit0/marker替代全raw证据。
