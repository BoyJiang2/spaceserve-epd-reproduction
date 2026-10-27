# G2 Space离线RGB/数据集绑定增量
沿用AGENTS3.2.1只读审查，不网络/GPU/凭据/改文件。
新增本批dataset26文件，来源是已在本地的EPD dataset副本，但复制前逐一与Space实际configs/relocated-inputs.json的path/bytes/SHA全匹配26项后才独立copy。evidence/dataset-local-exact-copy.json记录；没有复制EPD性能数据或改旧source。辅助synthetic图片存在不等于Space G3覆盖颜色测试，实际G3仍COCO四主题/7cases。
analysis/analyze_formal.py小增量：verify_inputs从已被model57绑定的relocated manifest选dataset26项逐SHA核实际本地文件；新rgb_identity参考已被G3 consumer347原件绑定的cold-native rgb-before（records[0]20图RGB/size/hash），正式每cell前后cache manifest SHA/20图RGB与之完全相同，records仅1/API PID匹配本cell launch、url固定、inference_requests0。
新增test_RGB_boundary负例改像素/manifest/API ID，18CPU PASS。六旧实际model-preflight boundary本地schema复核也全部PASS，不等于formal数据G4；实际formal raw仍不抓回、不分析、不改远端源码/预算。
请核源RGB参照确在G3绑定、copy文件匹配实际Space pin、增量输入/缓存闭环有无降级。只新增这项CPU分析验证，输出APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES与blocking。
