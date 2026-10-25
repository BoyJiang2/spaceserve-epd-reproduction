> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g2-rgb-deployment-prompt.md) SHA256 9b8c6df10a638f2b4f2562490f59c40ccb848586a7ca9fd2014d5e27e9a3ac29。原数字及解释不变。

# G2补充：000部署遗漏RGB共享helper

只读核D:/Documents/codex/AGENTS.md，Claude额度失败接替仍有效。刚才cold重试通过MPS idle后，在模型加载前baseline_server.py import rgb_cache失败，PID3805389已清理退出1。新目录preflight-cold先保留原始，不覆盖；无正式请求。

最小部署修复：把outputs/spaceserve-h20-7b/scripts/rgb_cache.py逐字节复制至outputs/qjh000-migration/scripts/rgb_cache.py，再复制000；原helper不改（RGB448x448/20图/缓存SHA）。现baseline_server.py和check_rgb_cache.py都依赖它，新增无推理分支或采样变化。
实际CPU导入CUDA_VISIBLE_DEVICES为空并--help退出0，evidence/model-adapter-cpu-import.log；无GPU模型工作。请独立比较三份（旧7B/新000/封存reproduction helper），确认只补部署遗漏，批准冻结cold/restart继续，不批准formal/G3。其他代码无变。
输出结论、BLOCKING、NON-BLOCKING、QUESTIONS。
