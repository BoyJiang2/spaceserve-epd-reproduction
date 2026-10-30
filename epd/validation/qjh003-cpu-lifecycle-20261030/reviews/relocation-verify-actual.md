# EPD CPU 静态迁移：实际 verify 独立审计

reviewed_at_utc: 2026-10-29T23:51:12Z
reviewer: /root/gpu2_report_g4

**APPROVE_WITH_NITS / BLOCKING 0：本批 CPU 静态迁移 apply→verify 完成。没有 Ray/Torch/dlopen/CUDA IPC/GPU 或 runtime-ready 许可与结论。**

本人仅本地只读原件、Git对象、JSON/tar、计算SHA，不运行项目、测试、网络、SSH或GPU，不修改源码。唯一verify目录为 `epd-relocation-CPU-20261030-verify/`，对应capture为 `epd-relocation-CPU-20261030-verify-capture/`。

## 真正的来源与批准链

实际input中的verify审批JSON与独立 `epd-relocation-CPU-20261030-verify-execution-G2.json` 相同；base64 review原字节与对应G2原文相同，SHA `ad2d1ccb0053b675f777f20b6ecf48215741facab09ef4da05fb302f24551d7f`。它是另签phase=verify、max_attempts1的条件审批，未套用apply批准。先前本人实际apply审计原文SHA `641f18a9e1489bdb42a1d778322161a2e3176a09417bcdc54a12e4d1e0210cf4` 及其JSON、全部bound_files重新核SHA一致且通过；verify实际source-proof绑定此真实审计SHA，执行时间在该审计产生后。

source `0e3031089b7e523309b4cc3fcaab2b91f4ba4382963778cf22ea78cba647acec`、config `218bfc2d53f623d98aa64286c1d132c9c74a8f6db0c75aa8e48cfaa9f82f0e70` 从真实input解码，分别与本地Git97a33d5287cfdca69956da0fdabe5bc68ea65d46的对应blob原字节核同；实际argv的base64 operator也解码与获审原命令字节一致，SHA `87e0cd40d438d084c5de5fab12d4ab4310cdf375dad7757217213f1a6f7f4d9e`。真实FD input-file回执的input SHA一致。helper97a33与实际runtime a3f03b9dd5956db92add454f9b3afd5663f84609分开保留，未重标为已部署新runtime。

## 原件与apply后不变性

verify包1003520 B，SHA `97dc246c9b1e5f3e9f219043be2731e4df7de1d234803016870f26869f256374`。实际123个唯一普通成员为122物理文件和1个生成的 `CAPTURE_INVENTORY.json`；与apply包中生成索引名 `__capture__/inventory.json` 不同，不将命名差异混成实际新文件。独立核122物理raw大小/SHA/UID全部过。

相对apply的121物理原件，仅新增 `staging/asset-relocation-cpu-20261030/verify-terminal.json`。本人逐项比较旧121raw全部原字节，以及索引中path/bytes/SHA/UID/mode/mtime完整字段字典，均相同；3条python symlink记录也全等。因此apply审计已独立重建的61startup/56字节变换、56备份、claim与原nested/flat ELF均保持不变。原nested SHA `12e4145134ba1697bb745fd51c37a8f275293284d6152c17b42513dd6d07ca20`，flat SHA `fdb86ae5a5658d17c98cc8cc17e3b0d911433bf270fb8bcfbb381a99f66a970e`。此前直接解析ELF二进制所得NEEDED相同、新RUNPATH精确的结论适用于本次全同字节，不重复运行readelf或加载库。

新增verify-terminal与实际stdout第一行JSON语义全等：exit0、startup_files_verified61、rewrites_verified56、changes空、original_nested_unchanged true、flatSHA匹配。实际两个静态命令patchelf --print-rpath与readelf -W -d均exit0，RUNPATH等于新配置三目录。没有把verify exit0解释为这些依赖已实际加载。

## 身份、时间与终态

实际verify started_ms1793317720444/finished_ms1793317720503，elapsed0.058857490秒；fresh booking observed_ms1793317709263，差11181ms。真实本人CPU58743aa0、04–11、boyjiang/h20/qjh003、当前时段与结束前120秒余量均核；不是GPU票代CPU权限。实际获审operator/tool写前强制host qjh003、UID2147、boot65f52a67-afe4-4919-8646-4694255b48ee、CPU50/nice10、runtime HEAD clean、Space claim/started不存在及自有项目进程guard；本审依据真实执行断言和结果，不另称有独立内核affinity或/proc采样。

实际SSH PID55052/FILETIME134377913092723465与controller记录保留；argv为system Python -I -S -B、CPU50/nice10、CUDA_VISIBLE_DEVICES空、foreground TERM60/kill-after30。stderr为空，SSH exit0/finish1793317720690，stdout末行保留helper/runtime双commit、phase verify、new_GPU_requests0及grants_no_runtime_readiness true。没有UNKNOWN终态或证据拼接。同步静态子命令和SSH已返回；没有独立最终整机/proc采样，不据此认定其他任务释放或整机空闲。

## 完成范围

本批静态迁移完成，可以保存为CPU资产准备结果。后续真实Ray生命周期、父唯一释放/创建quiescence、库加载、IPC/native36、模型与公平PD性能仍须各自审查、真实证据及合法资源窗口。不得重跑apply/verify覆盖本批，不修改原nested/旧封存/七ZIP/Release，不自动新增GPU或恢复Space模型。完整实验目标仍未完成。

GATE_RESULT: {"gate":"EPD-CPU-relocation-20261030-verify-actual-audit","passed":true,"decision":"APPROVE_WITH_NITS","blocking":0,"CPU_static_migration_complete":true,"Ray_approved":false,"dlopen_approved":false,"IPC_approved":false,"GPU_approved":false,"runtime_ready_granted":false}
