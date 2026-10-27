# CPU复制G2初审

独立/root/profile_instrument_review：REQUEST_CHANGES，BLOCKING 1。普通symlink仅位于整root且非strict解析，可能指向未复制/排除目录，复制后悬空却标verified。要求strict解析、目标必须在实际复制集合、排除缓存，复制后复查及合法/悬空反例。

主执行者已修并请求复审；未执行被拒版本。顺序schedule-v2单独APPROVE/BLOCKING0。
