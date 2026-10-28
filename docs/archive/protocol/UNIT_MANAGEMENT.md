# 编队、收藏与图鉴

范围：五槽编队、收藏、永久图鉴与战斗入场容量。强化、出售和特殊进化分别开发，不以本批次通过代表已恢复。

原版PartyInfo含三主槽、两副槽；NPC助战不写进自有编队。保存允许1–5组，组内非零实例唯一且自有，leader非零、active有效；跨组可复用。cost应用条件未确认，原初始角色cost总和295而本地max_cost200，因此不凭猜测拒绝原始队伍。

`save_unit_favorite_flags`严格接受唯一自有实例及整数0/1，验证整个批次后保存。原ComManager.GetUnits和SaveDataManager.Load在tutorial_flags[0] bit5未设置时会重新载入旧本地收藏；SEND_FAVORITE负责上传旧列表。成功上传（含空列表）原子设置bit5；响应仍只有code/session_id，下次auth返回该标志。不得以修改客户端判断代替服务端迁移。

`login.unit_collection`按unit_id唯一，原UnitPanel以status100表示曾获得，保留最高历史等级。每次请求在同一SQLite事务内同步获得/移除前后图鉴；出售后仍保留。旧存档只从现存单位补齐，客户端unit_collection_flags不授予获得资格。

MMUnitOver只在单位数量大于容量时阻断。因此奖励可超容量，不吞已赢奖励；超容量的新战斗订单拒绝9472且不扣AP/放弃旧运行，同GUID快照重取保留。

只读RTDFlow扩展为编队及最多24个可见/离屏单位行、弹窗实例ID。Unity日志行实际约1014字符，观测按150字符分块，保持代理对完整；解码器验证上限、冲突和序号，新一帧不完整时禁止使用旧帧输入。游戏逻辑和响应不由observer修改。

测试：33项服务端回归通过；收藏迁移先观察到expected32/got0，再修复通过，写故障回滚及空列表包含在内。观测解码5项测试通过，覆盖Unicode、乱序、重复、冲突、截断及新帧失效。独立整体审查及过期观测重要缺陷的RED→GREEN修复已完成。

实机：隔离库unit-management-20261025；form_units于17:43:13成功，首组[1002,1001,1003,0,0]，客户端重启20261025-174610保持。初次收藏重启发现旧本地覆盖，补bit5迁移后真实0→1上传并双重启验证成功。脚本直接读取1001.favorite=1，没有再次切换；完整存档SHA b21df0a0b0c00751e7b3aee166132a5c697cd00bd298327262df7ec56d9ad64d不变，20单位、10图鉴。证据favorite-restart-verified.json保存在该隔离库目录；最终MCP截图已返回主界面。
