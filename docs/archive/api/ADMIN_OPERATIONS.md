# 本地卡池、活动与礼物后台接口

适用版本：2026-10-27，SQLite schema2。启动原有 `start-rtd-server.ps1` 后，基础地址为 `http://127.0.0.1:18766/admin/v1`。接口为 UTF-8 JSON，不使用游戏协议的 gzip/form、玩家 Cookie 或支付系统。服务只监听本机回环地址，无后台登录系统；需要在本机调用。已提供中文 Web 管理页面 `/admin/`，直接使用同源接口；当前独立后台实例为 http://127.0.0.1:18767/admin/，与 18766 共用当前数据库。操作说明见 [Web 后台验收与使用](../protocol/ADMIN_WEB_ACCEPTANCE.md)。

## 当前默认内容

| ID | 卡池 | 消耗 | 数量 | 默认单位（全部等级1、等权） |
|---|---|---|---|---|
|10000|普通单抽|100友情点|1|10000、10021、10030、10033、11100、11102、11112、11133|
|20000|稀有单抽|5水晶|1|20000、20010、20020、20030|
|30000|普通十连|1000友情点|10|与普通单抽相同的8个初始单位|

这是本地可配置池，不是已恢复的官方历史卡池概率。三个池独立配置，十连没有额外保底；消耗和抽数固定。教程首次召唤有独立固定规则，不受运营关闭或配池影响。默认三个池均开放、无时间限制。

默认活动列表为空。当前实际可玩关卡为教程10000、10001及普通11000、11001、11002、下述新增12关，以及多层入口20000和已验收子层20100/20103/20110/20120/20122/20131；这些普通和多层关卡可绑定活动。已恢复的主表共有1021个关卡记录，历史活动条目可在目录按 `division=20000` 查询，未验收者不能在正式模式开放。目录中的 `playable` 表示已验收范围，`event_configurable` 表示已实现配置协议；其他201xx仅可在实验模式研究。实际入场仍需满足教程解锁、体力及已批准视觉替代设置。未提供历史活动标题与开放时间的虚构默认值。

新增12条普通关已完成原客户端实际胜利、唯一结算回执与完整重启验收：11010/11011/11012、11020/11021/11022、11030/11031/11032、11040/11041/11042。它们保留原地图、掉落、解锁与首通，正式模式`playable=true`，可配置并开放活动；默认活动列表仍为空。其他未验收内容继续受实验门控，以实时目录为准。

单位名称：普通池为ラビ、アーニャ、カロル、シグムント、ヨハン、ミハエル、アルフォンス、ワルプルギス；稀有池为アレン、カイン、ルカ、マリア。11000名为「旅立ちの平原」。原活动目录示例：11999–12002「蠢動の呼声」、12009–12012「業火の呼声」、12019–12022「深海の呼声」、12029–12032「蒼炎の呼声」、12039–12042「陰陽の呼声」，均为入門/初級/中級/上級四档；这些记录目前不代表活动已开放。

## 路由和响应

| 方法 | 相对路径 | 作用 |
|---|---|---|
|GET|`/config`|读取完整持久化配置及生效状态|
|PUT|`/config`|原子替换全部卡池及活动|
|GET|`/gachas`、`/gachas/{id}`|卡池列表或单池|
|PUT|`/gachas/{id}`|完整替换固定池，可省略与URL一致的id|
|PATCH|`/gachas/{id}`|修改部分字段；entries整体替换|
|GET|`/events`、`/events/{id}`|活动列表或单活动|
|PUT|`/events/{id}`|创建或完整替换活动，可省略id|
|PATCH|`/events/{id}`|修改部分字段；quests整体替换|
|DELETE|`/events/{id}`|删除活动并解除关卡绑定|
|GET|`/catalog`|单位、关卡、可配置掉落表目录|

卡池/活动接口成功状态为200；礼物首发为201，重试为200。`GET /config` 和所有写操作返回 `{ "data": {"revision":1,"gachas":[],"events":[]}, "availability":{"gachas":[],"events":[]} }`。列表/单项GET返回原始记录于data、顶层revision、对应列表/单项availability。availability只读，卡池包括id、effective_open、currency、cost、draw_count；活动包括id、effective_open。此状态仅反映运营开关和时间，不代表某账号可以入场。

