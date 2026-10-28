# T05 分离存档与验收矩阵

自动测试入口 `server/test_accounts.py`：每个case用TemporaryDirectory创建独立DB和日志，ThreadingHTTPServer端口0，不能接收生产数据库参数；API重启仍使用同一个临时DB。`server/capture_contracts.py`复用该隔离。基线演练脚本只读生产，SQLite backup至独立快照，恢复到临时副本。实验客户端尚未绑定独立测试账号，后续破坏性客户端验收必须隔离设备存档/数据库，不能拿账号3试卖或合成。

| 路径 | HTTP/SQLite | 客户端 |
|---|---|---|
| 新注册/同UUID重试/冲突注册 | test_account_lifecycle中的实际断言；5测试输出可追溯 | 历史114746，当前未重跑 |
| 老账号认证/会话失效/越权 | test_accounts.py账号生命周期及过期会话测试 | 历史172111恢复账号3 |
| 编队/图鉴/标志存储 | 现5测试覆盖所属检查及重启 | 单位标签切换通过；真实编队变更尚未验收 |
| 首教程进入/地图hash/重启 | test_tutorial_order_restart_is_idempotent | 历史171719首教程完整通关 |
| 结算丢响应/服务重启重试 | test_settlement_survives_response_loss_and_restart | 历史171719真实clear_quest2；没有客户端丢包验收 |
| 首抽丢响应/重试 | 同结算case，持久回执 | 历史171719首次召唤 |
| 主界面/API双重启 | HTTP成功不能作为通过依据 | 历史172111 SELECT_AREA，数量不变 |
| 未知接口/坏奖励/无活动结算 | HTTP拒绝，状态检查 | 失败UI未逐项触发，保留未测 |

T10将新增重构后客户端回归；历史证据不用于冒充新实现已通过。5个test方法是多个场景的组合，详细测试名以samples/test-output.txt为准。

## 2026-10-25迁移后T10实测（取代上述“当前未重跑”状态）

10项服务端测试在新机通过，输出analysis/migration-server-tests-20261025.log。新AVD绑定独立测试DB与账号1，不使用正式账号3；客户端首教程、clear_quest2、首次召唤和主界面证据为analysis/android/flow-runs/20261025-002304，客户端/API双重启为20261025-003205。前后状态快照在migration-t10-20261024-234823/before-restart.json与after-restart.json；金币30000、经验50、5单位、货币/完成标志/回执一致，battle为空。没有客户端丢响应故障注入、普通编队变更或普通关卡验收。

新注册的原生昵称框由代理通过MCP核对后确认；新加焦点等待后的空白设备全自动注册尚需复验。3项MCP传输测试和1项资源HTTP完整性测试另行通过，不替代游戏功能验收。

## 2026-10-25战斗入口增量

服务端共13项HTTP/SQLite测试通过，新增helpers精确DTO/认证/越权/只读/API重启、22/70原始表版本、10001先决/版本/助手/floor拒绝及同token/API重启快照测试。真实客户端MCP已通过助手列表、第二教程队伍确认与10001首条对话；实际请求地图hash4081725474、14表hash、订单成功，AP19→18，15条敌人记录。证据目录flow-runs/battle-entry-20261025，当前停在对话；无10001结算、客户端重启恢复、退出或普通关动态验收。HTTP重启复用不能冒充客户端恢复已通过。
