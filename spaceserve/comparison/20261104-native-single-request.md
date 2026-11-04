# 11月4日：原生vLLM已完成Qwen2-VL-7B真实单图请求

本次为单H20、FP16、TP1、V1/eager、固定COCO000328及128目标输出的诊断。运行源为baseline/vllm-v0.7.2的d7ec548300d7950c1305231b2aaf970bab7569c1，tree与官方0.7.2相同、commit不同。没有正式吞吐、TTFT、TPOT或SLO结论。

[实际响应、退出与恢复释放](../validation/official-entry-20261104/s4-evidence.json) · [独立G3范围](../validation/official-entry-20261104/native-g3.md)。s4 HTTP200/curl0，usage prompt281/completion128/total409，finish_reason=length；主体描述三名军装人物坐长椅、读书和休息，与已核图片相符。关于身份和地点的猜测不作为事实，尾部换行原样保留。prompt tokens不能直接当视觉tokens，buffered响应不能证明客户端TTFT。

原work_exit0、cleanup_exit1、outer_exit1完整保留。收尾遇进程非Z退出过渡态environ拒读，严格拒绝不明身份；随后同run助手stop恢复exit0、known_live空、GPU3显存0。只批准恢复后受控释放，不能称原cleanup通过。下一候选助手设置250ms单次观察重试预算，live拒读到期仍拒绝，birth变化仍拒绝；CPU原问题复现及8项原真实进程测试通过，尚未在模型运行中验证该新收尾版本。

[有界助手](../tools/official_space_processes_bounded.py) · [启动脚本](../tools/official_space_first_request_bounded.sh) · [CPU结果及diff](../validation/official-entry-20261104/bounded-cpu.json) · [代码与fork诊断审查](../validation/official-entry-20261104/bounded-review.md)。服务器文件也在既有spaceserve/assets，原版不覆盖。

之前真实失败依次为：源码checkout缺_C扩展；limit参数JSON不符合native KEY=VALUE；缺vendored FlashAttention依赖。仅通过已有二进制软链、image=1参数、官方build清单的4个依赖软链逐项修复。_C及两FA二进制复用原env，0复制；两份FA Python与官方CMake固定pin字节相同。两PY精确排除项及全部SHA见[依赖manifest](../validation/official-entry-20261104/flash-links.json)和[固定来源对比](../validation/official-entry-20261104/flash-official-pin.json)。tracked源未改不等于二进制完整编译来源已证明。_version缺失仍显示dev，实际运行SHA按上述Git而非版本字符串追踪。

实际模型15.5313GB，vision采用原版xformers回退、V1 attention使用FlashAttention，sampling因无FlashInfer采用PyTorch回退；没有额外装包优化。日志/profile/配置完整原件留服务器/local/boyjiang/spaceserve/runs/s4，必要小证据含manifest大小SHA。

下一步为同单卡官方fork真实请求、实际设备/并发/有效encoder mask，再做冻结矩阵。原生首请求不证明fork、SM、二进制全面ABI兼容或正式性能，旧历史结果不拼接。
