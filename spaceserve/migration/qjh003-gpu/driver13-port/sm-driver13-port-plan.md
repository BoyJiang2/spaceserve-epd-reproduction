# 原库 CUDA Driver API13 兼容诊断

首次numeric真实exit1：FP16通过/max_abs_error0.030937，H20全78SM原生探针启动成功；原libsmctrl在第一次mask明确拒绝DriverAPI13000。MPS通过原finally停止，GPU0/0MiB/compute空，父子/登记helpers全部退出且没有信号。原失败run与源码/资产/claim不改。

固定mysmctrl 6ff5735 README的“Porting Stream Masking to Newer CUDA Versions”明确提供MASK_OFF从0每8字节增长的官方探测方法；libsmctrl.c以CUDA12.2的0x4e4为base，MASK_OFF分支实际写新stream布局。我们不猜测已知offset、不改驱动/库源码、不替换libsmctrl、不升级CUDA/模型/精度/请求协议。

仅申请一次独立numeric诊断：同GPU0/UUID/boot/fresh本人CPU+GPU票，在项目staging/sm-driver13-port下用原已编译probe（无MPS、每个进程独立native CUDA context）（源/二进制SHA绑定）与原libsmctrl，显式offset候选0,8,...,248最多32个，各独立进程最多3秒，超时仅绑定自有进程TERM→受控KILL，单元≤180秒工作+120收口；不并行、不模型、不正式测量。每候选新CUDA上下文；原probe本身要求mask严格子集、清零恢复全SM、重施恢复相同subset。无成功或出现无法确认释放即停止，不扩大搜索。找到首个成功只作候选，须原mask probe再独立重复3次通过并实际GPU释放；无偏移性能结论。

首轮扫描不启动MPS，不复制运行源码或模型；直接执行原run只读已编译probe和assets原库，stdout/stderr全部写独立staging。每个候选退出后查询GPU0显存/compute为空才继续，任一无法释放就停且不影响他人。父进程PID/start_ticks/UID二次核验后才TERM/KILL；不信号未知身份。找到首个成功后仍同native严格重复3次；这只确认native候选offset，不证明MPS或服务encoder mask。真正三次MPS与服务stream证明留给后续独立重新审查批准的新numeric/model Gate。每候选原始stderr/stdout、实际PID/ctime/exit/SMsets、offset、boot/UUID/库与probeSHA全部留存。

若该官方兼容机制实际验证通过，后续单独审最小runtime/config补充，将确定offset显式冻结并传入所有相关phase、capture记录该值；仅环境兼容配置，不改变三组或算法。新numeric/cohort及实际G3仍需重新通过，不追溯把首次失败记PASS。不够201min则不formal，09结束08:58清理保持。

用户此前已授权遇到问题自主决定并继续，目标明确要求有效mask；本申请属于官方机制的必要兼容诊断，仍须独立G1/G2，不自行启用fallback或降低验收。若风险或范围不能合规收敛，保留失败收口，优先本地EPD后续准备。
