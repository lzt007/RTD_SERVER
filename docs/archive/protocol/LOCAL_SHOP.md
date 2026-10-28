# 三项本地商店

支持原操作buy_recover_ap、buy_max_unit、buy_max_friend；原请求是字符串字典，扩容传当前max_unit/max_friend，响应是17字段ComPlayerDataBAP。get_shop_list仅恢复出地址，无构造/DTO/消费逻辑，保持8197，未杜撰官方列表；三个本地功能通过原硬编码菜单操作。失效平台支付等依赖留T25。

每次扣1水晶（原单位扩容实机确认框已复核），扩容+5；免费先于付费扣款、本地上限1000单位/100好友为明确重建政策，不代表官方历史上限/扣序。余额非负且total=free+paid；不足8961，满体力9216，超容量9217，非法请求8194，活跃战斗8197。体力补至max并重新设置自然恢复锚点，不累积满体力时间。扣费、收益、回执及请求前自然恢复同事务，异常全部回滚。

旧容量作为扩容幂等键：新消费需旧值等于当前值；已成功旧值重放只返回当前玩家，不回退后来容量/货币/AP。并发同旧值只扣一次。体力购买无nonce；retry0是新购买，retry>0需已有成功回执，返回当前玩家且不补体力/不扣费。不能区分任意伪造或跨次延迟重试，不声称消除原协议歧义。两种重试回执跨进程保存。

REA原DLL SHA c83aea19ee65ae973815daf6a04e430d9e87b8426b6180c1fe507e4260763ecc；4个原类型parent ev_4e5bfd054a4757b2f50efbb76a20441a40ebc5c210103c0822ac2fd2f802323d，metadata完整，#US两处terminal flag异常。该次错误嵌套全名未匹配；随后使用原嵌套元数据选择名ComPlayerDataBAP成功匹配，parent ev_ba6258579a988896b1faab4512cf26ab8588232ed71942262cab175f1bf1ec71，未把空选择当证据。

7项商店测试3.797s、全73项55.502s、19项工具0.838s通过；独立审查无发现，73项56.187s及7项3.730s通过，额外探针验证自然AP先恢复、购买锚点、当前重试DTO和AP写后异常回滚。

local-shop-20261025独立库首次未注资，MCP全自动原确认框购买单位扩容20→25，原已有水晶1→0，9单位/70825金币不变；flow20261025-211851及after-unit-expansion.sqlite3。零余额原提示已核对，未点付费购买按钮、未打开失效支付。

后续独立测试夹具只设置免费1/付费1/总2水晶和AP17，非真实充值，原检查点保留。21:25:24自动buy_recover_ap成功，AP17→22/22，免费1→0，付费1不变；after-ap-purchase.sqlite3。21:26:23自动buy_max_friend成功，好友容量12→17，付费1→0，其他收益不变；flow20261025-212559及after-all-purchases.sqlite3。

客户端/API双重启通过，完整存档不变，原客户端容量25/17、水晶0、AP22正确；after-shop-restart.sqlite3和restart-verified.json，状态SHA 52d139fc1108ec8a465a693853d12bb57b56aea6b356b6d662058bfed486436c。正式DB SHA521d5997...1ecd仍未改。
