# SpaceServe 固定运行入口（迁移候选）

本目录是唯一维护入口，来源为 [ecad958 冻结版本](https://github.com/BoyJiang2/spaceserve-epd-reproduction/tree/ecad958fdc9f09f8f3d39e3eef7c08d43db634df/spaceserve/code/h20-window-20261028)。本次重构尚待完整独立审查、发布和 qjh003 实际验证；不能复用旧 qjh000 批准。

固定根 `/local/boyjiang/spaceserve/` 下，`repo/` 为指定 commit，`assets/` 保存唯一模型/环境/框架/图片，`runs/<run-id>/` 仅冻结少量代码、两份实验动态库、实际配置和证据。模型与环境不按运行复制。默认 [候选配置](configs/project.candidate.json) 没有预约、UUID 或执行许可，会拒绝 GPU 动作。

```bash
python3 spaceserve/runtime/entry.py plan
# 仅在 CPU 预约、资产迁移逐 SHA 验收及适用独立审查后：
python3 spaceserve/runtime/entry.py prepare --config /absolute/reviewed-config.json --commit <pushed-full-SHA>
# 后续必须使用本次冻结配置，依次 CPU、numeric、实际独立 G3、model、实际 G3、formal：
python3 spaceserve/runtime/entry.py cpu --config /local/boyjiang/spaceserve/runs/<id>/configs/project.json
python3 spaceserve/runtime/entry.py numeric --config /local/boyjiang/spaceserve/runs/<id>/configs/project.json
# model/formal 各自还需实际证据与对应批准，入口不替代 Gate。
python3 spaceserve/runtime/entry.py analyze <trace-directory> --server-log <log> --output <new-output.json>
```

Space 三组仍是同单 H20、Qwen2-VL-7B、FP16、TP1、eager：native / 编码器解耦 / 有效 encoder mask。54 单元、5400 正式＋1080 预热，313 模型预检、201 分钟入场、每单元900秒、截止前120秒清理均不变。未验证 decoder 互斥，不能称完整 SM 分区。

`configs/source-files.json` 是冻结成员索引；哈希由指定 Git commit 部署时生成，避免清单自哈希循环。模型/输入/框架内容锁在 `asset-content-pins.json`。历史生成器、旧预约与旧审批不作为当前运行代码，原件仍在上述精确历史 commit。旧批次原始数据、封包和 Release 不变。

本目录的 CPU 测试只覆盖相应软件契约，不能证明新主机实际 CUDA、MPS、并发或 SM mask 生效。阶段失败保留原件，不覆盖 claim、不自动重试。
