# 复跑入口与验证状态

本页区分“代码可核查的步骤”和“已经在新环境复跑成功”。目前没有第三方/新主机从零复跑的成功声明。不要把解除旧主机保护条件当成已验证的可移植实现。

## 可直接执行的CPU路径

在已授权clone的仓库根目录、安装Matplotlib 3.9.2的Python中：

```bash
python scripts/revision/compare_existing_space.py
```

输出为新的`docs/revision/space-relative.{json,png,svg}`，重算历史逐请求中位数与三次吞吐，并校验封存统计；不连接GPU，不改原始outputs。完整历史分析还需原始主机身份/清单条件，[原命令](README.md)不能简单移除校验后宣称等价。

## GPU复跑：代码入口已核查，新主机路径待验证

| 项目 | 前提与入口 | 当前状态 |
|---|---|---|
| SpaceServe最小单点 | 支持所需CUDA/驱动和显存的NVIDIA GPU；新专属目录；固定fork/模型版本；对应环境、dataset/RGB manifest及实际GPU UUID | H20/7B仅在归档主机验证，不能保证任意单卡，24GB设备优先考虑旧2B协议 |
| SpaceServe SM/并发路径 | 对应libsmctrl二进制、设备/stream探针、私有MPS身份核验及锁；入口[preflight](outputs/qjh000-migration/scripts/preflight_model.sh)和[start_server](outputs/qjh000-migration/scripts/start_server.sh) | 原入口绑定专属路径/UUID；需在新副本适配并重新预检，不默认禁用MPS或清除marker |
| EPD最小1:1:1 | 同机三可用GPU，CUDA IPC/P2P一致性、NUMA/拓扑、固定MiniCPM与cuBLAS环境；同三卡三副本作为性能基线 | 不能单卡运行三阶段公平复现；原[启动器](outputs/epd-profile-a/scripts/start_server.sh)和[通信探针](outputs/epd-profile-a/scripts/probe_epd_embedding_ipc.py)需按新主机确认 |

新主机操作顺序：盘点空闲GPU和存储→专属环境/模型固定及累计补丁→通信与实际放置→单图/多图/并发、cold/restart正确性→正式测量。每个步骤保存新证据，旧通过记录不能替代。对EPD的8图新协议还需同时调整并验证服务器图数上限、上下文、图片序列和实际视觉tokens，不能只改客户端参数。

本轮文档修正不会生成一个声称已验证的通用GPU启动器。可移植GPU实现和新测量属于后续独立批次，须经过代码与机制验证；该项尚未完成。
