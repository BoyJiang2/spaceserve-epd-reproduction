> GitHub阅读副本：仅修正链接；[封存原文](../../../../../outputs/qjh000-migration/reviews/g3-model-final-subagent.md) SHA256 9539c7a38719cf7d61374e09cf06dd2e2e96e178e002c2187920ecdc12a37f16。原数字及解释不变。

# G3最终：7B三组cold+restart

实际审查者 /root/profile_plan_review，只读，Claude额度接替依本批。提示g3-model-final-prompt.md。
结论G3 APPROVE_WITH_NITS，BLOCKING0；cold+restart足以验收第三组“编码器实际stream的SM掩码生效”。

承接已批准cold，独立核restart45固定案例，90总案例input/output IDs/routing/长度/原生reference一致，RGB20前后及跨重启相同。API/worker/MPS均新身份、同物理UUID，参数FP16/CUDA0/配置相同；显存逐样本PID/求和正确，无foreign GPU进程。
Masked同PID4097863/同stream再次78→64→zero78→reapply64→首次64，unmasked均78；读重启后补实测service-sm-check-after-restart.txt，helper3be03cf88212241b7b5de47673939170d5781a0fcce57839be9c9fcb194b3a1b和lib529e2502...与实际校准相同，注明此为重启后检查。
5restart gzip完整流读/CRC/SHA/worker核验，无辅助probe kernels。独立相对时间交叠unmasked1.192614s/35.6256%、masked2.696985s/68.6218%。批准代码/归档脚本与cold一致，COMPLETED、supervisor exit0、MPS stopped/GPU空。
NON-BLOCKING：仅encoder stream mask及采集片段并发，不称decoder互斥/完整SIS/TPC个数/资源比例/overlap加速；保留失败和epoch浮点量化说明。主执行者可据此记录G3及有效SM，正式仍须G2/冻结code/关闭probe和profiler/排除本项目后台负载。审查者未写marker/启动GPU，总goal未完成。
