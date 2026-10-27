# G2 Space整批分析初审
独立/root/profile_instrument_review，REQUEST_CHANGES，BLOCKING2。
1. G3原件绑定需显式原件SHA与完整清单校验，补删空/删一项绑定负例。
2. MPS/显存需交叉前后server/GPU UUID/物理进程身份，窗内样本拒重复/未知PID/非法bytes及串用其他cell记录，补反例。
三配对区组/df2/完整性及全局冲突禁用逻辑正确。只读未运行代码或远端。

主agent处理：原formal15清单SHA已间接绑定同G3原件，仍采纳显式6364...f222及347项检查，使信任边界清楚。MPS前后client/server/截断与完整UUID/physical集合严格一致，显存PID只允许本cell已核worker和MPSserver，拒重复/unknown/非整数负数/大于物理用量的单进程值。保留MPS合计可能含shared allocations限制，不称物理容量使用。
新增删空/删一项G3、server/UUID错、串用PID/重复PID/非法bytes负例，15CPU PASS。实际旧六组model-preflight boundary格式本地复核也PASS；不是formal数据G4，源不改。复审待。
