# CPU复制：实际内部绝对链接delta G2

独立/root/profile_instrument_review只读结论APPROVE，BLOCKING0。

第一次CPU检查在创建target前拒绝src/SpaceServe/vllm/_C.abi3.so绝对内部链接；exit1，未创建新root/未GPU。原helper stage_cpu-attempt0.py、staging-attempt0.log、approval-attempt0.json在专属辅助目录保留。

修复仅允许strict目标在实际复制集合的绝对链接，在newroot内转对应成员relative；转换前核原link身份，源前后原link/SHA不变，目标按转换期望独立核，双manifest保存。外部非解释器仍拒绝。Linux实际6CPU测试通过，无skip，包含真实内部绝对链接source不变/dest指向newroot测试。

执行前更新当前script SHA审批。批准不涵盖CUDA扩展可加载性、GPU或runner，须分别实际验证。
