# closed1 模型终态 capture 单次执行 G2

APPROVE_WITH_NITS / BLOCKING 0。只批准准确适配capture源码85c31286af762d9e46312955a534b084bfb12a8258019b6da87c100bcb4d954f（7330B）在真实模型已终态后的一次CPU只读capture。原frozen helper e72f1c82b871c6b8ea3af79e75db3e97c7b2688d3095b812aa15473dc3d1fded（7292B）不修改。已逐文本核七处记录名各一次替换，规范化换行后其余源码完全一致；phase_identity/remaining_owned/phase_code/模型清单/GPU与MPS释放逻辑均未改。

真实terminal readback ac32163b6f425389a05d8318a1077d4bef33d286c29955d10d652c5e9ed5d798 的嵌入原件逐bytes/SHA自洽：closed1 start23b0cc6f953a29f6a3149a8daf27dcefb235eebd83ea978e63476f1f68bef7e7；动态model manifest707dee09621845e0cf460fcd90c7d619acda6896a57c30dd9d10ad5855b189cd；launcher251512/ctime1793404655.44、child251515/ctime1793404655.63及controller_id/start时间在terminal匹配，exit0；313 completion marker与当前model SHA相符。这里只审核这些收据接线，不以marker单独签完整313实际G3。

准确执行：原共享space venv -I -B，CPU50/nice10/空CVD，先加入frozen scripts/tools路径；sys.argv phase=model，--start-sha=23b0… --producer-sha=707d…；compile适配源码时__file__设原ROOT/tools/capture_phase.py，以便identity_helper源路径和真实原helper SHA正确。外壳60秒TERM/30秒kill-after，不推理、不发信号、不执行清理、不重跑模型；额外wrapper记录原helperSHA、适配SHA、实际argv，不能把capture_helper_sha256误称适配SHA。

原main必须现场再次拒绝live父/子、同run own/unconfirmed残留、AccessDenied、GPU2 UUID不符/显存非0/compute非空、MPS非stopped或token/pipe/UUID不符。四输出model-closed1-terminal.json、model-closed1-files.json、model-closed1-final-owner.json、model-closed1-booking-at-capture.json必须实际absent，原open-x/xb保留，旧失败与capture不覆写。任何原检查拒绝都保全并停止，不绕过、不自动重发。

外层SSH观察超时与原子phase exit0分开记录，绝不补写transport0。capture返回后还需独立核六服务正确性、设备/并发/encoder mask、诊断trace、313完整性及释放原件，才可模型实际G3。此G2不授未来G3或formal；本窗formal0/54且不再启动。审查者未运行测试、SSH、GPU、capture或修改源码。
