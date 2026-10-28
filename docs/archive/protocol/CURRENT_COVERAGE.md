# 当前通信覆盖与开发重点

2026-10-28：中文 Web 后台已完成并运行于 http://127.0.0.1:18767/admin/ ，支持卡池与活动启停/日程/权重/掉落，版本冲突保留草稿。Python228/228、Node11/11及隔离浏览器验收通过；与18766同库，真实配置版本32及完整存档保持。见 [Web后台说明](ADMIN_WEB_ACCEPTANCE.md)。

2026-10-28资源核查：从实际 Unity 原生注册表、文件名处理及 SHA1 调用还原 Shared 缓存键，90/90 原缓存全部唯一命名；76 当前基础包、7 敌人包、7 个角色 751–820 包。音频缓存版本 12 对 APK 请求 6，741–750 为 11 对请求 10；CDN 根不参与该键。只补齐下载服务缺失的原版龙与 7 个角色包，全部 90 原包载荷哈希往返一致，新增 8 包 HTTP 长度/哈希通过。独立设备探针对照未产出完整结果，未进入原缓存恢复阶段，不能称游戏内加载已验收；三轮均恢复原 APK/无进程及原数据、缓存和后台库内容。见 [原缓存身份与发布核查](ORIGINAL_CACHE_IDENTITY_20261028.md)。

2026-10-28用户调整优先级：本机模拟器性能及偶发崩溃暂不作为阻塞，只处理稳定复现的问题。暂停进一步SIG11/原生故障实验，优先核心功能与运营配置的真实使用闭环。下方取证记录为历史进展，不再代表当前开发重心。GLES2实测失败后已回退原GLES3；当前原APK/无游戏进程、完整SQL/六账号273会话88场62回执/请求/偏好/服务均现场核验保持。新保护错误记录器与自有夹具仅完成离线测试（全部原生工具217项通过），现场传输前置失败、未发送故障命令，不能称PC/地址捕获已验证；对应计划Task3尚未完成。

系统调用取证：独立夹具已获得内核SIGSEGV与Frida双正例，但唯一游戏启动实验因Android绑定超时被SIGKILL9终止；没有复现旧SIG11。未验收的启动追踪入口已撤下，默认启动精确还原；唯一审查后修复短写及未完整回执的拒绝，全部186原生工具测试通过，无现场重放。全态、原包和服务保持；新增归档换行Minor暂缓，见[取证结果与撤回](NATIVE_SYSCALL_EVIDENCE.md)。

启动身份取证新增严格只读适配器，165原生工具测试通过。唯一一次新窗口PID13278恢复后90.912秒、公告实际显示，未出现身份差异/原生异常；MCP正常关闭并恢复原包，全SQL/273会话/六账号/88场62回执/偏好/请求/30保护文件/服务不变。前次PID12041差异原因仍未知，不宣称SIG11修复，见[启动身份差异证据](NATIVE_IDENTITY_EVIDENCE.md)。

2026-10-28新增：启动公告HTML及原com_text4 GET/POST已本地化，独立于下方36个核心游戏协议。新候选ddc68da5通过flow033400原生公告显示及原held11000恢复，零新入场/结算；225 Android/88原生/9 HTTP/5管理补丁/33缓存检查通过。见[本地启动公告](LOCAL_STARTUP_NOTICE.md)。当前无游戏PID，原安装APK已恢复；API25508仍使用quest-departure-guard QA，默认测试候选已升级，正式库未迁移。

最终审查三项防护修复后为227 Android/88原生/10 HTTP/8管理补丁/9打包/33缓存检查通过，候选哈希不变；一次独立审查、一次C/I修复，无复审。

原生诊断补充：首次独立app_process测试发现旧记录器for-in漏采真实寄存器，正确拒绝成功；现已修复为显式读取，第二个独立v2测试获得11项寄存器/5帧、无错误并确认退出，runner0。全native131/131。游戏、完整SQL/273会话/六账号/偏好/请求均未变化；只证明通用ia32采集，不证明ARM翻译链或RTD SIG11根因。见[寄存器采集修复与真实正例](NATIVE_REGISTER_CAPTURE.md)、[保留的首次失败](NATIVE_FAULT_POSITIVE_PROBE.md)。

