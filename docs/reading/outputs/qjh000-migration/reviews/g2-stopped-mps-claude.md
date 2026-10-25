> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g2-stopped-mps-claude.md) SHA256 3b1b3c4365d079a2bff874d73e54cd5a69705252b2a5bd71d8bcaf568de94de9。原数字及解释不变。

# G2 审查：qjh000 清理已停止 MPS 的残留 socket（逐位校准小补丁）

**结论：APPROVE_WITH_NITS，BLOCKING 0 项。** 清理步骤，以及它在两个 preflight 里的调用位置，可以批准。

审查者为 Claude（claude-opus-5-5），沿用之前的会话，只读。我对照了真实源码和已保存的状态，没有仅凭主执行者的说明下结论；没有改文件、跑实验、碰 GPU 或读凭据。

本次批准按以下 SHA256 绑定：

| 文件 | SHA256 | 状态 |
|---|---|---|
| `prune_stopped_mps.py` | `f6e531f9…6c06e950` | 新增 |
| `preflight_sm_layout.sh` | `571ded3a…6c743f9` | 修改 |
| `probe_sm_layout.cu` | `88dcb6ad…82ce585` | 修改 |
| `service_sm_probe.cu` | `d4732a66…6989a17` | 未改 |
| `preflight_model.sh` | `192f3816…39de81ea` | 只批准 `:37` 的清理调用 |
| `mps_owner.py` | `2dfa155d…` | 未改 |
| `gpu_exclusive.py` | `c0ee2e2f…` | 未改 |
| `env.sh` | `983ffff5…` | 未改 |
| `mps_control.sh` | `c82a00be…` | 未改 |

`preflight_model.sh` 的其余部分仍由单独的 model-service G2 审查。批准范围不包括 7B 服务、SM_EFFECTIVE 和第三组。逐位校准的实际结果另做 G3。

## 对照源码与状态的核对

| 项目 | 结果 |
|---|---|
| 现场状态 | `evidence/mps-owner.json` 记录 `state=stopped`，PID 3458093，control_inode 4831151。`mps-stale-socket-observation.txt` 显示：目录 inode 4831144、uid 2147、权限 700；control 为 socket、inode 4831151、uid 2147、权限 666；GPU0 计算进程表只有表头。socket 的 inode 与停止记录完全一致。目录是 700，所以 socket 的 666 不会暴露给其他用户。 |
| 前置条件 | `prune_stopped_mps.py:9` 要求主机是 qjh000、EXP_ROOT 是固定路径、`REPRO_HOST_LOCK_HELD=1`。`:13` 处理悬空 symlink。`:16-18` 用 lstat 确认目录本身不是 symlink，且为 700 权限、属本人 UID；`resolve()` 结果与原路径相同，说明路径上没有 symlink。 |
| 身份核对 | `:20` 要求 state 为 stopped，记录中的 pipe 路径与目录一致，token 带专属根目录前缀。`:22` 只要记录的 PID 还在（包括 PID 被别的进程复用）就拒绝。`:24-26` 主机上只要有任何 nvidia-cuda-mps 进程就拒绝。`:27-29` 用 lstat 确认 control 是 socket、属本人 UID，且 inode 与停止记录一致。 |
| 先存证、再操作 | `:34` 以独占方式（`open('x')`）先写新的证据文件，`:36` 再核对一次 inode，`:38` 只 unlink 这一个路径。脚本不发 quit 或 kill，其他文件不动。 |
| 不会与本项目其他步骤并发 | 本项目所有 MPS 启动都必须持有主机锁（`mps_control.sh:3`），目录又是 700，检查与删除之间实际上不会有其他进程插入。 |
| 调用位置 | `preflight_sm_layout.sh:12` 在持锁之后、`:16` 检查 control 不存在之前；`preflight_model.sh:37` 在 trap 之后、`:38` 启动 MPS 之前。清理失败时 `set -e` 会直接退出，不会进入 GPU 步骤。删除后 `mps_owner.py:43` 不再拒绝启动。 |
| 上一轮建议的落实 | 标签改为 `unmasked-stream-default`（`:44`）；`:29`、`:36` 补了 stderr 说明；探针加了 `timeout --kill-after=10s 300s` 和每次运行的起止时间（`:62-69`）；运行前用 `sha256sum -c` 绑定代码（`:5`，未持锁和持锁后各跑一次）；`used-code.sha256` 加入了 env.sh 和 gpu_exclusive.py（`:38`）；记录了服务端库的 SHA（`:31`）和 helper 导出符号（`:30`）；停止后复制 owner 状态、GPU UUID 和 MPS 日志（`:73-75`）。 |
| helper 符号问题 | `helper-exports-before.txt` 只导出 `repro_sample_actual_stream`、kernel stub 和 dim3 构造函数，不导出任何 cudart API。所以 helper 在 torch 进程里仍用它自己的静态运行时，不会被 torch 的 libcudart 替换。保留原链接参数合理，上一轮第 1 点关闭。 |

