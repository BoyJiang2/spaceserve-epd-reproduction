> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g3-native-sm-claude.md) SHA256 1769eeea4259a75aededfce8c9e822b7f78916a99e2a256f9f43945c28aae784。原数字及解释不变。

# G3 审查：qjh000 原生 SM 掩码可行性

**结论：APPROVE_WITH_NITS。BLOCKING 0 项。**

审查范围仅限 G3 的 qjh000 原生 SM 掩码可行性，不包括 7B 服务、服务内 encoder_stream、正式性能，也不构成第三组批准。我没有修改任何文件，没有运行实验、访问 GPU 或读取凭据。为核对本地副本，额外用了只读的 `Get-FileHash` 和 `ls -la`。以下路径相对于 `outputs/qjh000-migration/`，另有注明的除外。

## 证据支持的限定事实

建议按以下措辞记录：

> 在 qjh000 的 GPU0 上（NVIDIA H20，UUID `GPU-d1b595ce-0b57-cdee-c1c0-9b1051aaa07e`，驱动 535.161.08，Driver API 12020），用固定 mysmctrl `6ff57356…` 构建 libsmctrl.so（SHA256 `529e2502…`）。对原生进程中 `cudaStreamCreate` 创建的流调用 `libsmctrl_set_stream_mask_lzc(stream,0,0,0,0xfff)` 后，该流上 kernel 观测到的不同 `%smid` 从 78 个降到 64 个。无 MPS 和私有 MPS 各跑 3 次：退出码都是 0，stderr 都是 0 字节，同一模式内三次的集合完全相同。

以下推论不能由这些证据得出：
- 0xfff 在 H20 上关掉 12 个 TPC；
- 64/78 是资源比例；
- 服务内掩码已经生效；
- 第三组可以验收。

### 已核对的项目

| 项目 | 核对结果 |
|---|---|
| 代码 | 本地五个文件的 SHA256 与 `evidence/native-approved-code.sha256:1-5` 一致。`probe_sm_mask.cu` 与 qjh005 的 G2 批准版逐字节相同（`978d0867…`）。 |
| 库 | revision 为 `6ff57356…`。`preflight_sm_h20.sh:21-23` 用 `git archive` 取已提交的版本，工作区改动不会混入。`libsmctrl.c` 与 qjh005 归档的版本逐字节相同（`7b0b538f…`）。两个二进制文件与 `binaries.sha256:1-2` 一致。 |
| 机器码 | `preflight_sm_h20.sh:25` 只生成 `code=sm_90`，不嵌 PTX，`build-probe.log` 为空。12.2 驱动无法即时编译 nvcc 12.8 生成的 PTX，kernel 能运行，说明实际用的是 sm_90 机器码（这是推断）。 |
| 运行 | 6 次退出码都是 0，stderr 都是 0 字节。由此可知没有触发 `libsmctrl.c:409` 的 abort，也没有设置 MASK_OFF（设置了的话 `:390` 会写 stderr）。不加掩码时，每次都看到 0–77 共 78 个 SM，Driver API 为 12020。 |
| MPS 身份 | `mps-before.txt` 为空。`mps-start.txt` 记录了 PID 3458093、创建时间、带专属根目录前缀的令牌、私有 pipe 和 inode，UUID 与 `device.csv:2` 一致。`mps-before-stop.txt` 里有 server 3458102，说明至少有一个客户端连上。三次 MPS 运行都得到 MPS 下特有的集合，说明三次都在 MPS 下执行。 |
| MPS 停止 | `mps_owner.py:82` 先重新核对身份，`:89` 等待进程退出。`preflight_sm_h20.sh:2` 设了 `set -e`，`:59` 先清理再写 `:60-61`，所以 COMPLETED 存在就说明停止命令返回了 0。`processes-after.csv` 只有表头。 |
| 时间线 | MPS 守护进程创建于 1792749156.63，约为 2026-10-23T09:52:36.6Z；COMPLETED 为 09:52:38Z，前后一致。 |
| 与 qjh005 的区别 | 同一份 `libsmctrl.c` 对 API 12020 有专门分支（`:332-334`，偏移 0x4e4，`:205-206` 注明在 535.129.03 上测过）。qjh005 的 API 13000 没有对应分支，落入 `:409`（见 qjh005 的 `private-mps-1.stderr:1`）。差别来自驱动 API 分支，不是 H20 硬件，两台机器的结论不能互相套用。 |

## BLOCKING

无。

## NON-BLOCKING（按重要性排序）

