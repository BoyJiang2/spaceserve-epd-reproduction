# G2 审查：qjh000 逐位 SM 布局校准代码

**结论：APPROVE_WITH_NITS，BLOCKING 0 项。** 代码可以运行这次逐位布局校准。批准不包括 7B 服务、SM_EFFECTIVE 或第三组。

审查者为 Claude（claude-opus-5-5），与上一轮 G3 同一会话，只读。只审代码，实际结果另做 G3。

我读了：
- 更新后的 plan.md；
- 新增的 `probe_sm_layout.cu`、`preflight_sm_layout.sh`、`service_sm_probe.cu`，以及 `service_sm_probe.py`；
- `source-evidence/__init__.py` 和 `core.py`；
- 新补的 `mps-owner.json`、`native-sm-launch.log`、`runtime-probe.json`。

另外对 4 个支撑脚本做了只读哈希。没有改文件，没有跑实验或碰 GPU，没有读凭据。

## 已核对的项目

| 项目 | 结果 |
|---|---|
| 掩码调用接口 | `probe_sm_layout.cu:13` 的函数类型与 `libsmctrl.h:27` 一致。`:48` 把 `1<<bit` 放在第 4 个参数，即最低 32 位，对应 TPC 第 bit 位。官方 `__init__.py:170-176` 按 `mask_list[0..3]` 依次传入。`core.py:463-464` 的 `[0,0,0,0xfff]` 对应 mask4=0xfff，与探针的 `:57` 一致。上一轮“官方参数顺序未证实”的疑问关闭。 |
| 采样 helper | 函数类型与 `extern "C"` 导出一致。kernel 加了 `sm<512` 的边界检查（`service_sm_probe.cu:6`）。 |
| helper 资源与错误 | 每次采样都申请再释放显存（`:14`、`:25`），出错时也会释放。`cudaFree` 前会等 GPU 上的工作结束，不会提前释放还在用的显存。memset、10 次启动、拷回、同步都在传入的同一个 stream 上（`:16-24`）。返回的是第一个出现的错误；`measure()` 遇到非零就写 stderr 并以 2 退出（`probe_sm_layout.cu:17-18`）。 |
| 控制设计 | `:55` 和 `:60` 先执行 `measure()` 再做 `&&`，所以前面失败后每次恢复测量仍会执行并输出。每行输出后都 `fflush`，中途失败也能留下前面的结果。退出码条件 `:65` 的运算符优先级正确。 |
| 掩码是否每次生效 | 每次改掩码前，上一次测量已经同步完成，没有带旧掩码还在跑的 kernel。驱动是否在每次启动时重新读 stream 掩码，由零掩码恢复测量直接检验；若驱动缓存了旧掩码，恢复检查会失败，结果偏保守。 |
| 主机锁与私有 MPS | `preflight_sm_layout.sh` 的空闲检查、MPS 存在检查、清理与 trap、两种模式的循环、按身份停止，都与已批准的 `preflight_sm_h20.sh` 逻辑相同。`mps_owner.py`、`gpu_exclusive.py`、`env.sh` 的 SHA 与 `native-approved-code.sha256` 一致。探针失败时用 `if` 捕获退出码，6 次都会执行并各自保存 exit-code 和 stderr。脚本不写 SM_EFFECTIVE。 |
| 机器码 | 两个 nvcc 命令都是 `code=sm_90`，不带 PTX（`:25-26`）。 |
| 新增的身份与版本证据 | 记录了 hostname、boot_id、`/usr/local/cuda` 指向、cc 和 nvcc 版本、三个二进制 SHA、运行时代码 SHA（含 `mps_control.sh`），探针还打印 PID。上一轮的溯源和构建建议大部分已落实。 |
| 上一轮遗留项 | `evidence/mps-owner.json` 为 `state=stopped`，PID、创建时间、token、inode 与 `mps-start.txt` 一致。`native-sm-launch.log` 为 `finished`、`child_exit 0`，没有出现保留锁的状态。plan.md:24 已继承布局标准，并写明 64/78 不是资源比例。`core.py:509` 确认编码器在 encoder_stream 上执行。 |

## BLOCKING

无。

## NON-BLOCKING（按重要性）

