# 结束后只读释放复核：实际命令

2026-10-28 约 15:07:55（北京）在本地执行，复核脚本为同目录 [release-check-script.py](release-check-script.py) 的字节（从本地经 SSH 标准输入传给 qjh000 的 `python3 -I -S -`），参数是实际回执中父进程与清理记录里的 9 个 `pid:start_ticks` 身份：

```bash
ssh -o BatchMode=yes -o ConnectTimeout=20 qjh000 "python3 -I -S - 3256104:7767392 3256122:7767399 3256321:7767756 3256291:7767728 3256187:7767694 3256184:7767671 3256180:7767648 3256172:7767614 3256171:7767614" < release-check-script.py > release-check.json
```

[release-check.json](release-check.json) 就是该命令的原始 stdout（未经改写）。脚本只读 `/proc/<pid>/stat`、自有进程的 cwd 链接，以及本 root 的 `git rev-parse`/`git status`；不向任何进程发信号，也不查询 GPU。输出中的 `signals_sent: 0` 与 `gpu_queried: false` 是脚本按其代码路径写出的固定字段，依据是脚本本身，而不是对系统状态的另行测量。