`GET /catalog` 返回 `data.units`（unit_id/name/max_level/icon_url）、`data.quests`（quest_id/name/division/category/playable/event_configurable/reason/event_openable/next_quest_ids/sp_event_id/event_point_configurable）以及 `data.event_quest_drops`。新增字段分别表示当前模式允许开放、必需子层、原活动积分身份和积分可配置状态。网页删除活动使用携带 expected_revision 的 PUT /config，避免无条件 DELETE 覆盖并发修改。后者按关卡ID字符串索引，包含支持配置的普通关与多层关，列出原始drop_data_id、entries及空掉落权重，可作为修改模板。单位目录有751条，名称取原主表。icon_url为同源原版头像PNG地址，无图记录为null；头像按原g_id映射，支持GET/HEAD。

失败格式：`{"error":{"code":"invalid_configuration","message":"说明"}}`。400非法UTF-8/JSON或长度，404不存在，405方法不支持，409版本冲突，413超过1MiB，415非application/json，422字段验证失败，500内部异常。失败不保存部分配置。JSON布尔必须是true/false，不能用字符串或数字；不支持未知字段。

PUT/PATCH可带顶层 `expected_revision` 正整数；与当前版本不符返回409，可GET后重试。不传时按最后成功写入生效。每次成功写入revision增加1。DELETE没有请求体，不作版本条件判断。全量PUT只提交 `gachas`、`events` 和可选expected_revision，不提交只读revision/availability；先读取、再删除revision即可保存模板。数组没有逐项PATCH语义。

## 字段

卡池完整记录：

```json
{"id":10000,"name":"普通单抽","enabled":true,"starts_at":null,"ends_at":null,
 "entries":[{"unit_id":10021,"level":2,"weight":7}]}
```

id固定10000/20000/30000，不可新增或删除。name为1至80字符非空白名称（后台说明用，未修改原客户端静态文字）。entries为1至256项，unit_id必须在目录且池内不重复，level为1至该单位max_level，weight为1至1000000整数。每次独立抽取概率是weight除以池总权重，允许重复抽中。

活动完整记录：

```json
{"id":"local-11000","name":"本地活动","enabled":true,
 "starts_at":"2026-10-26T00:00:00+08:00","ends_at":"2026-11-02T00:00:00+08:00",
 "quests":[{"quest_id":11000,"drops":[
   {"drop_data_id":30140,"no_drop_weight":3,
    "entries":[{"unit_id":10021,"level_min":2,"level_max":3,"weight":7}]}
 ]}]}
```

活动id符合 `[a-z0-9][a-z0-9-]{0,63}`，最多100个活动。quests非空，同关卡不能同时归属多个活动，即使其中一个关闭。教程不允许绑定。目录中`event_configurable=true`表示支持保存配置，`playable=true`才表示已通过客户端验收；11000、11001、11002、新增12关及20000/20100/20103/20110/20120/20122/20131已通过验收，其他201xx子关可保存禁用配置，尚未验收的关卡仅在`RTD_CONTENT_EXPERIMENTAL=1`时允许启用。以实时目录为准。

多层活动必须包含全部可达子关。type20 楼梯的目的关卡和 type21 移动地形的导航代码均不作为掉落表ID，也不接受掉落覆盖。若catalog的掉落行含`original_missing=true`，表示原始主表缺失，并非原版不掉落；启用前必须显式配置该行。目录给出的`entries=[]、no_drop_weight=1`可作为运营者明确选择的本地无掉落规则，提交时删除只读元数据`original_missing`。未配置的缺失行会拒绝开放，不能猜测原始权重。

配置多层入口20000后，客户端收到派生关卡表及哈希，本地开放时间取代原2013年过期日程，原前置关卡条件保留。删除该配置后恢复原日程。已入场的整个多层链保存当时的配置和版本，后续修改、关闭不改变链内抽样，也不会再次扣体力。

正式支持不等于自动开放原过期活动：需要显式配置入口及所需子层。目录标记`original_missing`的掉落必须由运营者明确配置，未恢复的原概率不能推定为零；联调使用的明确无掉落覆盖不是历史掉落复原。六出口真实原楼梯及两层唯一结算、实验/正式完整存档重启已验收；高等级/素材/AP准备均为隔离QA夹具，不代表自然养成平衡。

后台写入成功后，服务端立即按新配置校验新请求；原客户端已缓存的活动列表不会主动刷新。通过原菜单“其他→返回标题”并重新进入即可取得新关卡表，无须结束模拟器进程。区域按钮依次切换普通、活动、特殊区域，多层入口20000在活动区的「超古代遺跡の秘法」中。

