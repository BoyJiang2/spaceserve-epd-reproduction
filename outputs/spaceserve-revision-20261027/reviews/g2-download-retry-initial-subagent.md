# G2 传输重试初审（拒绝保留）

/root/profile_instrument_review：REQUEST_CHANGES / BLOCKING1。

仅拒新旧holding相等仍允许新目录在旧holding内，违反旧目录不改；先resolve会丢失路径链接信息。须拒双向包含、对原路径从WORKSPACE/work逐层检查links，再解析创建，并补创建前拒绝反例。其余exactSHA复用/残缺保留/四路互斥/原merge逻辑正确。审查者未运行代码/联网/改文件。

主执行者落实：os.path.abspath保留原路径，local检查后双向is_relative_to拒包含。三个新case+七原守卫10CPU PASS；复审待。
