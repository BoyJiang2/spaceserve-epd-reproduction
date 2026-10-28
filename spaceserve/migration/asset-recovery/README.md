# SpaceServe 精确小资产恢复准备

原下载清单已从既有封存输出恢复：download_manifest.json原字节10,162B，SHA256=1bb637d5a3ca359e9e1cd4656012ead4fa3257878fa4f95d56b2c1847dec39e5。此处保留逐字节副本，不重新序列化；旧不匹配副本及旧下载失败证据继续保留，不追溯改写。

八件本地素材均精确匹配现行protected pins，共2,710,088B：两个实验库、原下载清单、五个已验模型小文件。旧1.632GB.partial未验证、不上传、不当作完整权重。目标为qjh003固定spaceserve/assets，仅排他写缺失文件；不是完整环境或Qwen权重恢复。

工具25f4756eeb8b9f547503c98ff719e8974036de5e8bf812892a84653d26d83a7f、测试1156810bbba8215065b0a788ae9c512a3e0453928be6102e829d471cd5b222ea、依赖9cf保持。一次4项CPU-MOCK全PASS/0skip，0.010秒（父0.199秒），源前后不变、temp空。仅验证成员/pin/排他写入/链接祖先拒绝；不是目标Linux运行、完整资产、CPU_STAGED或GPU G3。

[G1范围](g1-space-small-assets.md) · [G2](g2-space-small-assets.md) · [素材清单](space-small-assets-candidate.json) · [原始4测试结果](space-small-tests.json) · [完整stderr](space-small-tests.stderr.log) · [传输wrapper](space-small-wrapper.py)

实际上传仍须G5/Git-first/三端工具字节核、fresh CPU预约及现场准入，8MiB payload、60秒工作＋120秒收口、300秒证明、至少4GiB可用空间、固定boot/UID/CPU50nice10、全部目标/evidence不存在。失败原件保留，不自动重试。wrapper先核两个模块原始SHA，然后把八件二进制base64原样交业务工具；source wire与业务payload分别记SHA。不能从目标尚未上传推定成功。

Space专用环境尚未重建，剩余权重另审；不使用EPD环境代替。模型/精度/请求/54矩阵不变，GPU0，旧源和旧raw/七ZIP/Release不动。
