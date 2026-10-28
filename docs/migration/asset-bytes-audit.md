**ASSET_BYTES_AUDIT：APPROVE，BLOCKING 0。**

审查者：`/root/space2300_review`
reviewed_at_utc：`2026-10-28T14:49:39.522078+00:00`

独立重算通过：

| 单元 | 成员/组件 | 复制字节 |
|---|---:|---:|
| data | 27＋27＋1，三个组件 | 4,112,010 |
| env | 45,958 | 6,866,027,252 |
| model | 24 | 16,210,140,997 |
| 合计 | | **23,080,280,259** |

- 五组完整source-before/source-after/target清单逐项相等，包含类型、权限、bytes/SHA和链接文本。env仅有四个批准链接，精确匹配。
- 下载24份原件共31,285,351字节，逐文件大小/SHA全部符合capture索引。
- 三单元实际exit0，terminal均为`ASSET_BYTES_COPIED_RELOCATION_PENDING`、failure=null，claim身份与terminal一致。
- payload/command/stdout的SHA绑定一致；模块解码SHA符合受审8ff/9cf，tool commit为351e927，runtime仍a3f。每次准入记录目标/evidence不存在。
- 各单元结束时证明年龄约6.2、42.2、63.8秒，均小于300秒；host/UID/boot与固定范围一致。CPU50/nice10由实际argv及受审executor硬检查约束。
- PAM/SSH例外快照SHA重算一致并保存在claim/terminal；六条Git检查终态全部exit0、无failure或清理未确认。capture终态可读项目cwd进程为空。
- 两次写前失败保留，本次成功没有追溯覆盖旧失败。

capture索引SHA256：

```text
bf97a380b17ec98a85fdd7067adcd929eca485b01121425b612871eb6a47d59a
```

**这里只确认原始资产字节复制完整性。** 环境shebang/.pth、IPC RUNPATH尚未重定位或验证独立运行；不覆盖目标suite、Linux/GPU机制、模型正确性或性能。cwd筛查及服务身份例外不能证明完整FD/maps引用为空，不授权删除旧源。Space专用环境/Qwen完整资产等未完成项继续单列。

此次仅只读本地原件和重算SHA，没有测试、SSH、网络、写入或GPU操作。

GATE_RESULT: {"gate": "ASSET_BYTES_AUDIT", "decision": "APPROVE", "blocking": 0, "copied_bytes": 23080280259, "state": "RELOCATION_PENDING"}
