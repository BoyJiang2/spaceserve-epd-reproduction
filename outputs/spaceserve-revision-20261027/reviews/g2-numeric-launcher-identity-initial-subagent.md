# Launcher身份复验G2初审

独立/root/profile_instrument_review：REQUEST_CHANGES，BLOCKING1。正常路径确认身份失败后，except仍无条件child.terminate，绕过保护。要求所有TERM使用同身份函数，未知不信号，补CPU回归。

已统一terminate_owned，正常/异常均复验UID/PID/ctime；不确认仅留cleanup_identity_unconfirmed，不terminate/wait。实际目标Linux六CPU测试通过，含ctime改变+异常清理不信号，真实INT/TERM、MPS半启动与TERM/ALARM。等待复审；未运行被拒版本。
