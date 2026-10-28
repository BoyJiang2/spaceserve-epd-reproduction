# Space 独立环境与框架的固定CPU构建

模型原字节已通过独立审查；本阶段专用于尚缺的Space环境和框架，绝不用EPD环境替代。系统Python3.10.12/glibc2.35、原工具uv0.13.5的ELF37,597,160B及SHA8a70已实际只读取证，version/install/compile帮助保存。venv帮助仍需bootstrap实际验证，未知参数将安全失败，不会删安全选项继续。

[G1](g1-space-environment-build.md)/[G2](g2-space-environment-build.md)冻结五个独立action：bootstrap排他复制原uv并建独立venv；lock原12cc的154exact版本、wheel-only/no-deps/hashcompile；install消费该实际锁、require-hashes且wheel-only；framework只固定官方66de/6ff及已审UUID/cache/queue食谱，静态metadata避免加载Torch，新8链接按原relative pin；verify静态154版本、pip check、原2582全部bytes/link/target_member全等。任何差异停，不改pin、不重编原2so、不make或启动GPU。所有action成功仍仅ASSETS_MATERIALIZED，不CPU_STAGED、actual CPU suite或GPU机制通过。

每action fresh真实CPU003/bootUID2147/CPU50nice10，240秒工作＋120秒收口、API300、实际END-120，盘≥120GiB，claim/log/终态排他，前一真实成功及logSHA才接下一，失败保留partial并阻断后续。uv子进程使用受审9cf的pidfd/session受控收口；新resolver UV_HTTP_RETRIES=2只在该有界action内，下载4/安装1/构建1，显式官方index和新Space cache/tmp，清除外部index/配置/凭据环境。原两catalog保留为90/154的部分来源资料，不继续第三批。

首次4CPU-MOCK实际3PASS/1FAIL为Windows字符串前缀fixture问题，原件保留；[恢复G2](g2-space-environment-test-recovery.md)后仅fixture改Path.is_relative_to，生产512f不改。一次纠正4PASS/0skip0.002秒（父0.311秒），source前后相同temp空，不证明实际安装。实际执行仍待G5/push/三端源码与wrapper/fresh准入。

[纠正原始测试](environment-build-tests-corrected.json) · [首失败](environment-build-tests.stderr.log) · [真实软件只读资料](software-inventory.json) · [具体wrapper](environment-build-wrapper.py)
