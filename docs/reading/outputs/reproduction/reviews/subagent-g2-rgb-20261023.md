> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/reproduction/reviews/subagent-g2-rgb-20261023.md) SHA256 184e76e836ab1e7ef03e0071eeca90594327ab4a40cb7ef851c7a00f317c8b62。原数字及解释不变。

**G2：APPROVE_WITH_NITS；BLOCKING：0。**

实际审查者：独立 subagent `/root/fallback_g1_g2`。这是本次 RGB 修复的补测前审查，不追认历史实验。已只读审查提示词列出的代码、CPU测试源码、原 API 插入点及必要调用脚本，未运行测试、实验或访问远端。

本次补丁已解决原 B1 的**代码缺口**：

- `outputs/reproduction/scripts/start_server.sh:14–17` 为 EPD 和 baseline-epd 设置同一 manifest，SpaceServe 不启用预载。
- `baseline_server.py:46–57` 将图片加载到 `/generate` 实际使用的 path-key 字典；`apply_epd_compat.py:78–99` 通过原 `load_image_cache` 填充 EPD 实际使用的 basename-key 字典，插入位置在函数定义之后。未发现新增模型前向、视觉特征、embedding 或 KV 缓存。
- `rgb_cache.py:17–25` 从实际缓存对象计算 RGB 像素 SHA，缺失条目不会隐式加载；`check_rgb_cache.py:17–30` 独立读取原图生成 expected，并核对每个服务的20张图片、尺寸、mode、manifest及像素内容。校验使用元数据接口，没有提交推理请求。
- `run_cache_fix_h20.sh:13–20,45–76` 使用新的结果及日志目录，先 EPD 三卡、再同三卡三个完整副本，保存前后缓存证据并限定进程清理范围。
- `run_matrix.sh:18,41–49` 将本次运行限定为单图/C1，仍调用原 benchmark、全局20推理预热、100正式×3、128 tokens；未修改请求序列或丢弃重复。

因此，这属于落实既定“相同缓存条件”的最小修复，没有改变用户固定的实验参数，无需额外确认流程。**当前实际补丁可进入定点补测。**

NON-BLOCKING：

- `run_cache_fix_h20.sh:58–66` 在正确性请求之前调用 runtime capture，而后者要求三个 worker 均已加载两个 cuBLAS 库。若某 worker 需要首次前向才完成库加载，流程会安全停止。建议把 runtime capture 放在正确性检查之后、benchmark之前，避免这种启动顺序造成的误拒绝；目前没有证据证明该失败必然发生。
- 本次正确性检查只请求基线 `URLS[0]`，缓存校验则覆盖全部三个副本。后续记录应准确区分这两个覆盖范围，不称三个副本分别通过了独立 C8 正确性检查。

QUESTIONS：无阻塞性问题。

CPU测试已报告通过；我只审阅了测试源码，未独立重跑。此结论批准代码进入补测，**不关闭 B1 的数据问题**：两台机器的成对补测、实际前后 RGB 校验及 G4 数据复审仍须完成，G5 尚未获批准。
