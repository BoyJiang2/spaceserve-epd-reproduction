# 传输wrapper初审问题

独立G2审查者 /root/profile_instrument_review 和G5审查者 /root/profile_runner_review 均发现：全局将http.client.HTTPSConnection替成函数，与实际Python3.13原构造器super(HTTPSConnection,self)冲突，会TypeError。G2 BLOCKING1，尚不批准该版本。未停止原上传或执行wrapper；原直连继续，源/asset不改。

主执行者最小修复：release_assets中专用UPLOAD_CONNECTION入口默认原类，仅注入该入口；不改http.client全局。新增真实构造器（不联网）及实际无认证HEAD验证，避免原mock遗漏，提交G2复审。
