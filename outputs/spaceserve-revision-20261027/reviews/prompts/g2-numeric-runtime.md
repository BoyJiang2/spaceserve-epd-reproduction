# G2：仅Space数值预检候选

只读、不改文件、不GPU/远端/凭据。Claude额度耗尽接替规则见AGENTS及work/repository-upload/g1-plan-claude.json。请审scripts/run_numeric.py、probe_runtime.py、probe_sm_mask.cu、resource_guard.py、booking_window.py、mps_owner.py、mps_control.sh、env.sh、test_lifecycle_signals.py。

已G1冻结单H20 GPU4 UUID79214...、FP16/Qwen7B三组六负载54cell，G2 CPU独立复制实际32643项/23735714281bytes通过，原源不变。此次只请求部署这些守卫并在实际CPU测试/manifest/fresh预约/资源后numeric action；不模型、不正式。

resource_guard/booking/owned是既有EPD受审逻辑新root/单卡变更，证据CPU_STAGED schema不同已适配。独立数值FP16一次与私有MPS的三轮unmasked/mask/clear/reapply，不加载模型；严格包含/恢复/reapply判据。实际模型stream仍另G3。保留旧host lock只读字节不变，新锁+截止前120秒信号finally清理。MPS仅UID/私有pipe/token/creation记录可验证时控制；未知拒绝。

注意所有目标代码尚未部署/未GPU；本地AST通过，POSIX真实TERM/ALARM待目标CPU补跑，不拿Windowsskip当PASS。scripts其他baseline/正确性/SM集合helper是后续模型候选，不在此次numeric授权。

输出G2结论/BLOCKING/NON-BLOCKING/QUESTIONS，指明允许numeric与否。后续代码manifest必须绑定实际部署脚本和复制库SHA；fresh GPU预约仍单独核验。
