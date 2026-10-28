# 后台礼物原客户端验收

2026-10-27；隔离QA数据库analysis/android/flow-runs/content-expansion-high-level-20261026/test.sqlite3，账号1。正式数据库未改；不把明确QA礼物当自然养成。

接口设计和完整契约见[后台接口](../api/ADMIN_OPERATIONS.md)。原游戏协议get_presents/open_present不变，SQLite schema仍2。

## 实际闭环

共同证据：analysis/android/flow-runs/admin-presents-20261027。

- 更新API protocol-input-admin-v1前正常关闭候选v61并核对设备原APK恢复SHA；全六账号、配置、战斗运行与结算回执精确不变。
- 输入候选v62 PID3261登录原账号，flow20261027-092555；完整登录差分仅自然AP26→28，图鉴/关卡位无变化。
- POST账号1，request_id=QA-admin-inbox-20261027-1，message=QA运营发信验收1金币，kind1/amount1/level0。首发201，生成serial3；再次同内容200/replayed。完整状态只有这份原礼物、单调序号与持久发送回执变化，币仍2022520。first-ack/replay-ack/before/sent保留。
- 原其他菜单→礼物确认→原领取对话框→领取。inbox.png/confirm.png、claim-flow.json与claim-logcat.txt留证，实际原open_present请求一次且serial_number_list=[3]，金币2022520→2022521；完整六账号差分仅该礼物移除、原领取回执与1币。claim-proof.json/claim-requests.json/claimed.json保留。部分中文字体缺字仅显示字形子集，线包message仍完整。
- 正常关闭v62，设备原APK恢复SHA核验；API完整重启为protocol-input-admin-v2，同编号重试仍200，原首次date/serial内容保持，不重新入箱，全六账号/配置/历史精确不变。restart-replay/restart-final留证。

- v63 PID4033/flow20261027-093114再次完整登录，AP28→28且全六账号/配置/历史精确保持。重试仍不复活；实际source0x5002从SELECT_AREA进入ETC_MENU，BGM/SE/GUIDE偏好均true。restart-input/restart-settings/restart-menu及original-hashes留证，原APK/DLL/正式库/基线候选保持原SHA。

上述证据没有借助直接写余额、伪造领取结果或修改客户端礼物逻辑。满仓单位发信和领取容量边界由原服务及后端测试承担，本次实机只发1金币。

## 自动验证

新增7项测试先RED（缺少路由/Delivery），再GREEN：真实HTTP/原领取/新API重试、内容冲突/账号作用域、严格类型/未知字段/账号无写、原单位等级经验、两API实例并发单次发送、真实保存后异常回滚、隐私GET/过期过滤/HTTP错误。

整增量初次全回归：服务端179项179.462s，Android111项23.895s，资源3项0.895s，C#原属性5/伤害4/弱点6共15项，全部通过。整增量审查裁定另见docs/reviews/2026-10-27-protocol-input-review.md。