## BLOCKING

无。

## NON-BLOCKING（按重要性）

1. **证据文件名只用 inode，可能撞名后反而卡住。**
   - `:30` 生成的文件名是 `mps-pruned-socket-{inode}.json`。ext4 会复用已释放的 inode。
   - 如果逐位校准时新 daemon 的 socket 又分到 4831151，那么之后 `preflight_model.sh:37` 再次清理时，`open('x')` 会因文件已存在而报错，整个预检停下。这是失败即停，不涉及安全。
   - 建议文件名加上 owner token 的随机后缀或时间戳。只改文件名，不改判断逻辑。

2. **`preflight_sm_layout.sh` 中清理的执行顺序。** 删除（`:12`）发生在两项只读检查之前：OUT 不存在（`:14`）和 GPU 空闲（`:15`）。不影响安全，因为这个 socket 本来就是残留。建议把清理移到 `:15` 和 `:16` 之间，等只读条件都通过后再改动状态。

3. **代码绑定还缺清理脚本。**
   - `sm-layout-approved-code.sha256` 本地还看不到，它必须包含上表全部执行代码，尤其是 `prune_stopped_mps.py`。`sha256sum -c` 只检查清单里列出的文件。
   - `used-code.sha256`（`:38`）也要加上 `prune_stopped_mps.py`。
   - 建议把 `sm-layout-code-check.log` 和清理记录复制进 OUT，它们现在只放在共享的 evidence 目录。

4. **清理记录写在删除之前。** 若 `:38` 的 unlink 失败，记录里的 `removed_socket` 字段会有误导。建议删除成功后再追加一个确认字段，或另写一行完成记录；同时加上时间戳和 boot_id。

5. **可选：加一项被动的存活检查。** 除了看进程名，再查 `/proc/net/unix` 里是否还有进程在这个路径上监听，并记录 `st_dev`。

6. **helper 的符号证据还可以补强。**
   - `:30` 只列已定义的符号，建议再保存 `nm -D --undefined-only`，证明没有导入 `cuda*` 符号。
   - 现在的 `helper-exports-before.txt` 没写对哪个二进制、用什么命令生成。
   - nvcc 的临时文件名可能使每次编译出的 SHA 不同，正式运行编出的 helper 未必等于 CPU 试编的 `7931ec34…`。服务应以 `results/sm-layout/binaries.sha256` 为准。

7. **“原生库与服务库 SHA 同为 `529e2502…`”本地还无法核对。** 远端的 `evidence/libsmctrl.sha256` 没有抓回。`:31` 会把服务库 SHA 写进 OUT，留待 G3 核对。

8. **两个说明，不需要改：**
   - 失败退出时 `:73-75` 的复制会跳过，owner 状态只留在共享路径，可能被下一轮覆盖。
   - `timeout` 会把探针放进独立的进程组，锁监督进程发出的 TERM 到不了探针。bash 要等探针结束才执行 trap，最坏情况下会持锁约 310 秒，有上限，可以接受。

## QUESTIONS

1. 批准后写入的 `sm-layout-approved-code.sha256`，是否与上表的 SHA 逐项一致，并且包含 `prune_stopped_mps.py`？
2. `tmp/mps` 里除了 control 是否还有其他残留（例如 log socket）？清理脚本按设计不碰它们。若新 daemon 因此启动失败，会失败即停。是否在 MPS 启动前把 `ls -la tmp/mps` 存进 OUT，便于诊断？
3. 确认 `preflight_model.sh` 只有清理调用属于本次批准，其余仍待 model-service G2。

**未解决的 BLOCKING：0 项。**