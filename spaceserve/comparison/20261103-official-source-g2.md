# SpaceServe：原生vLLM来源与加载路径核查（2026-11-03）

本页只记录来源和静态检查，不是模型/并发/SM实效通过。权威checkout仍为官方66de079af4234b27f7f82ff91d238ef1351324ba、adapt/qjh003-v1、clean，未修改源码。

## 原生v0.7.2的源码内容关系已核定

| 对象 | commit | Git tree |
|---|---|---|
| SpaceServe作者改动之前的基点 | d7ec548300d7950c1305231b2aaf970bab7569c1 | 9887287659a56df6f9744e631667f67893512b8c |
| 原生vLLM v0.7.2标签 | 0408efc6d0c17fba17b2be38d0d0f02e96d2bf9d | 9887287659a56df6f9744e631667f67893512b8c |

两棵tree完全相同，提供源码内容身份依据；不是凭已安装分发包的0.7.2标签推断，也不把两个不同commit声明为同一提交或同一Git祖先历史。Space作者基点到固定66de版本的比较为ahead23、behind0。

[原生提交对象](https://api.github.com/repos/vllm-project/vllm/git/commits/0408efc6d0c17fba17b2be38d0d0f02e96d2bf9d)、[内容基点对象](https://api.github.com/repos/vllm-project/vllm/git/commits/d7ec548300d7950c1305231b2aaf970bab7569c1)、[Space作者改动](https://api.github.com/repos/gofreelee/SpaceServe/compare/d7ec548300d7950c1305231b2aaf970bab7569c1...66de079af4234b27f7f82ff91d238ef1351324ba)。原始对象及文件SHA见[证据JSON](../data/official-g2-static-20261103.json)。

此前跨历史compare的404或diverged结果不用于推断源码不同；提交历史不同与源码树相同可以同时成立，不推测历史重写原因。

## 相关作者改动与编译产物

六个相关文件对照中，requirements-cuda、vllm/__init__、version及_custom_ops逐字节相同；Qwen2-VL与GPU worker有作者改动。作者delta没有csrc/cmake、CMakeLists、setup或requirements-cuda变化；这只说明这些源未变，不证明二进制ABI、动态加载或推理正确。

官方源码包目录未见_C扩展，现有环境site-packages中有217472040B的_C.abi3.so。未复制或加载它，也未执行setup.py。实际从新checkout加载源码和编译模块的路径需在合法窗口验证；目前只是加载风险，不冒充已经发生的ModuleNotFoundError。

原生v0.7.2可据源码内容作为对应基线，正式时仍须对齐V1/eager、模型/精度、预处理、请求序列和缓存；源码来源相同不保证旧批次配置可比。旧48/54独立保留，不追溯改写。

下一步针对第一处真实加载/运行错误做最小适配，不先审完整作者改动清单。单H20/Qwen2-VL-7B FP16 TP1预算不变；设备放置、实际重叠、encoder mask及其允许/观察SM集合均待实测。有限采样不强求覆盖全部允许SM，未验证decoder互斥时不称完整分区。
