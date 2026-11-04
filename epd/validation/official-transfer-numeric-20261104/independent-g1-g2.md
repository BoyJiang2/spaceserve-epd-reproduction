# 独立小张量传输诊断 G1/G2

独立审查者：subagent /root/official_epd_runtime_review_1104。2026-11-04；仅依据主执行者转送方案、源码和实际CPU回执，不独立读取文件、执行命令、核验SHA或访问GPU。

方案：不改官方源码，使用现有fdb86ae5二进制。三卡三个spawn进程，E→P视觉张量[5,3,8]、P→D KV[2,2,5,3,2,4]，FP16整数pattern，src[4,1,3]→dst[0,4,2]，检查逐元素精确相等及未写sentinel。生产、目标初始化、接收均显式同步，禁CUDA缓存；D退出后P退出，最后E退出。180秒工作共享截止，120秒清理，60秒保存，单元360秒。仅自身spawn/pidfd清理，无模型、Ray、MPS。

G1实际结论：APPROVE / BLOCKING 0，限现有二进制的独立数值传输诊断。成功也不证明原模型异步顺序、多请求KV语义、二进制构建来源或性能。

v1 G2实际结论：REQUEST_CHANGES / BLOCKING 2。

1. ProcessLookupError退出竞态可能跳过其余child及terminal，需实际修复并验证父SIGTERM。
2. 两消费者target初始化后、迁移前必须显式同步。

还要求核实真实返回契约：官方C++get_ipc_mem_handle返回vector<int64_t>；两register及unregister返回bool；两migrate为void。转送源码已核，GPU实际schema尚未测。

v3最终返回原文：

v3 G2 **APPROVE / BLOCKING 0**，限8282B版本：

`f82911cbed5b0b01dbba8ef36fc4b265debd1b855293f60ec1bca940fc6c9e6c`

两项BLOCKING已按转送证据闭合：退出竞态由专用helper处理，真实父SIGTERM测试完成三child收口；两消费者均在初始化后、迁移前同步。补充的真实C++返回契约也支持register／unregister断言，未误把void返回作成功标记。

精确版本离机发布核同后，依既定G1条件fresh核资源及360秒单元余量，可执行该小张量诊断。保留v1/v2及各CPU原件；GPU后仍须核每条数值路径、退出与释放。

禁缓存是该诊断的明确条件，不能外推模型缓存分配和原异步调度正确；未实际记录或核验的指针／storage offset也不能写成已测证据。

本结论依据转送代码与CPU回执，未独立读取、重算SHA或执行GPU；数值G3尚未通过。
