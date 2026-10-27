# G2 Space终态精确SFTP清单与无覆盖合并
沿用AGENTS3.2.1只读subagent接替，不网络/凭据/GPU/改文件。
新增work/revision-phase/transfer_space_formal.py/test_transfer_space_formal.py。它自己不执行SFTP/SSH，只在真实终态helper四回执已经取回holding/receipts后生成精确get批次，实际网络在控制器确认结束后由主agent另行执行。当前未取真实四回执/未prepare实际计划/未下载formal。
prepare固定初start原件SHA、formal producer/同controller exit、released/父子不live/own空、GPU4 UUID零mem空compute、MPSowner同snapshot/pipe/UUID/stopped、capture helper实际SHA与booking owner/resource/GPU lane/start/end。只选helper inventory中formal/runtime-formal/MPS logs/intents/controller等路径，拒模型/env范围、..绝对路径/引号换行/反斜线/冒号、casefold重复，local root只task/work，预算2copy+512MiB。raw/plan/batch任存在拒覆盖，目录不跟symlink/junction。输出仅CPU plan，明确无runtime/G4许可。
merge要求plan host/root/controller与当前actual start SHA一致；重新由原始capturedmanifest+四回执bytes/SHA构造expected并严格等于plan，防改计划；全量源bytes/SHA和所有目标冲突先检查，任一不符不copy，已有同SHA跳过，只有缺失目标用xb逐copy再SHA，最终回执也x。不覆盖G3/producers，不解压archive、不执行JSON或二进制。
5CPU PASS，全部mock数据置task/work临时目录标SYNTHETIC CPU ONLY且从未执行getbatch：成功原字节、existing冲突全不copy、live/mixed owner拒、坏下载/plan换model路径拒、路径注入/越界/重复拒。CPU fixture不是真实终态或新Gate。捕获进程实时与否由前置已G2 helper实际执行+主agent实际PS再核，此脚本本身的flags不替代那个事实核验。
请核路径/来源/field关联/批次命令注入/无覆盖merge与失败保留，给APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES及blocking。仅CPU工具，不是实际传输/实际G4。
