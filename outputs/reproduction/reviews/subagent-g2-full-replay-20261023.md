**G2补充结论：APPROVE；BLOCKING：0。**

独立 subagent `/root/fallback_g1_g2` 已只读核对 `outputs/reproduction/scripts/run_epd_h20.sh:73,76,88,91`：

- EPD检查位于第2 epoch矩阵前后，覆盖实际单端点。
- 基线检查位于矩阵前后，覆盖三个实际副本端点。
- 四份证据分别写入独立的 `*-rgb-before/after.json`。
- 调用的检查器仅访问 `/repro/rgb-cache`，没有推理请求；未改变预热、正式请求或模型参数。

该补充可纳入最终完整复跑版本，不影响当前补测批准。未执行脚本；实际数据有效性仍由后续G4审查。
