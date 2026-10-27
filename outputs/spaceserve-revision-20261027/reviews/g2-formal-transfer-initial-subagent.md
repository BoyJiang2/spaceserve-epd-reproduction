# G2 Space精确传输初审
独立/root/profile_instrument_review，REQUEST_CHANGES，BLOCKING2。
1. merge需重做prepare中的真实捕获身份/producer/released/helperSHA/owner/booking校验，不能只信自洽plan/raw/receipts；补错误controller/未释放但同步metadata SHA仍拒且零copy反例。
2. started/receipts/plan控制文件直接read绕过链接检查；须所有控制输入/输出走同一路径边界，补目录/回执链接负例。
原全量下载SHA/全目标冲突预查/xb无覆盖/失败原件保留认可；只读未执行或联网。

主agent已将只读validated_capture集中并让prepare/merge都先调用；控制文件读取/输出均local()拒symlink/junction，包括initialstart/4receipt/plan/batch/merge receipt。7CPU PASS，新self-consistent错误controller与未释放仍零copy，目录/receipt/plan的两种OS link predicate均模拟拒；不把mock说真实POSIX/NTFS链接验证。尚未真实使用工具。
