# EPD 迁移静态盘点（只读 CPU，等待 Space 模型预检收口后）

成功标准：明确 /local/boyjiang/epd 下 raw env/MiniCPM/IPC 的实际位置、解释器与console shebang、IPC ELF NEEDED/RUNPATH以及flat库是否存在，形成原始输出和SHA；不把静态检查写成可加载或GPU通过。

只有本次Space预检真实终态/自有CUDA与MPS释放确认后执行一次。fresh本人qjh003 CPU票 bk-20261028T0925-0332cf80，21:00–09:00，CPU50/nice10、UID2147/boot65f52a67-afe4-4919-8646-4694255b48ee，60秒工作+30收口且08:58前。无GPU查询/初始化/kernel、无模型、无Torch导入/ops.load_library；不用ldd，不改driver/库/env/source/manifest，不创建远端实验目录。

原生/usr/bin/python3 -I -S -B仅读Path/stat/SHA。所有管理路径祖先须真实、项目内owner2147；记录epd/repo HEAD（git只读且禁fsmonitor/hooks/全局配置），与已知a3f不同时记录差异不reset。只读取envs/epd/pyvenv.cfg的home/version/include-system-site-packages、bin/python链接与普通bin文本第一行shebang。检查assets/build/epd-cuda/libcuda_ipc_utils.so、预期flat assets/build/libcuda_ipc_utils.so，记录SHA/size和/usr/bin/readelf -W -d/-S输出；readelf每次最多10秒、统一60秒deadline；仅which检查patchelf可用性，绝不执行修改。必要依赖仅列new env torch/lib、nvidia/cuda_runtime/lib的文件名和大小，不重hashGB大库或执行它们。无secret/token/home配置读取。

原stdout/stderr/实际argv/fresh CPU预约API原始回执/票据原件（仅资源/归属/起止/观察时间，剔除Authorization、token、cookie和任何认证材料）保存本地outputs/migration-qjh003/epd-static-inventory，失败保留不扩展或改动。随后依据真实事实单独写最小重定位G1/G2；本步骤不批准EPD native36/selected360/PD GPU或新的340分钟预算。Space当前生产bead/模型预检尚在跑时，不实施此远端检查。
