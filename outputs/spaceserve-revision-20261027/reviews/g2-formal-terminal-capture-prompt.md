# G2 Space正式终态CPU取证helper
沿用AGENTS3.2.1接替，独立只读，本地不网络/凭据/GPU/改文件。
新增work/revision-phase/capture_space_formal_terminal.py与test_capture_space_formal_terminal.py。仅在同formal真实exit回执存在且launcher/child实际PID+ctime均不live之后，CPU读原件/sha与nvidia-smi只读状态；没有kill/stop/信号/inference。未部署远端/未执行helper；正式继续运行，不能提前hash大数据。
main固定qjh000/UID2147/新root/实际FORMAL_STARTED SHA(db3714...0772)与formal15 producer(a1f794...92eb)，校exit配对（非零原样允许）和childctime，身份不明或live立即拒；借已审formal_code/model_code/numeric code_identity核实际15/57/18，remaining_owned非空拒bulk。要求目标GPU4 UUID/零compute零显存/MPSstopped，才freeze四个新文件formal-terminal.json/final-mps-owner/final-booking-state/formal-files.json（任何已存在拒覆盖）。
inventory包含全部formal（含失败/partial无marker）、runtime-devices/formal-*（partial未复制的device证据）、logs/mps、formal启动/exit/父子日志、MPSintents；路径越界/源变化拒绝，不读取权重/env/cache，不签G3/G4；copy booking仅预约状态无认证。helper SHA记录。需要终态之后才允许部署小helper和运行，对当前冻结源码无修改。
4CPU PASS：错回执/真实exit1不改、live父/子拒、PID复用/UID错/AccessDenied不误判无进程、失败部分文件均保留SHA。初始Windows测试缺psutil时将其import延迟至Linux实际进程查询函数；目标专属环境此前已确认psutil7.2.2，不安装/改用户Windows环境。现测试fake psutil仅CPU逻辑，不是实际target终态证据。
请核防重复/身份/无GPU负载/取证边界/路径/拒覆盖/失败保留是否恰当，输出APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES、BLOCKING/NONBLOCKING；不是收尾实际G4或资源释放声明。
