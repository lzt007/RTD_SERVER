# Schema 1与事务验收

## 2026-10-25：10001最新边界（优先于历史范围）

第二教程相同奖励正常重刷及API重启重试已纳入真实HTTP测试，无须篡改零经验。新GUID/retry=0订单经全部校验后，允许把同关活动运行原子标记abandoned并新扣1AP；校验失败旧运行不变。旧GUID不会复活，不退旧AP、不发旧奖励。clear_quest2快照、完成位、首次奖励、升级、单位、活动清除及回执仍同一事务。请求的party_instance_id是六个战斗槽，而非存档的五槽。

独立审查补充了协议歧义的另一方向：新运行首个结算包未到服，retry=1到达时可能恰与旧运行奖励指纹相同。返回旧4096会让客户端误认新战斗成功、丢失结果。当前10001对此明确8197、不改档，不静默返回旧成功；退出后可按新GUID重新开始，旧运行不奖励、不退款。无活动战斗仍可重取成功回执；新运行retry=0仍可正常同奖励结算。原有延迟旧retry=0与新结算无法区分的限制依然存在。不能声称任意断连/乱序均可恢复。

实现：`server/rtd/storage/store.py`。每次API调用持有一个BEGIN IMMEDIATE事务；嵌套仓储connect复用当前线程连接，不另行commit。校验、会话读取、扣费、JSON存档、quest_runs、operation_receipts同一事务；异常整体回滚。线程锁只是同实例辅助，SQLite锁防止两个独立Store重复结算。

schema0保留原players.state JSON、players和sessions。schema1新增quest_runs（服务器UUID运行实例、状态、原始快照、进入响应、时间）、每玩家一个活动运行的唯一索引，以及以(run_id,operation)唯一的operation_receipts。PRAGMA user_version=1在迁移事务最后写入；未来版本明确拒绝。不修改账号3字段。旧活动battle在下一次真实结算时懒导入运行表；旧JSON clear_receipt兼容回读，旧指纹保留兜底。

每次正常order retry=0且无活动battle创建新run；活动同关卡重复进入不重复扣AP。结算指纹规范化字典键序并忽略ver/retry/retry_count。同run完成后重复结算回原结果；新run活动期间retry>0且匹配旧回执，返回旧结果而不结算新run。完成后order retry>0返回上次进入响应，不另建战斗。retry=0正常结算新run，允许连续同关卡重刷。

**协议限制**：客户端没有运行ID或通用幂等键。旧请求在新run活动期间若retry仍为0且内容完全相同，不能与新结算区分；目前依赖客户端原重试计数。不能宣称任意延迟/并发/手工重发均可准确识别。只有首教程进入实现，重复运行测试用隔离数据库零经验奖励；这不是普通关卡或历史奖励规则验收。继续、退出、阶层等尚未接入。

新增 `server/test_transactions.py` 5测试：三次正常重复结算、延迟retry、新run不受旧retry影响、重启回执；回执写入后故障整体回滚；两个独立API实例并发只结算一次；旧活动快照非法请求回滚懒迁移；schema0备份和schema1升级回读一致。原5项HTTP测试与49份脱敏样本继续通过。

生产迁移前快照 `server/backups/rtd-20261024-183919.sqlite3`。回退必须停API后隔离当前DB/WAL/SHM并恢复该快照，不能运行中复制覆盖；备份含凭据。临时副本恢复已通过，正式回退未执行。
