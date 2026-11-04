# 11月4日SpaceServe：收尾修复准备，模型尚未运行

EPD真实单请求完成后发现共同CPU助手的stat→environ退出竞态；Space助手同样修复，只在相同birth且进程已经Z时按退出处理，活进程不可读或PID重用仍拒绝。两个启动脚本仅更新helper SHA。Space候选既有8项真实CPU测试及退出竞态/身份保护fixture通过，bash-n通过，独立G2 BLOCKING0。

[修复助手](../tools/official_space_processes.py) · [修复启动脚本](../tools/official_space_first_request.sh) · [共同错误/补丁/CPU原件及审查](../../epd/validation/official-single-request-20261104/) · [EPD实际请求报告](../../epd/comparison/20261104-official-single-request.md)。服务器原文件保留，选用既有assets内official_space_first_request_candidate.sh及HELPER=official_space_processes_candidate.py，按本commit工具SHA绑定；未改官方模型源码。

这次仅完成CPU工具修复，尚未执行SpaceServe模块/模型请求或SM机制验证。[单请求执行说明](../docs/official-first-request.md)仍适用，工具版本须使用本次修复commit，不能继续标成旧bf9版本。单H20、Qwen2-VL-7B FP16 TP1、native/fork真实路径与有效encoder mask仍待实际验证；没有新增吞吐或延迟结果，不称完整decoder互斥分区。
