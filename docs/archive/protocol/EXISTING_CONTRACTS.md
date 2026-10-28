# T04 现有契约与重试

传输：POST `/rtd/2.4.0/api/<operation>.php`，表单键request是JSON对象，客户端版本2.4.0；Cookie为RTDSESSID，query user_id如存在必须等于会话玩家。响应code必须第一个字段，紧凑UTF8 JSON经GZIP编码，禁止HTTP Content-Encoding。成功4096，未知操作8197，结构错误8194，版本8193，认证失败8195，缺少/过期会话8196，越权8198，非法名字8448，冲突注册37122。错误解析先读code，非OK不进入成功DTO（ComManager.ChangeReturnValue）。

精确字段、继承、构造缺省和嵌套类型以index.json中对应DTO完整源码为准，不从字段类型臆造允许null的业务语义。字典构造器全文也已收录。成功和失败的脱敏HTTP样本为samples/isolated-http.json，通过server/capture_contracts.py从临时DB及随机端口重建，不采集生产凭据。它们证明本地HTTP行为，不是原服样本。

| 当前支持 | 响应契约/范围 | 重试与边界 |
|---|---|---|
| create_user | ResponseCreateUser / ComPlayerDataGC及UnitInfo、party | UUID同参数重复不重置；不同参数拒绝。空session_id |
| auth_user | ResponseData / ComPlayerData（比注册多system_flag/payment_total） | 重新签30天会话；历史会话仍有效 |
| login | ResponseLogin / LoginData | 同UTC日只计一次；无实际登录礼物，不能称奖励已实现 |
| get_units | ResponseGetUnits / units和party | 单位去leader而保留favorite；注册单位恰好相反 |
| form_units | ResponseFormUnits / party | 当前5组5槽、所属检查、去重；旧单队RequestUnitForm有不同members结构，尚未宣称支持 |
| get_master | ResponseGetMaster加四类关卡标志 | compare_hash_only时不带data_list；20类型启动覆盖，21文件；不返回原历史玩家字段 |
| get_level_master | ResponseGetLevelDataMaster | 413地图，hash相同不重复；缺失明确8197 |
| get_quest_info | ResponseGetQuestInfo | 活动战斗列表或[]；活动快照持久化 |
| order_quest | ResponseOrderQuest | 仅10000；活动相同关卡重复不扣AP；普通关卡明确拒绝 |
| clear_quest/clear_quest2 | 各自DTO：对象/数组；clear2含present_param_1 | 仅10000、有限奖励范围、无随机掉落/挑战；同指纹重启回执，不支持升级。现回执未有运行ID，T08必须修复以区分正常重刷 |
| buy_gacha | ResponseGacha | 仅20000且tutorial_flag=true；首抽回执永久，不重复扣费 |
| get_friends/get_presents | 各自DTO | 当前只有初始空列表，完整社交/领取未实现 |
| save_local_flags | ResponseSaveLocalFlags | byte数组，幂等覆盖 |
| save_unit_favorite_flags | 成功只消费code/session外层，不解析result | 仅拥有单位及0/1；不代表出售保护已实现 |
| save_quest_new_flags | ResponseSaveQuestNewFlags | 将quest_id映射主表flag_no；不是数组索引 |

客户端SequenceCoroutine_Common遇RETRY会重认证后重建请求，retry变化；DB_DEADLOCK直接重试；ERROR弹框返回标题，不能把失败当作无副作用的原地提示。所有地址表retryLimit=5（null占位为0）。save_tutorial_flags、accept_invite_usercode、get_shop_list只定位到地址/空响应分支，无当前SetAddress构造；保留未知，不编造请求。

原客户端不提供通用幂等键。当前结算指纹去掉ver/retry/retry_count；不能据此实现普通反复刷关，必须在T08加入运行实例并记录无法区分的边界。
