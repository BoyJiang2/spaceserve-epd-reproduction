# G4 全量SpaceServe数据与证据（在全量已取回后调用）

你是独立审查者，先读 D:/Documents/codex/AGENTS.md。只读，不改项目/原始数据/marker，不访问远端或GPU，不运行实验。允许本地CPU只读复算、读取归档校验；正文回复主执行者保存。未完成项不能用预计状态替代。

本机只读CPU运行时：C:/Users/23520/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe。需要计算时使用PowerShell命令 `& 'C:/Users/23520/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -I -B -c '<内联Python>'`，仅stdlib读文件/计算/输出stdout，不写脚本、临时文件、pyc或任何项目文件，不使用重定向/网络/外部子进程。输出紧凑计数和差值，不把全raw展开进入上下文。不要读取凭据或项目无关文件。

范围：outputs/qjh000-migration，全量results/formal/points和rest，report/space-all.json。正式同一qjh000 H20 GPU0，Qwen2-VL-7B FP16 TP1 eager，native/Space/encoder-mask三组，1/4图×C1/4/8各六负载，共18配置5400formal+360warm，128输出，20warm+100formal×3。首轮1800+120已经独立G4批准，在同监督器/MPS/锁续余四点，不重采首轮。旧采样失败300+20保留但不选入。

请独立核验（不只相信passed JSON）：
1. 18配置、54重复的raw请求/摘要与完成标记；5400+360总数、无失败/缺失/重复、实际输出128，实际URLs/角色、模型、精度、上下文、eager、采样和缓存设置公平。按每重复实际起止窗口重算请求/s和token/s，再核三均值/样本SD、300formal的TTFT/TPOT/E2E inclusive P50/P95。
2. 跨组三重输入ID/图片序/视觉tokens和RGB一致；不同输出raw IDs/文本、首次分歧和同实现跨重复变化，检查是否出现串图/串响应的具体证据。不能将差异无证归因FP16或宣称全量语义/逐token一致。
3. 每个GPU显存样本的PID归属、求和bytes、UUID/物理容量和时间单调，窗口覆盖/间隙/foreign；实际设备参数文件和MPS边界。采样不等于瞬时完备排除外来负载。
4. 同一660项冻结源/used-scripts一致，全量结束后source check、boot、无自有后台、GPU/MPS stopped、实际终结exit0；points双层manifest与批准marker原bytes未变。full-current-code-check及pre-rest-current-code-check须真实通过。
5. evidence/formal-all-{transfer,local-integrity,payload-sha}.json、work/formal-all-20261023.tar.gz：独立检查全文件成员集合、SHA、完整gzip CRC/EOF、源postpack不变和本地已收齐；旧失败仍保留，points从未被重写。

机制G3已有真实cold/restart证据和独立审查：encoder stream 78→64→zero78→reapply64→首真编码64，CUDA重叠；LM仍保留visual，mask仅encoder，不是完整SIS。不要重新运行模型。EPD A qjh0032400已受限封存，不与本批混为同机同模型。

首轮已知吞吐改善同时高TPOT/低TTFT退化；mask额外约±0.5%不能称稳定显著收益。其余负载应据真实数据判断，保留负值及输出差异。

输出APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES；列出实际独立复算/检查的计数和证据范围、BLOCKING文件行号/理由/最小建议、NON-BLOCKING、QUESTIONS。不要写批准marker，不把本审查等同G5或最终ZIP验收。

实际收齐：监督器exit0，全局COMPLETED 2026-10-23T15:02:44Z；原始传输包9,301,339bytes、415payload，SHAd7d75ef664e750ba87b3810ba43ccc3b06ff0f159814d28cba59a8ac9f0e6814。源postpack、本地gzipCRC/EOF/所有payload及唯一集合已主执行者真实通过。final-background passed、目标GPU进程表为空、MPS原token stopped，boot/两repoHEAD通过。主执行者已CPU复算全量passed；你的独立审查仍须检查实际raw与统计。