1. **服务里复用同一个 helper 二进制时，CUDA 运行时符号可能被替换。在跑布局校准前决定是否处理。**
   - helper 以 `--shared --cudart=static` 构建（`preflight_sm_layout.sh:25`）。在本地原生探针进程里，主程序不导出运行时符号，helper 用的是自己静态链接的那份运行时。
   - 我不确定：一是 `libcudart_static` 链进 .so 后，`cudaMalloc`、`cudaLaunchKernel`、`__cudaRegisterFatBinary` 等是否默认导出；二是 torch 2.5 是否会以全局方式加载 `libcudart.so.12`（12.4）。若两者都成立，helper 在服务进程里调用这些函数时，可能改用 torch 的 12.4 运行时，或者一部分用 12.4、一部分用自带的 12.8。
   - 由于测量用的是驱动层的 stream 句柄，后果多半是报错或崩溃，不太会悄悄测错。
   - 但 model-service 计划要求服务复用“校准过的同一个二进制”。如果到时再改链接参数，就得重做校准。建议现在先在 CPU 上用 `nm -D` 或 `readelf --dyn-syms` 实测导出了哪些符号。必要时加 `-Xlinker --exclude-libs,ALL`，再跑校准，并把导出符号列表存进 OUT。

2. **目前的一致性检查只比数量，不能单独证明布局。**
   - `:61` 只检查各位单独减少的 SM 数之和是否等于 0xfff 组合减少的数。
   - G3 在无 MPS 模式下还应检查集合：各位关掉的 SM 集合两两不重叠，且它们的并集等于组合关掉的集合。
   - MPS 下编号可能被压缩成 0 到 N−1，集合检查没有意义，只能看数量。
   - `:44` 的标签叫 `baseline-mask-zero`，但测量时从未设过掩码（enabled=0），和后面“设成零掩码”的恢复测量（enabled=1）不是同一状态。建议改名，报告里也按两种状态分开描述。

3. **探针没有超时。** 若卡住，会一直占着主机锁和 MPS，也就违背“失败一律保存 exit 和 stderr”的要求。现在用到的掩码都是 0xfff 的子集，0xfff 上次在两种模式下都剩 64 个 SM，卡住的风险很低。仍建议给 `:58` 套上 `timeout --kill-after=10 300`。

4. **证据还可以补强：**
   - stop 之后把 `evidence/mps-owner.json` 复制进 OUT。这个路径是共享的，会被下一轮覆盖。`results/mps-gpu-uuids.txt`（`mps_owner.py:76`）同理。
   - 运行时代码 SHA（`used-code.sha256`，`:34`）缺了实际也会执行的 `env.sh` 和 `gpu_exclusive.py`。
   - 同时记录 `build/libsmctrl.so` 的 SHA，方便 G3 直接确认服务用的库与校准用的库相同。
   - 每次运行前后各记一个时间戳。
   - 若可行，复制 `logs/mps/` 下的日志，用其中的客户端 PID 对应探针打印的 PID。我不完全确定 MPS 日志的格式。
   - 启动器把锁监督进程的 stdout 存到 OUT 旁边。

5. **两处失败没有输出原因：** `:29`（参数个数）和 `:36`（找不到函数）直接 `return 2`，stderr 是空的。建议写明是哪个参数或哪个函数。

6. **可选的补充检查：**
   - 扩展单位扫描范围，比如 0–63 或 0–127，检查所有位的减少数加起来是否为 78。这能把“部分位对应空槽位”从推断变成实测。只扫单个位，不要用会关掉所有 TPC 的组合掩码，以免卡住。
   - 加一个对照：给另一个 stream 测 SM，确认掩码只影响设了掩码的那个 stream。

7. **批准标记只看文件是否存在。** 以前的批准也是这种方式。建议在 `G2_SM_LAYOUT_APPROVED` 里写入批准时的代码 SHA，脚本开头先比对，不一致就拒绝运行。

## QUESTIONS

1. 服务用的 `build/service_sm_probe.so`，是否会与 `results/sm-layout/service_sm_probe.so` 逐字节相同？上面第 1 点的导出符号是否打算在跑校准前实测？
2. 上次 MPS quit 之后，`tmp/mps/control` 是否已经不存在？如果还在，`:14` 和 `mps_owner.py:43` 会拒绝启动（失败即停）。若需要清理，应作为单独审查过的步骤：确认 owner 状态为 stopped、没有 nvidia-cuda-mps 进程、路径在专属目录内，才删除这个残留管道，不要手工删。
3. G3 会不会按第 2 点，在无 MPS 模式下做集合层面的检查？

**未解决的 BLOCKING：0 项。**