drops可为空（保留原始掉落）；每个drop_data_id必须属于该关卡且不可重复。11000当前引用0、21000、21096、30140、30195，具体原始内容见catalog。省略的表保留原掉落。entries为最多256项，单位唯一，weight范围同卡池，level_min/max在单位有效等级内。no_drop_weight为0至1000000整数。entries为空时no_drop_weight必须大于0，用于明确不掉落。

每次掉落尝试，条目概率为weight除以（条目总权重+no_drop_weight），空掉落同理；抽中后等级在min/max闭区间内均匀取值。不改变敌人出现率、关卡基础奖励、经验、金币、魂或活动积分，也不取消原有五书上限。掉落加倍登录奖励保留原规则：首次空掉落可再尝试一次，最多一个掉落。配置drop0会影响原本引用该空表的出现敌人，需要有意设置。

每条drops规则新增**可选**`attribute_exp`，整数0–999999，布尔/负数/小数/字符串/超范围返回422且revision与原配置均不变。旧schema2配置省略时等价0，不需迁移或重写；catalog原掉落模板不包含此字段，需要时显式添加。例如：

```json
{"drop_data_id":30140,"entries":[],"no_drop_weight":1,"attribute_exp":25}
```

这表示出现且实际击败该掉落表对应的敌人时，原协议下发`add_attribute_exp=25`，是否掉卡不影响经验；未出现的敌人、楼梯和移动地形均为0。它是**本地运营者指定的经验数量**，不是恢复的原服数值或概率。原1808条掉落主表缺少属性经验数量，因此默认0，完整原数据不改。配置也不直接修改任何已拥有单位。

入场时冻结敌人原属性所对应的五属性奖励上界，以及己方三个实例的单位身份、原主属性、原上限；修改/关闭/删除活动不改变已入场链。原客户端提交的五属性累计分别受快照及每属性999999上限约束；三个入场实例获得累计总量，同主属性部分再加一次，受各自原`max_attribute_exp`限制，助手不加算。此为本地有界核验，不宣称逐击杀重放。正奖励时受奖实例缺失或身份改变拒绝结算；后改当前编队不能改变受奖对象。已有超上限历史进度保留但不再增加。活动积分仍不支持非零。

两层奖励、单位经验、货币和原清关回执共用同一事务；后层失败全部回滚，同请求重试不重复加算。旧战斗没有此快照时仍可提交零属性经验，非零受控拒绝。

2026-10-26隔离QA实测：后台HTTP活动`qa-attribute-11000`显式设置每敌5000属性经验、空掉落，原客户端11000真实胜利后报告none=5000/fire=30000，其余0；目标实例900301/16500由0达到原上限5000，两个零上限队员与助手不加算。同原请求重试4096且所有账号及回执不变；API及客户端重启后六账号、配置、41关卡记录及24回执一致。随后原菜单用素材900302/15532选择火分支，目标同实例变16501/Lv1/经验0/属性经验0，消耗素材及50000金币。起始等级50和素材等级99是明确QA夹具，无新增货币或AP；属性经验是此次实际战斗所得。此证据不代表原服经验数量已恢复，也不代表自然取得起始单位和材料。详见`docs/protocol/SPECIAL_EVOLUTION.md`。

两个类型共用enabled/starts_at/ends_at：时间为带时区ISO8601，保存为UTC；null表示无边界，开始包含、结束不包含，结束必须晚于开始。`enabled=false`始终关闭。每次请求实时判断，无需定时服务或重启。

## 生效与存档语义

SQLite中的配置是权威数据。首次启动从 `server/config/local-gacha-pools.json` 导入三个池和空活动；已有库不会被该文件覆盖。schema1自动升级为schema2。卡池、玩家余额、抽卡回执和新战斗下单共用请求级事务，避免配置更新与消费交错。多个服务实例读取同一数据库会看到最新配置。

卡池关闭后拒绝新抽取，不扣货币；已成功抽卡的网络重试返回原回执，不按新配置重抽。活动关闭/未开始/过期时，绑定关卡11000的新下单被拒绝、不扣体力；已扣体力的同GUID下单、恢复、续关和结算沿用旧快照及掉落。修改或删除配置不会回写旧战斗。

原客户端静态按钮、普通关分类和原版活动分类保留。绑定11000不会把它移动到原版活动页，关闭也不会隐藏静态按钮，点击会收到服务端不可用响应。**禁用活动会关闭绑定关卡的新入场；删除活动则恢复11000默认开放及原始掉落。** 这是现阶段活动管理语义。

