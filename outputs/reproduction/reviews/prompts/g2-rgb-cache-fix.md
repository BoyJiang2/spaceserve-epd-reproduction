独立subagent G2事前复审。用户已授权Claude额度耗尽时由subagent接替，既有额度失败和前次审查保存。只读本地审查，不改文件，不运行实验/安装/网络/SSH/GPU，不读取凭据。项目根 D:\Documents\codex\2026-10-23\new-chat-2；先读 D:\Documents\codex\AGENTS.md 和 reviews/subagent-g1-g2-20261023.md。

本次具体补丁已准备，尚未正式运行。请读以下文件：
- outputs/reproduction/scripts/rgb_cache.py、check_rgb_cache.py、baseline_server.py、apply_epd_compat.py、start_server.sh、run_cache_fix_h20.sh，以及run_matrix.sh中REPRO_MATRIX_ROOT、LOW_LOAD_ONLY变更。
- work/test_rgb_cache_fix.py（4个CPU测试已通过：实际buffer变更可见、缺条目不隐式加载、RGB/448尺寸校验、重复名/路径逃逸拒绝）。
- work/epd-api-before-rgb.py 若已存在，是当前远端修改前API源码，只用于核对插入点。

修复范围：EPD和baseline-epd启动时设置相同manifest路径，baseline用现有Image.convert RGB填充原path-key字典，EPD调用原load_image_cache填充原basename-key字典；不改模型/调度/通信，也不额外模型前向或embedding/KV缓存。SpaceServe不启用此预载。共享只读snapshot函数从实际接口缓存取20张RGB buffer算像素SHA；检查端独立加载原图RGB作expected，通过/repro/rgb-cache比较各服务，前后各检查一次，不提交/generate请求。

补测脚本在现有专属root内新建results/cache-fix-single-c1-20261023，不覆盖旧矩阵和日志；同boot/cuBLAS守卫；先EPD三卡，再同三卡三个完整副本；各phase保留固定正确性/C8检查、运行时与RGB前后证据，实际benchmark仍全局20预热+100正式×3、1图C1、128tokens、原脚本同请求序列。结束只停止本实验进程树并检查GPU空闲；脚本/官方Python patch快照另归档。

请判断是否关闭原B1所需代码缺口（数据补测及G4仍待进行），有无新BLOCKING；具体补丁若可跑，请明确G2 APPROVE/APPROVE_WITH_NITS，否则REQUEST_CHANGES并列文件行号、理由、最小修复。不要将代码批准当数据批准。不必因仅落实原相同缓存条件要求而额外推导用户确认；若实际改变固定设定则指出具体改变。

补充复审实际范围：先将runtime capture移动到正确性后、benchmark前；CPU集成测试发现既有output IDs插入guard幂等问题后，改为优先识别完整new_text并跳过，保留首次old_text唯一性断言，测试连续应用两次字节不变、预载/lookup/route使用同20实际RGB对象。另为完整复跑版run_epd_h20.sh在EPD/三副本矩阵前后增加相同只读cache检查，共四行，不影响当前补测运行。这些收尾均已分别交同一独立审查者只读复核，结果另存。
