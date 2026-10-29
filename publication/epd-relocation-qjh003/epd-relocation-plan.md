# EPD固定资产最小重定位（续约09:00–10:00）

用户已续约，实际本人CPU票bk-20261029T0057-e2efd603，GPU票bk-20261029T0058-f4c7c157，2026-10-29 09:00–10:00。本阶段仅用CPU50/nice10，native系统Python -I -S -B；不初始化/查询GPU、不导入Torch、不加载.so、不跑模型/native36、不访问其他主机/不改旧源。

成功标准：固定/local/boyjiang/epd新资产内预期flat IPC具有新依赖RUNPATH；需要的console/activate路径不再引用旧实验根；原nested库/旧源不变，所有变更有before/after字节SHA及原件备份；独立静态复核通过。不能把本步骤称运行/IPC/GPU通过；Space formal仍0/54，1小时不满足201分钟，不重跑313。

1. 先只读核本窗fresh本人CPU票/host2147/boot65f/CPU50nice10；收集EPD startup .pth、sitecustomize、console shebang与activate旧根引用及owner/link/bytes/SHA、pyvenv/pythonlink、nestedIPC readelf、固定依赖路径。只读本新资产范围，不读HOME/凭据；只保存批准非认证票字段。此前静态原件不足以覆盖startup，不能猜测。限60秒工作+30清理，09:58前。
2. 根据真实清单冻结最小allowlist与精确SHA。只修所需flat IPC路径/新RUNPATH及旧console/activate路径；不重装env、不改包版本/模型/调度/缓存，不顺手改metadata或未用文本。原nested359096B/SHA12e414保持，flat为受控新副本，patchelf只作用于副本；依赖定位用readelf不ldd。对env文本只改真实旧root到新root的必要行，保存完整原件和before/after。现有完整资产原manifest作为旧原始字节证据保留，新建重定位差异清单，不覆盖旧raw或封存。代码先本地最小编写/异常输入CPU测试、独立G2/G5、commit/push核远端byte；目标仅执行指定source，排他claim、freshAPI/boot/root/无本项目进程、路径owner/link检查。只在实际准入后一次apply，最多120秒+30清理；任失败保留partial不自动重试。
3. 静态独立重读全allowlist/flat/readelf/启动引用与原件SHA，限60+30，输出新资产状态并独立实际结果审查。必要未来Torch加载/通信/模型须单独范围批准和真实GPU预算，不混进CPU验证。源码维护在单一tools/relocate_epd_assets_cpu.py，不按窗口复制工程。09:58硬收口；不因CPU迁移成功签发GPU Gate。

Space证据已data2f3cf04/Release427341677，匿名API→CDN下载SHA过但browser路径当前超时分别记录；EPD新状态页保留前次API前验缺失偏差。此次执行不会复用旧票/旧通过marker，旧Space root及所有失败/ZIP/既有资产不改。若startup发现未知行为/路径依赖，不猜测绕过，保留具体阻塞并先修设计。
