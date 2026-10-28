# RTD 本地账号模拟服务

2026-10-28：中文卡池与活动后台已提供，访问运行新版服务的 `/admin/`。当前后台入口 http://127.0.0.1:18767/admin/，共用现有游戏 API 的数据库，支持卡池/活动启停、时间、权重、活动掉落。详见 [使用与验收](../docs/protocol/ADMIN_WEB_ACCEPTANCE.md)。

自行启动：先在根目录运行 `. ./enter-env.ps1`，再执行 `& $env:RTD_PYTHON server/rtd_server.py --port 18767 --database <目标数据库路径>`。明确指定数据库；省略时会使用 server/data/rtd.sqlite3，可能不是当前游戏实例的库。

**2026-10-26 当前入口：[本地可玩版交付说明](../docs/LOCAL_PLAYABLE_RELEASE.md)。** 已支持两教程、普通 11000、普通养成、礼物/登录、本地抽卡、好友、改名、单层恢复/续关；106 服务端测试通过。支付排除、抽卡不扩展严格安全校验。下方“普通关/抽卡/好友未实现”等段落是历史记录，请以当前交付说明和 TASKS 为准。备份/恢复使用根目录 backup-rtd.ps1，明确选择数据库，不覆盖原档。

2026-10-25最新实现：10001支持有界clear_quest2、书与依代、累计经验升级和首次水晶；原子回执及新订单放弃旧教程的本地政策已有15项临时库测试。全新账号客户端已真实完成10001并返回主界面，取得rank2/经验100/金币80500及首次水晶1；结果页的奖励确认/好友邀请映射已补充。六个战斗槽与五个存档编队槽不同。普通关仍未开放，不能把第二教程通关视为全部M2完成。见`docs/rules/LOCAL_POLICIES.md`、`docs/protocol/SECOND_TUTORIAL_SETTLEMENT_FINDINGS.md`；下文带日期的记录保留历史范围。

2026-10-24 开发计划实施：已拆分为`rtd`包，原`rtd_server.py`和PowerShell命令保持兼容。传输在transport/http.py，表单/GZIP封装在protocol/wire.py，业务在services，主表白名单加载在masters/catalog.py，本地赠送策略在policies/tutorial.py，存储在storage/store.py。当前新增schema1运行实例/回执与请求级BEGIN IMMEDIATE事务，具体重试边界见`docs/protocol/TRANSACTIONS.md`；普通关卡仍未支持。

新增验证：`server/test_transactions.py`（5项），`server/capture_contracts.py`（复放原5项并生成49份脱敏HTTP样本），`server/freeze_baseline.py`（只读生产备份与临时恢复）。回归矩阵见`docs/protocol/REGRESSION_MATRIX.md`。API可用`--run-id <客户端回放编号>`关联日志；日志新增request_id、耗时、匿名账号及货币/单位前后摘要，并递归去除凭据。关联信息不进入严格DTO。

2026-10-24 下午：增加首教程 clear_quest / clear_quest2 结算、get_friends / get_presents 新账号空列表、收藏与关卡 NEW 标志保存、首次 buy_gacha。结算奖励/完成位/单位/活动关卡清除/重试回执同一 SQLite 事务保存；实测账号3首教程结算经验50、金币30000、依代经验675。重试及服务重启测试验证不会重复发奖。

**明确的本地重建规则**：首教程完成后仅赠送一次5个免费水晶以满足客户端的强制首抽，首抽固定发放另一位原版初始角色（starter+1循环，等级1）。原服赠送时机和首抽奖池未恢复；此实现不代表历史经济规则。扣5水晶、单位、tutorial_flags bit0和重试回执一起保存。普通抽卡、普通关卡结算和随机掉落仍明确报未实现。

主数据首次写盘还会触发旧 AndroidUtil 原生 JNI 退出，现 SaveFileDataBinary 与读取一样改用 APK 自带 Java 类，保持 UTF-8 内容和私有 files 路径。21张表已实际下载保存通过。

Python 标准库 HTTP + SQLite。仅监听电脑 `127.0.0.1:18766`，模拟器通过 `adb reverse` 访问；资源仍由 `analysis/serve_offline_bundles.py` 的 18765 端口提供。

2026-10-25：新增只读本地NPC助手及第二教程10001有界入场，结算仍仅支持10000。使用10001前，在项目根目录执行 `python analysis/recover_battle_masters.py`，从原始资源按固定source/payload SHA恢复type22/70；依赖项目已有UnityPy，原始资源和生成主表不纳入Git。当前23张表的恢复选择、普通关资源缺口及动态验收边界见 `docs/protocol/BATTLE_RESOURCE_FINDINGS.md`。不得把10001入场成功视为第二教程已可通关。

## 启动