取证宿主已加总时限及显式退出，147原生工具测试通过。一次真实冷启动因身份读数提前停止，但随后证实同一完整生命周期进程仍存活，故未判定崩溃/未计90秒通过；MCP正常关闭及原包恢复，全态不变。连测已停止无重试，见[宿主截止与实际诊断](NATIVE_HOST_DEADLINE.md)。

整轮审查后补充核心清理挂起前保存原始错误，150原生工具测试通过；无设备重试、无业务状态变化。

2026-10-27。停止重复逐关推进；复用战斗只对新机制、资源和异常恢复做必要抽样。以下是当前代码与原客户端静态索引的交叉核对，不采用早期可行性报告里的旧“未实现”描述。

原DLL静态索引47个地址，当前36个游戏协议已路由（34个ROUTES加create_user/auth_user）。原DLL SHA c83aea19ee65ae973815daf6a04e430d9e87b8426b6180c1fe507e4260763ecc；来源[index.json](index.json)、[routes.py](../../server/rtd/services/routes.py)、[api.py](../../server/rtd/services/api.py)。地址存在不等于当前客户端有可达调用；这里不把静态占位地址全部算作待开发功能。

|功能|当前实现与边界|现有证据/测试|
|---|---|---|
|账号/登录/主表|create_user、auth_user、login、get_master、get_level_master、get_units|原客户端多次实际登录及完整存档重启；server/test_accounts.py等|
|队伍保存|form_units，5队×5槽、主队/备用槽、所属/重复/战斗中修改约束|[UNIT_MANAGEMENT](UNIT_MANAGEMENT.md)：实际队伍保存及重启；test_unit_management.py|
|收藏与本地标志同步|save_unit_favorite_flags、save_local_flags、save_quest_new_flags|原收藏重启、图鉴/关卡新标志实际线包；test_unit_management.py及真实恢复验收|
|设置保存|原MMEtcOption直接SaveDataManager.Save，BGM/SE/GUIDE写本地SharedPreferences；没有新增服务端设置协议|本轮正检查实际切换及完整客户端重启，见输入兼容文档；不是缺少后端接口|
|体力扣除/恢复|原关卡入场扣一次、按原恢复间隔自然恢复、等级变化、原buy_recover_ap；恢复/重试不重复收费|test_stamina.py、test_transactions.py、同场恢复真实get_quest_info证据|
|好友与发送单位|get_friends/select_user_code/send_friend_request/accept_friend_request/delete_friend/send_present；仅可赠送原表允许的所属非收藏/非主队单位|test_friends.py、services/unit_gifts.py；既有实际好友赠送链路|
|好友助战友情点|有向好友对按UTC入场日成功结算一次，借用者10＋冻结type10加成、提供者登录领取10；NPC零，频次与触发为明确本地政策|test_helper_rewards.py的16项合同；实际原胜利FP1870→1930、提供者MMLogin101领取10并MCP确认，见LOCAL_FRIENDS|
|礼物领取|通过get_presents/open_present，批次原子领取、唯一serial、货币/单位容量、持久回执|[PRESENTS](PRESENTS.md)、test_presents.py及实际领取/重启|
|挑战奖励|post_quest_challenge_reward，原挑战完成位/积分交集检验，经礼物箱领取|PRESENTS及既有实际挑战领奖|
|每日登录|login内UTC换日、连续登录/原月日历奖励、重登不重复；已实现|[LOGIN_REWARDS](LOGIN_REWARDS.md)、test_login_rewards.py；本轮真实UTC换日全态复核|
|独立每日任务|47地址及当前原类调用中未发现独立每日任务/每日领取任务协议|不把post_bonus当每日任务：原调用是商店导流推广，不能据名字编造协议|
|单位成长|sale_unit/compose_unit/evolve_unit/ultimate_evolve/sp_compose_unit，原等级/素材/属性经验及持久化|既有真实强化/普通进化/特殊/终极进化及完整重启；新增原16028出售1AP；只读独立恢复框观测已支持MCP单脚本（flow130208退出0），HTTP回放及双重启见UNIT_SALE；对应server测试|
|抽卡/本地商店|buy_gacha/buy_gacha_special/buy_max_unit/buy_max_friend/buy_recover_ap|[LOCAL_SHOP](LOCAL_SHOP.md)、既有抽卡/余额测试和实际操作；无支付|
|战斗/助手/多层|order_quest/get_quest_info/get_helpers/clear_quest/clear_quest2/continue_quest|既有普通、多层、同场恢复证据；服务端控制持久状态与结算，不重做客户端战斗引擎|
|卡池/活动运营|现有/admin/v1/config、gachas、events、catalog，开放时间/内容/掉落/可玩门控|现有后台API文档、test_admin_http.py/test_live_configuration.py|
|原活动积分|EnemyInfo本地显式sp_event_point配置，单/多层冻结、clear_quest2事务与幂等、login原列表、原积分解锁门槛|[SP_EVENT_POINTS](SP_EVENT_POINTS.md)：223服务端/182Android检查；原13206/7/8真实胜利、13208原报5点且持久5点，双端重启/原包重放保持5点；仅实验内容|
|后台发物品|GET players/presents与POST presents/{user_id}，持久幂等发送原礼物箱；玩家仍通过原open_present领取|[后台接口](../api/ADMIN_OPERATIONS.md)、test_admin_present_delivery.py；不直接写余额|

