> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/reproduction/reviews/h20-replay-provenance.md) SHA256 430d8d5ce66bad353ee02aa4381b387b9fe54feba519e126496c23e4dba18998。原数字及解释不变。

# H20 运行快照与复跑版本

本页记录RGB修复前的初轮整理状态。缓存修复后的当前版本对照另存 `report/h20-final-script-provenance.json` 与 `reviews/h20-final-replay-differences.diff`；定点补测实际使用的7份新源码SHA见 `report/cache-fix-code-manifest.json`，避免把前期的“13文件一致”误当作最终版本仍完全一致。

`report/h20-script-provenance.json` 给出17个相关脚本的 SHA256。两台归档快照在这17个文件上逐字节一致。13个文件还与当前交付版本一致，包括压测、基线适配器、服务启动、矩阵执行、环境、GPU采样、EPD兼容补丁、正确性、P2P/KV/embedding/BLAS探针和安全停止脚本。

四个差异已保存在 `h20-replay-differences.diff`：

- cuBLAS修复脚本增加uv路径回退，目标库版本不变。
- preflight由qjh003名称改为H20名称，并串入实际单独执行过的BLAS与embedding检查。
- 主流程改为H20名称，并串入运行时采集和postflight；压测参数及请求序列不变。
- bootstrap创建evidence目录、在H20覆盖cuBLAS，并只复制普通脚本文件，避免复制Python缓存目录报错。

两台 `evidence/<host>/execution-helpers/` 从远端原路径只读取回实际的 `watch_h20_finish.sh` 和 `collect_h20_delivery.sh`。原流程没有内联的baseline运行时快照和postflight由watch helper执行，对应日志位于各主机 `logs/finish-validation.log`。EPD运行时快照另在各主机 `epd-runtime.json`，包含采集时间、GPU UUID与加载库路径。

这些文件是归档时的源快照和记录；仅凭哈希不能证明历史上每一次命令的执行。需要结合运行日志、runtime、原始请求、完成标记及数据检查判断。当前整理后的脚本尚未被声称“在本轮重新全流程复跑过”，也没有因补审而启动额外实验。
