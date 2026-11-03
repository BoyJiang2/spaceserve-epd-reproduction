# EPD 三入口多图修复候选独立审查

审查者：独立 subagent `/root/official_first_goal_review`。Claude 此前为403账户验证失败，不是额度耗尽，不标为Claude审查。

范围：官方 API 源码、三行候选补丁、CPU handler-prefix fixture和baseline调用链草案；纯只读。未授权服务器部署、GPU或正式配置。

## 原始审查请求

请独立只读审查 test_official_image_routing_20261103.py、official-three-handlers-image-routing-20261103.patch、official-three-handlers-image-routing-cpu-20261103.json。来源为官方检查记录中的source_files和21份调用链源码。判断三行修改是否修复首图复制、CPU测试是否仅支持声称范围、是否可作为待部署补丁。核D完整模型候选和PD context首步传KV源码事实。只允许文件读取和散列，不运行命令、测试、网络、SSH或修改文件。补充审查 official-epd-baseline-design-20261103.md；分配仍是候选。

## 原始审查输出

G2 APPROVE / BLOCKING 0，可作为待部署候选补丁。

三处修改均对应固定官方源码，原/补丁SHA一致；逐路径加载修复首图复制，统一三组入口的多图映射。CPU测试仅支持handler前缀中的路径顺序、单图保持及两请求合成映射，不证明真实图片、缓存并发、HTTP或GPU，也不单独证明整体实验公平。

源码支持D为完整VLM候选：初始请求携带多模态输入、`is_prompt=True`，经正常ModelRunner首步后逐token解码。PD context首步产生输出，再将未结束请求及KV block信息交给decode迁移；不能写成已经验证CUDA IPC传输。

设计草案边界准确：P1D2/P2D1及三独立DP1服务仍为候选，尚未冻结或部署。批准不授权服务器、GPU或正式配置执行。审查来源为独立subagent，Claude此前是403验证失败。

## 之后的证据提取简化

测试输入已抽取为同目录 official-three-handlers-source-20261103.json，只含三份相同官方源文件、长度、SHA256及base64，执行前逐项校验；不再依赖完整环境inventory。实际重测exit0；没有服务器写入。已通知原审查者核查这一变更，后续复核独立保存，不反向扩大上述原审查范围。

## 简化后的独立复核原文

G2 APPROVE / BLOCKING 0，原结论保持。

当前脚本SHA256：f6cd6b903b22caa4a48e9768543d03146caa1c251a7b271f1cef5afad44ec5fa。

精简包三份源码与原审字节一致，长度/SHA核验正确；仅替换证据读取入口，不改变补丁或fixture范围。仍不证明HTTP、图像解码或GPU，不授权部署执行。
