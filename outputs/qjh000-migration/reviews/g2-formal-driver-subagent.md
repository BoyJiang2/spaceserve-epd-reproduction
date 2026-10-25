# G2：000正式driver

实际审查者 /root/profile_runner_review，只读，Claude额度接替，提示g2-formal-driver-prompt.md。
结论APPROVE_WITH_NITS，新增BLOCKING0。核driver/依赖和5项CPU回归：入口G2/G3、boot/SHA、清diag/profiler；有效SM才第三组、roles入points SHA；先两点、持同MPS及锁、G4 bytes完全匹配并双层清单payload后扩四点；20warm+100x3/128tokens；失败/外来PID/内存缺采样停止；后台守卫含同root孤儿，不终止外来。
NON-BLOCKING：pidfd cleanup未来修复不在本次批准中，需单独G2并重冻结；真实服务G3/SM证据仍须独立审查。本结论仅批准条件化代码，不代表当前可启动formal。审查者未改文件/运行代码/访问GPU。
