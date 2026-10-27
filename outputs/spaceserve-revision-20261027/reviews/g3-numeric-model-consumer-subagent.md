# 实际numeric证据向model-preflight consumer迁移G3

独立/root/numeric_g3_review只读：APPROVE，BLOCKING0。

- 原40项+原Gate共41，映射完整无重复/额外，原/归档bytes及SHA逐项相同，路径声明匹配。
- 原Gate SHA与mapping一致；numeric18全部不变，producer13a5539d1947c82c468372c193fc12b10eb8ac984513fbb3256e80e751c4795b保持。
- model_guard要求scope Space-numeric-for-model-preflight且model_correctness_approved=false，再独立model G2。

同意booking/MPS可变状态后续更新，consumer绑定mapping和41项archive，原producer不改，无需重跑。仅允许数值证据向模型预检过渡，启动仍须model G2/CPU/部署/fresh资源，不证明实际模型/encoderstream或正式。未执行GPU/远端。
