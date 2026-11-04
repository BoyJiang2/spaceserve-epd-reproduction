# 四图配对诊断：EPD与完整模型输出不一致

本页是正确性排错结果，**不是性能对照**。两个请求实际JSON逐字节相同，SHA256 `b149f9ac6a430ae55ab54b718fb960edce529188966c04126f1601fd9bb9a8ee`。

运行源码均为官方9b基线上的输入适配 `23694dbc522b68cf404728333967867be6430c44`：三个API入口各一行按图片路径顺序加载。MiniCPM-V-2_6、FP16、TP=1、greedy、ignore_eos、128生成事件。四张COCO328/400/623/1146的路径、内容SHA各异，basename唯一；prompt中四个同序图片占位要求按序简述。该prompt仅用于独立诊断，不替换正式协议。

## 实际观测

| 项目 | EPD e4a | 完整模型 d4a |
|---|---|---|
| 资源/入口 | 三卡E1:P1:D1 / epdserve | 单卡D1完整模型 / baselines/d/distserve |
| HTTP / curl / 生成事件 | 200 / 0 / 128 | 200 / 0 / 128 |
| prompt / processed prompt tokens | 47 / 307 | 47 / 307 |
| 输出 | 反复描述黑衬衫、绿领带、眼镜男子，称各图一致 | 先描述军装人物坐长椅，再描述船与狗，128处截断 |
| 原work / cleanup / outer | 0 / 1 / 1 | 0 / 0 / 0 |
| 最终释放 | 同身份恢复stop0、已登记live空、三卡显存0 | 自动收尾0、已登记live空、单卡显存0 |

本地已有原图经逐SHA核同后人工查看：第一图是三名军装人物坐长椅，第二图为船上露头的狗，第三图为女子抱大熊，第四图为绿领带男子。EPD文本未满足逐图描述要求；完整模型只证明输出前两段与前两图对应，**没有证明完整四图语义正确**，后两图未在128事件内描述。307是整体处理后prompt长度，不等同于已独立测出的视觉token数。

两者输出正文不同，不能归因于请求文件不同。当前仍不能由这些文本定位具体embedding/KV错误，也不能判定全部视觉特征是否被消费。单卡完整模型在此只作正确性参考，不拿来宣称与三卡EPD相比的吞吐或延迟优劣。

## 原失败及边界

e4a原清理报已登记worker2082803的environ不可读，原cleanup/outer为1。原清理后GPU显存读数各4MiB；不能将该读数当已释放证明。之后使用同一身份助手恢复stop退出0，三卡显存归零，原失败未改写。D4原自动清理0。均保留旧sd-pam不可读记录，未终止该进程。

完整原件保存在服务器 `epd/runs/e4a`、`epd/runs/d4a`；可浏览[EPD逐请求输出与失败/恢复](../validation/official-entry-20261104/e4a-small-evidence.json)、[完整模型逐请求输出及请求配对](../validation/official-entry-20261104/d4a-small-evidence.json)、[G3/G4范围审查](../validation/official-entry-20261104/four-image-pair-g3-g4.md)。两个run不拼接成正式批次。

## E生产端同步反事实：未改善

在单独诊断commit `d63cc3e8f15920c2e83653a5dca5b68bfa75346f`，仅在E写入视觉缓存后、返回前增加CUDA完成同步，P不改。e4b与e4a、d4a的请求实际字节相同；HTTP200、128事件、work/cleanup/outer均0、三卡释放，但输出与e4a逐字相同，仍不等于D4。[e4b原始输出/终态与SHA索引](../validation/official-entry-20261104/e4b-small-evidence.json)。此结果只说明仅加E同步未解决该固定案例；不外推所有同步问题无关。该诊断行已撤回。

## 配置传递与分片别名：CPU已复现

上述官方在线版本虽然传入 `--intra-request-dp 0`，调用链没有将其传到请求；请求工厂默认True，AsyncLLM同时丢弃generate的kwargs。CPU用真实方法/请求工厂复现CLI0最终请求仍True。已启用的分片方法使用浅拷贝，共享嵌套图片容器；四图A/B/C/D的四个分片最终都变成D。原源码及CPU结果保留，不能继续把历史CLI0写成有效关闭。这个纠正只适用于所列官方在线代码，不外推其他历史fork批次。

新适配 `06fbcb6f3f3b931950077077c9a040e9c238deee` 贯通在线CLI0，并记录真实创建后的request flag；直接构造者原默认True及显式覆盖保持。True分片缺陷未修，本阶段关闭。原E同步撤回，三API图片修复保留。[最小补丁](../patches/20261104-online-irp-wiring.patch)、[CPU复现和回归](../validation/official-entry-20261104/online-irp-cpu.json)、[独立G2](../validation/official-entry-20261104/online-irp-g2.md)。

**新版本仍只有CPU验证，e4c尚未运行。** 下一次必须核真实request.enable_irp=False、与既有参考请求字节相同及完整输出/释放；不能把参数修正或源码缺陷复现替代GPU正确性、embedding/KV数值、并发或正式性能。
