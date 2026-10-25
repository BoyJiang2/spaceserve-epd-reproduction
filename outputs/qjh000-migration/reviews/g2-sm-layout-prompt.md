继续同一Claude只读审查。先前G3原生可行性APPROVE_WITH_NITS/BLOCKING0（session7c380db4-09f7-4607-8a3e-67849dfd43a5），现为G2逐位用户态SM布局校准代码，不是放宽布局标准，不跑7B，不批准第三组。禁止改文件、GPU/实验、读取凭据。

目录outputs/qjh000-migration。plan.md已显式继承旧7B G1布局标准。补抓evidence/mps-owner.json(state=stopped)与native-sm-launch.log(host lock finished)，source-evidence/__init__.py为官方smcontroller，core.py为兼容补丁前源（并非7B服务运行证据）。env CPU已READY、pip check154全部兼容、FP16探针PASS(evidence/runtime-probe.json)，无7B服务。

新增scripts/probe_sm_layout.cu，preflight_sm_layout.sh，service_sm_probe.cu（后者只复用SMID kernel作小so，无Torch扩展，不修改libsmctrl）。同一GPU0、固定lib源码git archive、原生同host锁/所有权cleanup/MPS/noMPS各3重复。逐bit0–11 mask→测实际SMID→零mask恢复，最后0xfff→测→零mask恢复；输出逐位及组合集合/数/恢复。检查marginal减少总和与组合减少、MPS虚拟SM编号不声称物理位置；可能槽位空洞仅推断，不能先假定。一律保存失败exit/stderr；不写SM_EFFECTIVE。code=sm90，无PTX，无内核/驱动修改；不需要用户新增性能实验设定许可，属于已授权机制验证。

请G2核对GPU调用/资源生命周期、maskABI、helper采样/错误、host锁/私有MPS清理、证据/版本/身份，指出BLOCKING。输出APPROVE/APPROVE_WITH_NITS/REQUEST_CHANGES、BLOCKING文件行号+理由、NON-BLOCKING、QUESTIONS。实际结果会另G3复审。