1. **减少的 SM 数与掩码位不符，第三组要求的布局标准还没满足。后续必须处理。**
   - 按 `libsmctrl.h:37-39`，置 1 的位表示关掉对应 TPC。`lzc` 把 0xfff 写入最低 32 位（`libsmctrl.c:140-146`，`:404`），即请求关掉 TPC 0–11。
   - L20 上同一掩码使 SM 从 92 降到 68，少 24 个，正好是 12 个 TPC × 2（`outputs/reproduction/evidence/sapphire3/sm-mask.jsonl:3`）。
   - 本机只少 14 个 SM，约 7 个 TPC，和“一位对应一个 TPC”对不上。可能是 H20 屏蔽部分 TPC 后，掩码位对应的槽位不连续，**但现有证据无法验证**。
   - `outputs/spaceserve-h20-7b/plan.md:13` 已通过 G1，要求减少数与布局相符，否则不验收第三组。本批 `plan.md:11`、`:19-20` 只写了“通过”，没有重申这条。
   - 建议：
     - 在本批计划里写明继承这条标准。
     - 若要争取第三组，先做逐位扫描：只用用户态手段，不加载 nvdebug，在无 MPS 和同一私有 MPS 下分别得到每一位对应哪些 SM。
     - 若无法做到，就记录“布局不可验证，第三组不验收”。放宽这条标准需要 G1 审查和用户确认。

2. **MPS 与无 MPS 下的 SM 编号不能互相对照。**
   - 无 MPS 时被关掉的是 {0–3, 14–17, 28–31, 42–43}，MPS 下是 {64–77}，两者都是 14 个。
   - L20 也是同样的模式：无 MPS 关掉 0–23，MPS 下关掉 68–91（`sm-mask-with-mps.jsonl:3`）。
   - 也就是说，MPS 下加掩码后的集合总是 0 到 N−1。原因我不确定。
   - 服务内探针只能和同一私有 MPS 下的独立探针比较（7B 计划 `plan.md:14`），不能把无 MPS 的集合当作预期，也不能声称用的是哪些物理 SM。

3. **64/78 不是两边的资源划分比例。**
   - 按 `work/space-official-core.py:97-99`，语言模型 stream 的掩码被注释掉了；`:461-464` 只对编码器 stream 加掩码。
   - 所以并不是 64 个给编码器、14 个给语言模型的互斥划分。
   - 我不确定这份文件就是实际部署的代码，需要在服务 G2 核对。

4. **探针与官方调用是否等价，还没有证实。**
   - 本地没有 `vllm/v1/smcontroller`，无法确认 `stream_lzc_mask([0,0,0,0xfff])` 是否按顺序传给 mask1 到 mask4。
   - 如果顺序反了，0xfff 会落到第 96–107 位。H20 没有这些 TPC，掩码可能完全不起作用。
   - `probe_sm_mask.cu:55` 的标签目前只是假设，服务 G2 需要引用源码中的实际行。

5. **服务用的 libsmctrl.so 与本次探针用的不是同一次编译。**
   - 服务库来自 `prepare_environment.sh:21-23` 或 `complete_environment_offline.sh:17-19`。
   - `record_device.py:40` 只记录路径，没有记录 SHA。
   - 需要核对 `evidence/libsmctrl.sha256` 是否等于 `529e2502…`，并在服务中记录实际加载的库的 SHA。

6. **溯源信息可以补强。**
   - 结果中没有 hostname、boot_id、每次运行的时间戳，也没有运行时实际脚本的 SHA。
   - `mps_control.sh` 不在批准哈希清单里，但被 `preflight_sm_h20.sh:31-32,47` 调用。
   - 最终的 `mps-owner.json`（`state=stopped`）和锁监督进程的 stdout 没有抓回本地，所以 MPS 停止和放锁目前是间接推断。
   - 探针没有打印 UUID 和 PID。服务 G3 运行中应保存 MPS 的 `ps` 输出，或 nvidia-smi 显示的 M+C 类型。

7. **构建环境记录不完整。**
   - `build-library.log:2` 用了 `/usr/local/cuda/include`，但没记录它指向 12.8 还是不完整的 13.0；cc 版本也没记录。
   - `:4` 的 `error_at_line` 隐式声明警告只影响出错时的 abort 路径，本次没有走到。
   - `syntax-check.log` 只有一行 PASS，没有命令和文件清单，单独作为证据的分量很弱。

8. **探针的判定标准偏弱。**
   - `probe_sm_mask.cu:56` 只要求 SM 数变少。做可行性检查够用。
   - 服务 G3 应写明预期数值，并在 mask=0 后再测一次，证明 SM 能恢复。

9. **这次结论只能放行服务内探针这一步。**
   - `start_server.sh:31` 中，SM_NATIVE_APPROVED 必须和 `REPRO_SM_PROBE=1`、G2_MODEL_APPROVED 一起，才放行服务内探针。本次结论最多支撑这一个标记。
   - 不能据此生成 SM_EFFECTIVE，也不能据此批准第三组。

## QUESTIONS

1. qjh000 是否继承 7B 计划 `plan.md:13` 的布局标准（减少的 SM 数须与掩码位布局相符，否则第三组不验收）？如果要放宽，需要 G1 审查和用户确认。
2. 能否补抓本次的 `evidence/mps-owner.json` 和锁监督进程的 stdout？
3. 编译 libsmctrl 时，远端 `/usr/local/cuda` 指向哪个 CUDA 版本？

**未解决的 BLOCKING：0 项。**