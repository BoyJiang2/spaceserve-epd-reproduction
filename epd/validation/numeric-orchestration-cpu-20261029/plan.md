# EPD native36：本地接线实现范围

承接numeric-native-design-v2与已完成numeric_cache组件；当前仅本地源码与CPU mock，不SSH、不Ray/Torch/NVML/CUDA初始化、不GPU部署，不改变36/0模型/1800秒/三卡/.65/340分钟及零重试预算。qjh003实际CPU10–16他人占用，刚才路径apply在CPUguard写前拒绝，不能拿用户未预约CPU许可继续远程。

这一步补独立numeric_unit.py有限编排核心及测试：直接复用transfer_vector生成12个有向pair/载荷组、每组3copy、每组全新3个model-free worker身份映射；不写玩具通信。每次admit_transfer后持久化submitted，再调用现有prepare/copy原生组件；匹配实际source/target UUID、full geometry和完整验证记录。成功后target同步→确认importer PID/context退出→source退出→unused第三actor退出；任失败无后续transfer/group、保留raw并只对已验证身份做有界cleanup，未知拒杀/未确认release阻断下一组。一个claim/commondeadline，不按group重加时间。编排核心只接受有限backend操作，GPU依赖将留在后续真正Ray/NVML adapter、且必须在原有GPU grant/source/booking/durableClaim之后惰性导入。

顺带解决已定位的接线矛盾：为分配前核三actor真实UUID，要先调用资格identity，但capture_own_identity为独占文件，allocate再次调用会写同名sidecar失败。只给numeric probe增加identity缓存/同步窄动作，allocate复用由该worker自己实际产生的numeric identity；普通模型qualification_identity路径不改，不给模型路径增加缓存或宽松身份。拒重复identity/已有model_runner/非DECODING/未opt-in；同步只在已登记numeric身份后进行，0模型请求/0额外transfer。

验证：本地纯CPU fixture覆盖12fresh组/36唯一向量、每次charge→submitted→prepare→copy的真实调用顺序、37拒绝/失败不重试、重复或错UUID/几何/不完整结果拒绝、importer先exit及未确认release不放下一组、未知身份不杀但cleanup已知兄弟；identity侧仅实际capture一次/allocate不二次写、sync前置/普通模型拒绝。fixtures全标CPU-MOCK，绝不生成GPU PASS、G3或正式数据。保持fixed_unit numeric/selected当前fail-closed，不因组件存在提前放行；下一步Ray2.10.0实际actor/NVML/claim前端接完并独立G2后才开numeric分支。selected360与公平PD整体仍未完成。

修改面限epd/runtime/numeric_unit.py、numeric_cache.py及相应tests；不重构现有能运行的资格/校准/调度/传输层，不复制vN工程/旧源，不改Space。当前审批仅本地组件+CPU测试及后续精确源码发布；真实GPU与完整controller接线另审。本文件不请求新GPU预算。
