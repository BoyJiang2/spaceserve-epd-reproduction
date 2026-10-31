# 发布版Space报告与313派生记录：精确G4

decision：APPROVE
passed：true
BLOCKING：0
reviewed_at_utc：2026-10-31T10:41:53Z
审查者：独立 Codex subagent /root/handoff_cpu_review

本G4新绑定当前报告5042B/SHAabd19c9a246e4354de85937d95027173f2189750873ba26a6a7b010c9dd79013、313请求JSONL3361694B/SHA77dd1cb26341768f078a769144ab985b604b2e840f88e32a6a47e24ab3a1c523、evidence JSON2565945B/SHA880800d9fb8270ba065e4e3c7fb181a70b1a5602c6a3c31968b264891642999f。不是复用只绑定旧report的G4，也不是13文件发布G5。仅本地读取/JSON原件/SHA核对，未运行prepare-model-publication.py、测试、扫描器、SSH、网络或发布，未改源；只保存本审查。

原件与派生闭包：
- closed-model-actual-readback中262原件逐base64解码、bytes/SHA全部实比，合计8861910B。按原文件顺序独立解析reference/correctness/profile requests三种原记录，313行对象与发布JSONL逐条全等，重新编码后完整bytes及SHA也全同；每行source_path/source_sha256确回到原完整文件SHA，不只是抽样或根COMPLETED计数。
- 7reference+6×15target+6×36diagnostic=313，90target、216诊断，和六fold/根COMPLETED一致。报告没有把313全叫正确性用例。六组15target HTTP200逐条成立，逐同轮native baseline按case直接比较response.output_token_ids及processed_prompt_token_ids，90项全同，非只相信record.checks布尔值。
- evidence JSON逐原件解析机制字段并加入实际canonical_capture_raw/version_identity_raw，与当前派生evidence对象完整相同。prepare脚本只做来源封装/文档路径与下载状态替换，没有将诊断记录平均成性能数据；metadata builder/敏感扫描代码本审只读不运行。

机制与终态：
- 冷/重启未mask实际encoder stream记录before/after/first-execution均78个SM；mask记录78→54→78→54，first encoder为54，原UUID/stream/PID绑定保存。报告只称有效encoder mask，未推出decoder互斥或54/78资源/吞吐份额。
- 四overlap原JSON数值准确为cold-space564317、restart-space567123.75、cold-mask1409288.25、restart-mask1410180.25微秒；报告对应排列正确，clock_alignment明确baseTimeNanoseconds/1000+ts。此G4核其派生/报告一致与实际G3边界，不声称重新分析全部10个压缩trace；原G3已记录其审计限度，不能将本轮数值复核说成新增全trace重算。
- canonical postcapture四文件bytes/SHA均核同；inventory真实272文件/389866812B，terminal released=true/实际controller与child exit0、same_live=false、owned空、GPU2 UUIDc005 0MiB/0%、compute空、MPS stopped。原模型阶段0与外层SSH观察Timeout/local exit1的区别保留；不能由外SSH超时改称模型失败或反向改写transport0。本G4没有新增现场全机PID/FD观察。
- 六服务原server.log确有313条min_pixels/max_pixels intended overrides dropped警告，报告真实保留，未声称参数强制生效。实际RGB448/20图SHA与四图视觉token1024、同轮processed IDs输入一致等措辞沿真实模型G3范围，没有泛化到任意视觉质量。

统计/报告边界：正式0/54，无吞吐/TTFT/TPOT/E2E正式收益、无拼接旧48、无互斥分区推论；runtime edcaa/CPU verifier a899/闭合工具bc460及manifest707dee身份分别列出，原helper e72f与实际adapter85c不混写。旧失败/过期输入/SSH观察错误保持，不因本次预检认为整体EPD/fairPD完成。

Release与旧审查关系：报告两处明确“尚未上传Release/Release尚在准备”，资产表仅本地核验，不假称下载链已通；预期tag链接只能视作准备中的目标地址。本审不核发布服务可用性、不授create/upload/publish。已有space-20261031-G4.md/json仍是旧报告的真实历史G4，不能改其原件后称已审当前5042B版本；本新增G4才是本版本绑定，后续G5应明确消费本审查而非冒用旧report SHA。

允许当前精确报告/派生数据作为待发布候选的真实预检表述，实际Git/Release动作仍须独立G5。新CPU/GPU/性能实验无许可。

GATE_RESULT: {"gate":"G4-current-publication-report-and-derived-data","decision":"APPROVE","passed":true,"blocking":0,"reviewed_at_utc":"2026-10-31T10:41:53Z","reviewer":"/root/handoff_cpu_review","scope":"exact_5042B_preflight_report_and_313_request_provenance_only","report":{"path":"spaceserve/comparison/20261031-preflight.md","bytes":5042,"sha256":"abd19c9a246e4354de85937d95027173f2189750873ba26a6a7b010c9dd79013"},"requests":{"path":"spaceserve/data/space-20261031-requests.jsonl","bytes":3361694,"sha256":"77dd1cb26341768f078a769144ab985b604b2e840f88e32a6a47e24ab3a1c523"},"evidence":{"path":"spaceserve/data/space-20261031-evidence.json","bytes":2565945,"sha256":"880800d9fb8270ba065e4e3c7fb181a70b1a5602c6a3c31968b264891642999f"},"request_count":313,"reference":7,"target_correctness":90,"diagnostic":216,"original_files_SHA_verified":262,"original_bytes":8861910,"capture_inventory_count":272,"capture_inventory_bytes":389866812,"warning_count":313,"formal_completed":0,"formal_planned":54,"Release_uploaded_claim_approved":false,"publication_G5_granted":false,"new_GPU_or_remote_execution_approved":false}

未运行测试、扫描、派生脚本或远端/发布操作；当前结论仅报告和数据G4，不是Release下载验收。

