# EPD native36有限编排：本地CPU-MOCK验证

本批是源代码/CPU契约验证：**24项PASS、0skip；没有Ray/CUDA/NVML实际执行或真实IPC传输，不是numeric G3。** 生产numeric/selected入口仍fail-closed，公平PD整体尚未完成。[EPD项目与历史baseline对照](../../README.md)独立保留。

实现[有限编排核心](../../runtime/numeric_unit.py)，复用原36向量，每组三次、12组fresh身份；逐次charge→submitted→prepare→copy，一个1800秒共同deadline，向backend传入剩余时限。normal同步后按importer→exporter→第三actor顺序确认原始Proc/NVML释放记录；失败时若importer退出未确认，保留有IPC依赖的exporter，只清理独立合法actor并阻断下一组。真实Ray/NVML adapter尚未接入，持久化与连续采样须由该真实后端实现并另审，当前组件不能提前开GPU入口。

[numeric_cache窄修改](../../runtime/numeric_cache.py)仅为numeric identity捕获/复用与同步：解决分配前登记UUID后allocate二次写独占身份sidecar的问题；普通模型qualification_identity未缓存、不放宽。未改KV/VE原生通信方法、模型参数或正式实验协议。

[新测试源码](../../runtime/tests/test_numeric_unit_cpu.py)与[原缓存契约测试](../../runtime/tests/test_numeric_cache_cpu.py)均为明确CPU-MOCK。第一版23PASS使用了过弱的失败清理断言；独立G2发现importer未确认时仍释放exporter。先改测试，真实复现24项中的3失败，再修复依赖顺序，最终24PASS/0skip。旧23记录、3失败反例和修后原始stderr均保留，不把旧通过追溯改成新通过。

- [原23测试前后源码及expected IDs](local-tests/inputs.json)、[原结果](local-tests/result.json)。
- [修复前反例](local-tests/importer-regression-before.stderr.log)、[其源码绑定](local-tests/importer-regression-before.json)。
- [最终24测试原文](local-tests/importer-regression-after.stderr.log)、[最终源码/测试SHA及退出码](local-tests/importer-regression-after.json)。
- [当前四个源文件SHA](source-manifest.json)、[G1](reviews/g1-numeric-orchestration.md)、[G2及修订审查](reviews/g2-numeric-orchestration.md)。

本地复跑只需Python标准库。在仓库根下创建专属可写临时目录，将`EPD_CPU_TEST_TMP`设为该绝对目录，并用`python -I -S -B -m unittest discover -s epd/runtime/tests -p "test_numeric*_cpu.py" -v`运行。测试只生成CPU-MOCK临时文件，不需要模型、Torch、Ray、CUDA或服务器；临时目录应在受控工作区，禁止指向旧成果。原执行命令/60秒上限见[command.json](local-tests/command.json)，其中原Windows绝对路径属于原执行证据。

这里只验证有限编排/接口/异常条件，不能证明真实actor创建、完整GPU缓存分配、native36数据一致性、连续NVML归属/峰值或实际context退出。下一步真实backend及durableClaim前端仍须实现、CPU验证和独立G2；真实GPU须新的合法资源、指定源码部署及独立实际G3。
