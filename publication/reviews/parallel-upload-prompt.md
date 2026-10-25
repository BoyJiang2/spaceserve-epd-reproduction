窄核G2及G5原范围：七包仍同一集合/名称/SHA、同draft/commit/private，现当前串行worker5598在传236MB EPD，约170–210KB/s，无覆盖操作。拟并行提前上传尚未开始的最大947MB Space包，代码upload_large_asset.py 20行，仅从原七manifest按固定name+SHA选择唯一该包，进度/manifest写独立large-asset-worker目录；ROOT和STATE仍原source/同draft。调用已批准工厂+原run('upload')，无create/delete/publish能力调用。不停止当前串行、不删除任何资产。

串行worker之后若遇到大包仍starter，会依原“既有不同状态禁止覆盖”守卫退出，不接管或删；保留退出记录，待独立大包worker完整成功后，使用原七manifest串行upload再跑一遍，仅跳过已上传且size/digest一致的全部七资产，形成完整observed集合。最终原verify/publish始终用原七完整manifest，仍要完整实际下载SHA、当前asset身份集合匹配。若任一失败保持draft/pending，绝不声称全部成功。

此举只并行相互独立的网络传输，不改原件/统计/文档结论/批准流程/资产范围，不是新增GPU实验。请只读快速核当前新worker与上述边界，G2/G5分别给APP/REQ/BLOCKING，禁止凭据/远端/GPU/写文件。仍本次真实Claude weekly quota接替。
