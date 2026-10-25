继续同一Claude会话，独立只读G2小补丁，不改变GPU实验设定，不放宽SM布局验收。禁止改文件、GPU/实验、凭据。

此前G2逐位校准已APPROVE_WITH_NITS/BLOCKING0。现补处理您提出的旧MPS endpoint检查：000实际原daemon3458093已经quit/wait且owner记录state=stopped、无任何nvidia-cuda-mps进程、GPU0无计算进程；control仍存在，实际type=socket、inode4831151、uid2147，目录700。它是Unix socket不是FIFO，证据evidence/mps-owner.json、native-sm-launch.log和新evidence/mps-stale-socket-observation.txt。

新增scripts/prune_stopped_mps.py：仅000固定root+已持host锁，目录非symlink且700/UID/绝对解析匹配；owner state=stopped、pipe路径/token前缀匹配；旧PID不存在、任何MPS进程出现均拒绝；control必须socket/同UID/与已停止state的inode完全一致，二次inode检查后只unlink这个socket，其他文件不动、不发quit或kill。完整旧owner证据先写唯一新文件保留。preflight_sm_layout.sh与preflight_model.sh在私有MPS启动前调用；未执行unlink，等本G2批准。正式driver的未来使用另G2。

逐位校准非阻塞落实：native label改unmasked-stream-default；每probe timeout300s+kill-after10s；记录每次时间、最后stopped owner/MPS日志快照/服务lib SHA、env及supervisor代码SHA，运行前sha256sum-c绑定审批代码。不新增宽范围掩码或额外性能设定。

已用nm-D实测helper只导出repro_sample_actual_stream、kernel stub、dim3构造，无cudaMalloc/cudaLaunchKernel/__cudaRegisterFatBinary导出；evidence/helper-exports-before.txt，原CPU helper SHA7931ec34...。因此保留原静态cudart链接参数，不引入不必要重链flag；服务将复制本次实际校准so并逐字节SHA验证。原生库与服务build/lib SHA完全相同529e2502f633b0d7ef07db2848c64e42154cea73992a794c27a31d0361e5e7c5。

请确认小清理步骤及调用可批准，实际布局结果另G3；输出结论、BLOCKING、NON-BLOCKING、QUESTIONS。您可以对照真实源码与已保存状态，不以主执行者保证代替。
