# 新窗口G2：CPU stage与runtime最小迁移候选

按AGENTS额度接替只读审查，不GPU/网络/凭据/改文件，可本地CPU。主agent落盘结论。

用户新预约qjh000，已G1批准单H20/Qwen7B独立54=5400formal+1080warm，313预检上限，13–17北京，16:58截止。不拼旧48，不恢复EPD。10:22只读API显示CPU和GPU lane都是他人到13点，故不在13前远端复制/编译/测试；本地准备，13点fresh核自身GPU预约和实际资源后再按批准CPU stage。

候选outputs/spaceserve-window-20261027-1300/scripts：来自旧实际G4批次55原脚本，只对精确旧root→新root、Ray temp唯一名、stage SOURCE改旧完成Space root、TARGET新root，以及booking start/end13–17常量替换；configs/relocation-candidate-provenance.json记录每个旧字节SHA/初迁移SHA，未变文件维持相同，runtime-candidate-source-manifest.json为后续语义增量后的当前56脚本精确清单。旧文件和任何旧marker/results不复制/不改。

语义delta仅：booking_window.py增加固定新booking ID拒旧ID，同end−120s/5min freshness/owner/UUID不放宽。formal_guard.py新增独立CPU启动预算记录（186min估计+900s保守尾部余量=201min；不足就保全预检而不正式），仅原模型G3后/正式code guard前写新xb JSON无性能结论，仍每cell900s+16:58守卫。此预算策略已另请求G1窄review，不把其当已批准，G1/G2未齐不执行。test_window_booking.py三个CPU case全PASS：旧ID/lane/owner/window、prestart/cleanup/expired/stale、预算等于阈值/不足留证/拒覆盖。

CPU stage.py核心原行为不改，只SOURCE=旧实际Space root、TARGET新root。五旧CPU tests本地3PASS/2 Windows symlink skip，13点目标Linux必须五项全PASS、真实POSIX TERM/ALARM及runtime相关CPU不skip，再GPU。stage guard作用是纯复制，不授予GPU。源root已G4/封存不可改；CPU阶段后新relocated-inputs.json必须SHA匹配原相对inventory504760aae3c903cb090b766c7937640c2afdd8ea693a516da8c1a9733ff3357c，才可生成新numeric18/model/formal独立G2部署与实际新G3，规则expected-staged-version.json。源变化停留证，不能签新version当same model；actual stage回执/G2部署/G3都尚未生成。

请重点核clone边界/源不变/路径隔离/新booking窗口与budget是否绕门槛，未改benchmark/model/采样/公平性，未自动跑任何GPU。stage路径纯复制G2与其余runtime候选可分别给范围；仍需实际部署精确SHA/CPU及新G3，不声称源码approve代替部署。
