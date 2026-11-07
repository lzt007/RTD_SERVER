# 历史活动积分解锁排查、修复与回放（2026-11-07）

本次调查已拆分为两份完整文档，避免将原因、证据和操作步骤混在一起：

1. [完整分析结果](history-event-unlock-analysis-20261107.md)：原始关卡条件、客户端协议链、部署缺口、假设排除、实际生成对照、ADB 证据、结算持久化与重登解锁、验证边界。
2. [修复方法与回放手册](history-event-unlock-fix-20261107.md)：四文件最小修复、字段优先级、测试、部署备份和回滚、实际监听器健康检查、缓存刷新、观察包构建及 ADB 完整回放。
3. [脱敏验收摘要](evidence/history-event-unlock-20261107.json)：可公开、可机器读取的关键结果；原始敏感日志和二进制仍保存在 ignored 本地目录。

## 结论

仓库已有的积分补全尚未完整部署，生产给目标暗杂兵下发 `sp_event_point=0`。原客户端按服务端响应正常计分；此处不依赖敌人预制体的计数标记。最小修复部署后，100001 活动中仅 41028 每只 1 分，其他敌人为 0，显式运营和原始积分（包括 0）优先。

实机正常通关 20710 取得 7 分，`clear_quest2` 返回 4096，服务端保存余额 7 并完成 run。完全重启应用并重新登录后取得同一余额，20711 解锁，20712 保持锁定。30 项相关回归通过；166 个其他已有关卡的生成结果对照一致，247 个缺失或不支持配置跳过。

5 分门槛已完成实机链路，50 分边界通过 49/50 隔离协议测试，本次未实机刷满 50 分。旧战斗冻结快照不重算，验证修复应重新开局，不回填历史积分。

## 交付入口

- [ADB 导航与重登回放](../../scripts/android_event_unlock_replay.py)
- [ADB 选路、战斗与原生治疗回放](../../scripts/android_event_unlock_play.py)
- [多点 MotionEvent 注入源码](../../scripts/android/RTDInput.java)
- [真实关卡积分端到端回归](../../tests/test_history_event_points_e2e.py)
- [客户端只读观察包源码与构建说明](https://github.com/lzt007/RTD_CLIENT/tree/fix/history-event-unlock-verification/diagnostics/event-points)
- [此前已开放活动积分审计](event-point-open-audit-20261106.md)

模拟器已恢复原安装包并关闭，账号和正常获得的积分保留。发布内容为文档、脱敏摘要、测试与诊断源码，不包含真实部署地址、凭据、账号、截图、资源包、APK、签名材料或数据库。