尚未路由的11个静态地址逐项裁定：

|地址|裁定|
|---|---|
|app_store_purchase_begin/app_store_purchase_point/google_play_bill_begin/google_play_bill_point|按用户要求排除支付|
|make_password/move_save_data|按用户要求不关注官方设备迁移|
|accept_invite_usercode|外部邀请平台，原本地平台政策禁用；不伪发奖励|
|post_review_present|外部商店评分奖励；本地客户端明确提示禁用，不伪发水晶|
|post_bonus|原MMQuest推广导流领取；外部推广入口已隐藏/提示，非每日奖励|
|get_shop_list|有地址/响应占位，当前SetAddress/请求构造器/调用未发现；实际本地购买走上述buy_*|
|save_tutorial_flags|有地址/响应占位，当前可达请求构造器未发现；教程实际状态沿用已验证流程，不猜空DTO|

这份索引不声称所有UI边界已实机覆盖，也不把后端测试替代真实客户端。新的通信开发应从实际可达调用失败或明确运营需求出发；旧历史文档保留原时间点，三项已登记Deferred Minor不在这里偷偷改写。

补充边界排查（2026-10-27）：USER_RANK_MASTER完整200行（rank1–200）的unit_id均为0，故“Rank unit grants are unsupported”在当前恢复数据不可达；不为静态拒绝分支虚构升级赠卡。原体力上限/好友上限/金币/好友点升级奖励沿既有实现和原MMResult，flags2也未据名称猜作容量奖励。原DLL SHA/MVID经REA三类型精确选择复核，元数据与成员覆盖complete，user_strings因原terminal flags标记partial，不能称全局字符串无遗漏。共同只读证据analysis/android/flow-runs/protocol-boundary-audit-20261027；无业务或存档改动。

最新复核（2026-10-27）：原静态47地址与当前34 ROUTES＋create/auth两路逐项对齐，未路由11项恰好等于上述明确排除/未发现可达构造器清单，无新增原因不明缺口；这不等于穷尽每个UI时序。核心协议、输入兼容及本轮恢复缓存闭环已具备。恢复书结果修复及同PID下一场原出发实测、全部裁定与225server/189Android/33C#门见[RESTORE_MENU_CACHE](RESTORE_MENU_CACHE.md)。原生SIG11有新失败样本和Zygote原行，仍未定位，继续做运行时取证，不能把核心协议覆盖冒充永久无人值守稳定。

2026-10-28：[绑定完成后有限原生取证](NATIVE_BOUND_CAPTURE.md)一次默认启动后取得90.943秒双观察器/有限strace窗口，正常解除附加和MCP关闭，完整数据及原包恢复保持。未复现或修复SIG11，不覆盖启动早期。

2026-10-28：[被动内核信号记录](PASSIVE_NATIVE_SIGNALS.md)以自持夹具SI_USER正例验证后，一次出生前开始的游戏窗口完整120秒无丢失；取得灰色启动卡住及goldfish_pipe主/GL线程内核栈。游戏启动未验收通过，旧SIG11未修复；业务与原包恢复保持。

2026-10-28：[GLES2单变量实测](GLES2_COMPATIBILITY.md)确认实际EGL2仍SIG11；出生前完整内核记录定位本次GLThread4309的两次生成/投递及handler变化，未得到PC/地址。原GLES3环境与全业务状态已恢复，未重试或宣称修复。
