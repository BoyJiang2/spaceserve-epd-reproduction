> GitHub阅读副本：仅修正链接；[封存原文](../../../../outputs/epd-profile-a/README.md) SHA256 16144d9f4f8156fb57ec46a1c9ed29c6511b89c6cbde9bc78718132c35fc742e。原数字及解释不变。

# EPD方案A受限交付

测量来源为qjh003，8配置、2400正式请求、160预热；后续CPU分析在qjh000执行，未重跑测量。本批为独立G1/G5批准的EPD方案A受限交付，不代表SpaceServe或总目标完成。

- 报告及图：report/report.md、throughput-latency.png/.svg。
- 统计和CUDA关联：report/performance.json/.csv、cuda-analysis.json。
- 逐请求、全部原生Nsight报告与SQLite、实际运行脚本：results/formal/。
- 代码、补丁和依赖：analysis/、scripts/、src/、instrumentation.patch、各case的runtime.json和实际used-scripts。
- 原始运行命令：results/formal/used-scripts/run_profile_a.sh；pilot命令、正确性和审查见results/、evidence/、reviews/。不要为复算而重新启动GPU作业。
- 复算：见report/report.md。需要旧封存reproduction目录及同级reproduction-h20.zip，其固定SHA由aggregate.py验证；新批次不会修改旧包。
- CPU分析使用Python3.10标准库；绘图使用Matplotlib3.9.2、NumPy1.26.4。分析没有GPU依赖。
- SHA256SUMS覆盖交付payload，忽略Python生成的__pycache__和.pyc；外层ZIP完整性记录位于同级outputs目录。

原统计/阶段CUDA及新增通知分析G4、交付G5均APPROVE_WITH_NITS；G5 B1/B2已关闭，BLOCKING0。最终归档SHA/CRC和旧封存校验见同级outputs/epd-profile-a-integrity.json。高EPD仅路径存在性、未缩窗重采，off因果瓶颈未解释。已明确的少量输出差异、边界跳过活动和观测扰动均保留，详见报告。
