# 模型预检配置名称与实际部署映射

本批保留首次失败与唯一成功 attempt1 的全部配置，**不覆盖历史通用名称文件**。仓库中的通用名称不代表最后一次执行版本。

| 本地证据 | 内容与用途 |
|---|---|
| `model-code-manifest.json` | attempt0，53成员，SHA `e3feffa72ca74e9aa49bb0ba16c8bf291a1626effaab2f269ef740f1d41a92c4`；启动前失败，生成0请求 |
| `../evidence/G2_MODEL_CODE_APPROVED.json` | 上述 attempt0 的历史批准，禁止用于恢复 attempt1 |
| `model-code-manifest-attempt1.json` | 实际成功模型预检57成员，SHA `6782b5a1578c9d890f03bcc2368a36c3ab69663d7479f7b55b5af0c6f03141a5` |
| `../evidence/G2_MODEL_ATTEMPT1_CODE_APPROVED.json` | 实际 attempt1 的 G2 原件 |
| `../evidence/G3_MODEL_FORMAL_CONSUMER.json` | 347项绑定包含 attempt1 命名原件，供离线分析核验；不包含正式数据G4批准 |

远端成功执行时，`model_guard.py` 读取的通用名称已部署为 attempt1 字节；本地离线分析明确读取 `model-code-manifest-attempt1.json`，没有把 attempt0 当成实际57成员版本。本地原件命名与远端运行路径存在这一差别，复核时请核 SHA，而不是仅凭文件名判断版本。

新窗口复跑须按新的实际资源身份重新审查和生成部署配置，不能复制这些历史批准充当新许可。若恢复旧执行布局，仅在新的专属副本将 attempt1 manifest/批准映射到守卫预期的通用名称；原证据目录保持不变。此外 `resource_guard.py` 的前置 `_exclusive(None)` 读取 `configs/code-manifest.json`；本地保留的实际 numeric18 原件为 `configs/numeric-code-manifest-v2.json`，SHA `13a5539d1947c82c468372c193fc12b10eb8ac984513fbb3256e80e751c4795b`，仅在新的专属副本将其映射为 `configs/code-manifest.json`。现存 `evidence/G2_CODE_APPROVED.json` 已绑定同一 SHA，无需替换该历史原件。原部署57清单绑定的其他文件也须逐项核验。此说明仅解释配置出处，不授予新的GPU运行许可。
