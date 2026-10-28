# 普通强化合成

`compose_unit`请求：`dst_unit_instance_id`、`src_unit_instance_id`；目标正整数、素材1–6个唯一正整数且不含目标。响应`result`严格只有整数`add_exp`和`type`。原ComManager读取这两个字段；原MMUnitUnion在成功后本地扣币、删素材、播放加经验和升级，服务端须同步持久化相同结果。

费用为目标强化前等级×原主表cost×素材数。普通素材经验按原UnitData.UnionPoint：int(Single(Single(mix)×Single(pow(level,0.5))))；50000依代使用自身total_exp。真实master14100、mix1400、level51单精度结果9998，直接double会得9997。累计等级阈值沿用原六类指数与Single截断；阈值相等即升级，累计经验封顶到GetLevelExp(lv_max-1)，等级不降低。add_exp为本次原始经验，实际存档增加量受满级封顶限制，与原动画一致。

本地重建政策：固定普通成功type0、倍率1。原服大成功/超成功概率无证据，暂不随机。material_type非零或携带bonus/attribute_exp的特殊素材明确8197，避免无声丢失额外价值。目标可收藏或在编队中，素材不可收藏、不可占任意组前三主槽；两副槽素材可消耗并清全部组引用。目标满级、金币不足、非法混批均拒绝且不改档。

金币、消耗、目标等级/经验、永久图鉴最高等级、实例ID高水位与回执同一SQLite事务。回执以目标ID及排序素材ID集合SHA256保存在玩家JSON、无TTL；相同请求重排/并发/重启只执行一次，旧回执不覆盖目标后来进度。已被其他操作消耗的素材不产生新成功。后续不同素材正常强化不会被误去重。

原始初始角色可能为level5/exp0（原UnitData.SetLevelData同样将exp置0）。本增量保持既有档位，不通过降级或未经授权的补经验迁移改变它；实机首先选level1目标排除该混淆。

REA原DLL SHA c83aea19ee65ae973815daf6a04e430d9e87b8426b6180c1fe507e4260763ecc，parent ev_2411f063e565c7dbb32cb71fb284219f6cb84868978c5500529b058d313cf3c3。六个选择类型全部匹配；有一处#US terminal flag异常，不声称全部字符串完整。代码/原消费分支和实机结果共同约束本实现。

验证：44项服务端回归、14项Android工具测试通过，独立整体审查无发现。普通公式、阈值相等/封顶、主槽与收藏保护/目标允许、非法混批、资金不足、特殊材料拒绝、故障回滚、并发、重排、重启及后续正常强化均有覆盖。

实机隔离库unit-compose-20261025：目标1005（unit20000，level1），素材1006（unit10020，level1）；预览95金币、500经验，18:49:02 compose_unit4096；原版动画结束后level4/exp500、84605金币/17单位，客户端与服务端一致。第一次客户端/API双重启完整存档不变。第二次flow20261025-185553自动MCP使用1008依代105经验、费用380，结果level4/exp605、84225金币/16单位、10图鉴/2强化回执；再次双重启全档SHA86d566b50f4f9c3bfe1b9263ae687cabe6eb31ac7616ff287ceb44062b6fe2be不变，restart-verified.json为证据。
