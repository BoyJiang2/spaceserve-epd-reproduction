# 独立G2：仅CPU环境/模型/源码复制

只读、不运行实验/联网/GPU/凭据、不修改文件。Claude额度耗尽，独立subagent接替。读plan.md和g1-plan-v1-subagent.md。

审scripts/stage_cpu.py、test_stage_cpu.py、freeze_schedule.py、test_schedule.py。stage只从旧封存读入新root，精确固定member，SHA前后相等、双份空间预算、禁止共享inode/越界软链/现有destination、权限700，不复制旧evidence/marker、不导入Torch。新root只有CPU_STAGED，不是模型/机制批准。系统/usr/bin解释器链接例外，其他symlink必须relative并在所属root内。copy失败保留断点不删除。approve gate须绑定本脚本SHA与Space-CPU-stage-only范围。

现正式冻结schedule-v2 SHA7248d8829180d3df25f04204cd7e1e89b7b7462ea5f39651986f118418c0d8d3：54cells，负载内各角色位置恰一次，全矩阵每对先后9:9，负载内仍2:1。早schedule.json未执行候选不作为正式配置。当前仅CPU测试，没有远端部署或GPU运行。

请输出G2结论/BLOCKING/NON-BLOCKING/QUESTIONS。此次批准最多CPU复制及顺序配置，不批准新运行器、数值或模型GPU。
