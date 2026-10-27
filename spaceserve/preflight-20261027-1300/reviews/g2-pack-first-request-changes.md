# G2 pack first review — original independent response

Reviewer /root/profile_instrument_review.

G2：**REQUEST_CHANGES，BLOCKING 1**。UTC：**2026-10-27T11:01:33Z**。

**B1：凭据筛查不足以支持“零匹配”验收。**
work/spaceserve-preflight-publication-20261027/pack.py:14–16,52–55,96：

- 相较既有已审 scanner，遗漏 ASIA、DSA/ENCRYPTED private key及 password/api_key/access_token赋值；URL正则的 \\s写在 raw string 中，也没有按预期排除空白。
- 相对路径/文件名未扫描，匹配时异常还会直接回显路径。
- .gz/.so/.jpg/.png仅凭后缀即可跳过筛查，包括不在496项冻结集合中的新增文件，却统一输出 credential_pattern_matches=0。

最小修复：复用既有强规则并扫描相对路径，报错不回显疑似值；二进制跳过须限于精确路径＋SHA清单。保持本轮不解压 trace，但将未扫描压缩内容明确标为未验证，不能据此声称整个包凭据筛查通过；发布前仍须有相应安全证据。

其余静态流程成立：G3固定SHA与496项绑定、输入链接拒绝、ZIP_STORED流复制、成员SHA及读取时CRC核验、失败保留 partial、.gz/.so不进入Git副本、两资产清单生成。未执行脚本，也未读取大trace。

当前暂不批准执行该封包器；修复后仅重审相关增量，不涉及新实验或发布许可。

Primary disposition: accepted; original script archived unchanged; revised scanner and separate bounded G1 approved. Revised G2 pending, not executed.