在线备份工具同时支持schema1和schema2，schema2的runtime_config随存档备份。旧schema1备份可恢复到新路径，首次启动时自动导入默认配置。恢复请使用 `backup-rtd.ps1`/文档中的新目标路径流程，勿覆盖运行中的数据库。

## PowerShell示例

```powershell
$base='http://127.0.0.1:18766/admin/v1'
$config=Invoke-RestMethod "$base/config"
Invoke-RestMethod "$base/gachas"
(Invoke-RestMethod "$base/catalog").data.quests | Where-Object division -eq 20000

# 关闭普通单抽，带可选版本保护；开启改为$true
$body=@{enabled=$false; expected_revision=$config.data.revision} | ConvertTo-Json
Invoke-RestMethod "$base/gachas/10000" -Method Patch -ContentType 'application/json' -Body $body

# 独立配置普通十连内容，其他字段不变
$body=@{entries=@(@{unit_id=10021;level=2;weight=7},@{unit_id=10000;level=1;weight=3})} | ConvertTo-Json -Depth 10
Invoke-RestMethod "$base/gachas/30000" -Method Patch -ContentType 'application/json' -Body $body

# UTF-8 JSON文件保存上方完整活动样例；PowerShell5显式发送UTF-8字节
$body=[IO.File]::ReadAllText('C:\MYDATA\workspace\RTD_FAKE\event.json')
Invoke-RestMethod "$base/events/local-11000" -Method Put -ContentType 'application/json' -Body ([Text.Encoding]::UTF8.GetBytes($body))
Invoke-RestMethod "$base/events/local-11000" -Method Patch -ContentType 'application/json' -Body '{"enabled":false}'
Invoke-RestMethod "$base/events/local-11000" -Method Delete
```

curl使用 `curl.exe -X PATCH http://127.0.0.1:18766/admin/v1/gachas/10000 -H "Content-Type: application/json" --data-binary @pool-patch.json`；pool-patch.json为UTF-8文件，例如 `{"enabled":true}`。GET实时结果是当前状态依据，本文表格描述首次导入默认值。

## 本轮验证

全量121项服务端测试通过（85.625秒）。新增配置、游戏接入和HTTP测试分别先失败再实现；独立审查另跑118项并验证两个API实例的revision竞争以及抽卡事务与关闭操作串行化。审查发现的重启seed依赖、UTC溢出及后续回归发现的Windows未读请求体405连接重置已补回归并修复。

在演示存档的独立副本上，通过真实HTTP管理员接口及原游戏form/gzip协议验收：关闭无扣费、配置单位/等级生效、关闭后抽卡重试不重抽、活动掉落快照、同GUID复用、关闭后结算、schema2在线备份恢复及API重启配置保留。初次联调脚本的retry关键字重复和账号1编队硬编码为夹具问题，纠正后重跑通过，未为通过测试而放松游戏校验。原有账号完整状态逐字节不变，正式旧库/原APK/原DLL哈希不变。MCP确认原静态抽卡菜单，未在原有账号消费；本次不新增活动UI，也不将历史活动宣称可玩。

2026-10-27第150区新增正式可玩及活动可开放关卡11050/11051/11052/11053，已逐关原客户端真实胜利和完整重启验收。沿用现有活动开关、时间和drops接口，不变更schema。原掉落模板齐全，可用drops=[]保留原掉落；未验收20101/11100等仍拒绝误开放。当前QA运行库旧test-local-layers关闭、revision29保持，未自动创建新活动。实机挑战与本地客户端声明校验的边界见[第150区协议](../protocol/STORY_AREA150.md)。


## 向本地账号发礼物（2026-10-27）

当前传输边界：JSON解析器继承原Python行为，重复对象键会取最后值；调用方必须只提交一次每个字段。方法表之外的PUT/PATCH/DELETE等经后台处理返回405 JSON，但OPTIONS/HEAD沿用HTTP基类501/HTML响应头（HEAD无正文）。这两项已登记为暂缓Minor，尚未统一解析/方法分派。

GET `/players` 返回 `{"data":[{"user_id":1,"user_name":"Local","rank":1,"pending_present_count":1}]}`。按user_id排序，仅列上述四字段，不返回UUID、会话或完整存档。GET `/presents/{user_id}` 返回 `{"data":[原礼物DTO]}`，只列该账号未过期、待领取礼物。

