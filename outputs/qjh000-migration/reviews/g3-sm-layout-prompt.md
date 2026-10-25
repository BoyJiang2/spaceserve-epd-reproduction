独立只读G3：qjh000实际逐位SM布局与零mask恢复结果。Claude新明确session limit（outputs/epd-profile-a/reviews/g4-cuda-report-claude.json，is_error/usage_limit_reached，reset22:50），按AGENTS3.2.1接替。禁止改文件/GPU/实验/凭据，可本地CPU只读重算/hash。

实际结果outputs/qjh000-migration/results/sm-layout全部，含6jsonl/stderr/exit-code、二进制+SHA、完整mysmctrl固定源、代码SHA、driver/host/boot/GPU身份、MPS所有权/停止/日志/客户端、原生库与服务build/lib SHA。代码G2 Claude同session7c380db4...连续APPROVE_WITH_NITS：g2-sm-layout-claude.md及g2-stopped-mps-claude.md。旧socket精确清理G2批准后实际执行；最后CPU测试fixture的Path抽象类错误、Bash CRLF被前置guard拦截，未进入GPU，失败日志保留；只修fixture/conversionLF后实际启动PID3670450并完成，6次exit0。不得把CPU失败当CUDA失败或事后伪造G2。

请独立重算每个模式3重复：default未掩码集合78；每bit0–11掩码实际集合、各zero恢复、0xfff组合64与zero恢复78；元数据CUDA DriverAPI12020/物理78与实际qjh000 GPU0固定UUID/boot一致。无MPS各单bit关掉的SM集合必须两两不重叠且并集等于组合关掉集合；MPS编号会压缩，不将两模式ID当物理位置比较，只核逐bit数量/组合数量/重复稳定及恢复。减少数总14对应实测哪些低12位有变化，不猜12TPC/64:14资源比例；只验证本次相关布局，不声称全GPU TPC拓扑。

核二进制/源码SHA与当前本地脚本（LF变化属纯换行修复）、服务build/lib和probe lib同SHA529e2502...；helper符号无cudart导出/导入，服务将复制实际calibrated so而非旧CPU试编，G3服务再核SHA。确认private MPS三probe PID与日志/实例、state stopped、GPU process table empty、host lock finished，不能只信JSON summary bool。

输出APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES、BLOCKING文件行号+理由、NON-BLOCKING、QUESTIONS。范围仅native布局，不批准7B服务、SM_EFFECTIVE、第三组或formal；actual服务before/after/zero/reapply/first-execution还要另G3。