在项目根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\start-rtd-session.ps1
```

该入口检查/启动既有 AEHD 模拟器、本地 API、资源服务、scrcpy 和实验客户端，然后执行有状态的输入流程。默认在新账号完成注册并进入同伴介绍，或已有账号完成认证回到标题可操作状态后停止输入。服务和客户端保持运行；游戏进程退出后，兼容启动器恢复已安装 APK 原件并校验哈希。原始 APK 和热更新备份不修改。

首次起名/选人参数：`-PlayerName RTDLocal -Starter 3`。四组选项索引为 0–3；当前输入脚本只支持 ASCII 名称。已保存账号不会重新注册，也不会因参数变化改名或换初始队伍。手动控制与脚本控制不要同时进行。

单独运行 API：`powershell -ExecutionPolicy Bypass -File .\start-rtd-server.ps1`。

重新构建实验 APK：`powershell -ExecutionPolicy Bypass -File .\build-rtd-local-client.ps1`。构建依赖当前机器已有的 .NET SDK、Mono.Cecil、Python 和原始解包文件。输出 `analysis/android/rtd-local-api.apk` 是 root 模拟器临时替换用的实验包，签名不是可普通安装的正式发行签名。

## 已实现的协议

| 操作 | 行为 |
| --- | --- |
| create_user | 保存 UUID、名字、角色选择，建立三个角色实例及有效队伍；同 UUID/相同注册参数重试不重置进度 |
| auth_user | UUID 查找原账号，签发随机会话，返回玩家状态 |
| login | 验证 RTDSESSID，返回登录数据；同一 UTC 日内重复请求不重复计登录天数 |
| get_units | 返回保存的角色和队伍 |
| form_units | 校验所属角色、槽位、重复角色及活动队伍，事务保存 |
| save_local_flags | 保存客户端图鉴标记字节数组 |
| get_master | 按请求类型和 hash 提供已恢复的 21 张主数据表，剔除历史账号/会话字段；覆盖启动所需全部 20 种类型 |
| get_quest_info | 返回该账号持久化的进行中关卡，无关卡时返回空列表 |
| get_level_master | 按地图 ID/hash 提供 APK 原有 413 张地图，未知 ID 明确报错 |
| order_quest | 目前只支持教程 10000；恢复固定敌人和坐标，保存进入状态，重试/重启不重复扣体力 |

未知接口返回明确错误，不统一伪造成功。会话有效期为 30 天，会话与玩家绑定，拒绝 query user_id 与会话所属玩家不一致的请求。

POST 表单 `request=<JSON>`；响应体是标准 GZIP 压缩的 UTF-8 紧凑 JSON，第一字段为 `code`，成功码 4096。**不设置 Content-Encoding**：客户端会显式解压。注册与认证使用不同 DTO；客户端 LitJson 拒绝未知字段，因此每个响应须精确匹配其结构。

## 数据和备份

- 主数据库：`server/data/rtd.sqlite3`，SQLite WAL + 事务。玩家完整状态存为 JSON，会话另表。
- 脱敏请求记录：`server/data/requests.jsonl`；UUID 和会话值不记录。原客户端调试日志可能包含凭据，应仅在本机保存。
- 列出账号摘要：`& 'C:\Program Files\Python313\python.exe' server/manage.py list`。
- 在线一致性备份：`& 'C:\Program Files\Python313\python.exe' server/manage.py backup`，输出到 `server/backups/`，不会覆盖旧快照。备份含账号凭据。
- 验证测试：`& 'C:\Program Files\Python313\python.exe' server/test_accounts.py`；测试使用临时数据库，不改真实存档。

初始货币、容量、会话期限、UTC 登录日边界等是本地模拟策略；初始三个角色和等级来自客户端 `ClientData.firstPlayerUnit`。尚未恢复完整原服规则。客户端每次失败重试可能生成新 UUID，服务端不能凭重复昵称或相同模拟器型号合并账号；联调失败遗留的账号 1、2 保留，当前已被客户端保存并恢复使用的是账号 3。

## 界面输入流程

`analysis/RTDFlow.cs` 只观测 UI 状态，输出当前场景、步骤、对话框状态、真实 ClickOK 按钮坐标、输入框坐标及角色选择坐标。它不修改客户端成功码、教程状态或玩家数据。

`analysis/android/drive_startup.py` 注入真实 ADB 点击/键盘输入。它等待对话框 Stay 和状态稳定，执行后检查状态变化；同一动作最多尝试三次，未知/停滞状态保留截图后退出。进程锁阻止两个输入脚本同时运行。角色选择还检查确认按钮是否已启用，避免默认索引 0 被误认为已实际选择。

覆盖顺序：关闭原生公告 → 欢迎 → 名字输入 → 名字确认 → 资源等待 → 确认 Google Play 不可用提示 → 标题开始 → 新手欢迎 → 选人 → 确认角色 → 确认初始队伍 → 注册成功后的同伴介绍。旧原生公告采用固定 1080×1920 的已观察模板识别；Unity 按钮使用实时计算的坐标。新分辨率需重新适配原生公告模板。

每次回放输出到 `analysis/android/flow-runs/<时间>/`：逐步截图、steps.jsonl、result.json、完整 PID 日志。失败不等于卡死；以具体状态、网络操作或异常定位原因。

可选目标：

- `-Goal account-ready`：默认，注册完成或已有账号认证完成。
- `-Goal title-ready`：停在标题可操作状态。
- `-Goal registered`：仅验收新注册，不用于已有账号启动。
- `-Goal tutorial-request`：推进同伴确认，观察第一个教程请求；不表示教程已运行成功。
- `-Goal tutorial-ready`：同时覆盖新注册和已有账号恢复路径，停在战斗实景中的首次教程对话。
- `-Goal tutorial-controls`：确认已识别的首次移动教学对话，直到客户端报告操作已解锁且存在可点击面板。后续移动和战斗动作仍待逐步验证。
- `-Goal master-checked`：仅验证客户端收到本次新的主数据成功响应，不代表下载与结算都已完成。2005 恢复方式及返回标题的影响见 `analysis/android/INPUT_FLOW.md`。
- `-Goal login-checked`：诊断用途，在已有账号到达标题后，经一次性 `/sdcard/rtd-login-probe` 标记调用原有 `ComManager.Login()`，等待原客户端返回 OK。它没有跳过教程或伪造解析成功；完整正常流程中的登录时机仍待后续游戏流程验证。

## 2026-10-24 客户端实测

1. `flow-runs/20261024-114746`：从欢迎、起名到选人、队伍确认，全自动真实输入；注册后进入 Installer mode 6、userId 3，客户端执行过 SaveDataManager.Save。
2. `flow-runs/20261024-115057`：重启客户端后 auth_user 恢复 userId 3，登录探针调用原有 Login；PID 日志含 `LastPHP:ADRS_AUTH_USER`、`LastPHP:ADRS_LOGIN`、`RTD_LOGIN_PROBE completed OK`。
3. HTTP/SQLite 集成测试覆盖账号与会话重建、重复注册、同日重复登录、错误 UUID、跨玩家会话、失效会话、队伍与图鉴标记持久化、未知接口错误。
4. `flow-runs/20261024-120335`：最终构建经统一启动入口从进程启动、公告关闭、Google Play 提示确认到恢复账号 3 和登录 OK，全流程通过。实验 APK SHA-256 为 `f0ccce499ae741c43d2465998510f46d70edf46b33e4768d72efc5bf15fadd4e`。登录验收只接受本次新产生的成功记录，避免旧日志造成假通过。

首次注册响应到达后、解压结果输出前，客户端信号 11 退出。结合 `libGZipArchive.so` 中的旧 JNI 桥接，改为 Unity Java 桥接调用 APK 自带 `org.example.ScriptBridge.GZipArchive.Decompress` 后，实际注册/认证/登录响应均可解压解析；没有取得该次完整原生栈，确切故障指令仍未确认。Java 代码使用 GZIPInputStream；静态证据在 `analysis/smali/org/example/ScriptBridge/GZipArchive.smali` 和 `analysis/ghidra/gzip.txt`。补丁源码为 `analysis/TracePatcher/GzipBridge.cs`。

REA 已核对原始 Assembly-CSharp.dll 的账号类型元数据：SHA-256 `c83aea19ee65ae973815daf6a04e430d9e87b8426b6180c1fe507e4260763ecc`，MVID `81502538-516d-4802-bbff-d4f363e3388d`。详细行为结合既有 ILSpy 反编译与运行日志确认。

## 当前边界

账号、首教程战斗与结算、首次召唤、登录和主界面已打通；客户端和服务端同时重启后仍能进入主界面。教程使用原始地图和 100% 固定敌人表；随机掉落概率未恢复，当前不生成随机掉落单位。依代50000及请求的经验已持久化。其他关卡、普通抽卡仍拒绝执行，不宣称完整可玩。体力按原关卡表消耗，重复进入同一活动关卡不再次扣除；服务端自然恢复尚未实现。

地图来源见 `analysis/level-data/provenance.json`，提取入口 `analysis/extract_level_data.py`。这是 APK 内独立 TextAsset 文件，旧的 sharedassets-only 清单没有覆盖它们。备份中的死神资源经唯一容器名匹配，使用 `analysis/wrap_enemy_bundle.py ms00_death_01` 重建传输外层，保留原载荷，原子发布；这份资源 HTTP 下载已在客户端通过。

读取地图时传给 `MySharedPreferencesCall.getString` 的默认值为 null。旧 Unity JNI 路径在此退出，改为先 Contains 检查：不存在则直接返回原默认值，存在则使用非 null 的 Java 字符串参数。保留缺失键返回 null 的原语义。修复后已实际进入地图并显示教程，未取得退出时的精确原生故障指令。

另从独立 TextAsset 找回 32/33/16/17 四表，共 3402 行，来源在 `individual-textasset-provenance.json`。教程后的 2005 对应服务端 8197，已定位为缺失挑战表。现已实测完整主数据下载、保存、FRIEND/PRESENT 和标志同步通过。五项 HTTP/SQLite 集成测试通过，其中新增结算、首抽和响应丢失后重启重试幂等性验证。

缺少的类型不能用空成功响应掩盖。`save_tutorial_flags` 仅见到旧操作枚举，当前反编译流程未找到有效请求构造，未猜测实现。