POST `/presents/{user_id}` 必须精确提交五字段：

```json
{"request_id":"local-20261027-001","message":"本地运营礼物","present_type":1,"present_param_0":100,"present_param_1":0}
```

|字段|约束|
|---|---|
|URL user_id|已存在本地账号；正整数ASCII十进制、无前导零、最大2147483647|
|request_id|1–80位ASCII；字母或数字起始，其后可含字母、数字、下划线、点、冒号、连字符|
|message|1–120个Unicode字符；允许换行，拒绝其他C0控制及无效代理码点|
|present_type|严格JSON整数1金币、2友情点、3免费水晶、4原单位；不支持付费水晶|
|present_param_0|类型1数量1..9999999，类型2数量1..10000，类型3数量1..999；类型4为原单位master ID|
|present_param_1|货币类型严格整数0；单位类型为1..该单位原max_level|

JSON布尔、浮点、字符串不能代替整数，不接受未知字段。发送人为LOCAL/user_id0，永久礼物open_limit0，date为UTC时间；serial_number沿用账号单调递增的原礼物序号。

首发201返回：

```json
{"data":{"user_id":1,"request_id":"local-20261027-001","present":{"serial_number":1,"send_user_id":0,"send_user_name":"LOCAL","message":"本地运营礼物","present_type":1,"present_param_0":100,"present_param_1":0,"date":"2026-10-27T00:00:00+00:00","open_limit":0}},"replayed":false}
```

serial/date是示例，实际由服务端生成。**request_id作用域为URL账号**：同账号同编号同内容重试200，replayed=true，返回首次原礼物；同编号内容不同409（沿用error.code=revision_conflict，message说明投递编号冲突）。不同账号同编号是两个独立发送，不提供全服批量事务。回执随玩家存档持久保存，领取后或服务重启后重试也不重新入箱。

发送仅新增礼物、序号和发送回执，不立即增加余额/单位，也不改变卡池活动revision。玩家通过原get_presents/open_present领取；领取时沿用货币上限和单位容量校验。满仓仍能收信，腾出空位后再领；不支持绕过上限发放或付费。

错误沿用JSON格式：未知账号或非法账号路径404、方法405、JSON格式400、媒体类型415、字段422、编号内容冲突409、超1MiB为413；任何失败均不保存部分礼物/序号/回执。SQLite事务保证多API实例同时重试也只发送一次。不需要Cookie、玩家会话或expected_revision。本地回环服务启动方式保持不变。

## 原活动积分（实验，2026-10-27）

drops规则新增可选sp_event_point，严格整数0–999，缺省0，不重写旧schema2配置。与attribute_exp可同时存在；只允许原QuestMaster.sp_event_id在SP_EVENT_MASTER中的关卡配置非零，不能给普通关伪造活动ID。数量为运营者明确本地规则，原1808掉落表缺少此字段，不能称原服概率/数量恢复。地形/未出现敌人积分0，掉卡与积分独立。单场积分由原PlayerData上限999约束，活动累计封顶99999。

例如原活动13208的某个真实drop_data_id规则可写{"drop_data_id":实际目录ID,"no_drop_weight":1,"entries":[],"sp_event_point":1}；这里不把示意文字当可直接提交的JSON。实际ID须从catalog获取；空entries是管理员明确无掉落选择，不是恢复原掉落。普通11000的非零积分返回422且revision不变。

13206/13207/13208仅加入实验可配置范围，正式模式仍未验收/拒绝新入场。为它们显式绑定活动时，派生关卡表的本地时间替代旧2013窗口，原前置保留；删除恢复原日程，关闭不重写已入场快照。并不自动开放任何活动。

入场冻结原event_id及出现敌人的积分上界；clear_quest2只接受0..冻结上界，按层事务累积，失败/放弃无积分，回执重试不重复。旧无快照运行只接受0。原积分门槛检查不消费，已通关区域装饰不绕过关卡按钮检查。登录返回sp_event_point_list=[{"sp_event_id":100002,"point":实际累计}]；未新增独立积分领取协议。当前11项隔离SQLite集成及7项纯政策测试通过；原13208实报/持久5点、原包重放与登录DTO一致；双端冷重启后原包重放及登录仍保持5点，六态与81场/56回执不重复，不把合成测试输入当实机胜利。详见../protocol/SP_EVENT_POINTS.md。
