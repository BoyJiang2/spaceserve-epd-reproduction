# 正式控制器G2初审

独立/root/profile_instrument_review：REQUEST_CHANGES，BLOCKING2。未批准执行。

1. 单元审计未绑定精确计划行/model/dataset/endpoint，processed IDs仅非空、visual仅相信字段；要求与G3 COCO reference IDs逐项匹配并实际重算，增加错计划/IDs/endpoint反例。
2. monitor故障/foreign仅事后检查，仍提交请求；要求formal专用monitor打印后失败、控制器并行监看并受控停止本client与service，保原件不重试，补故障回归。

两项均已修并重新独立审查，未执行被拒formal版本。
