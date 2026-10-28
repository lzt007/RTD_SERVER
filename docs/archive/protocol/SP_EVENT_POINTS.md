# 原活动积分通信

2026-10-27。已接入本地配置、单/多层冻结结算及登录保存；223服务端、182Android、4资源检查通过。原13206/7/8真实胜利与完整六态审计通过，13208原clear提交5点，活动100002存储5点，原请求HTTP重放及登录后不重复。双端冷重启验证通过。实验验证计划见superpowers/plans/2026-10-27-sp-event-points.md。

原Assembly-CSharp.dll SHA c83aea19ee65ae973815daf6a04e430d9e87b8426b6180c1fe507e4260763ecc，MVID81502538-516d-4802-bbff-d4f363e3388d。REA静态检查不执行目标、不反射加载、不声称反编译；既有ILSpy输出仅用来解释精确方法，关键上限由本轮REA指令锚点核验。

|路径|原事实|
|---|---|
|EnemyInfo.sp_event_point→BattleManager→PlayerData.AddEventPoint|敌人给予的积分累积至本场变量|
|PlayerData.AddEventPoint / 0x060005e8|38字节IL，常量999位于IL17和27，单场封顶999|
|ComManager.CreateRequest_QuestClear2|原结果写入RequestClearQuest2.Quest.sp_event_point，不新增操作地址|
|MMResult.Update / 0x06000aba|按原quest.sp_event_id累计；常量99999位于IL1056和1083，已有活动累计封顶99999|
|CommunicationRTD.SpEventPointList|sp_event_id及point均i4；登录列表原字段|
|QuestMenu.Quest.Setup / MMQuest点击|按open_sp_event_id/open_sp_event_point检查，点数不消费；AreaMenu已通关装饰不等于入场绕过积分条件|

REA请求嵌套类型的斜线、加号和完整命名空间拼写均未匹配；实际提供器将这组TypeDef声明名返回为Quest，字段0x04000a48–53与原嵌套请求对应，其中sp_event_point=0x04000a4e。保留所有未匹配摘要，不把选择错误隐藏为完整覆盖。PlayerData/SpEventPointList/QuestMenu.Quest所选字段19、方法14、访问107均穷尽；MMResult/ComManager方法只保存前20/139，足够定位选定MMResult.Update，不宣称调用图穷尽。较大UI选择的user_strings为partial，不能据此宣布没有任何其他字符串或协议。

原SP_EVENT_MASTER12行，QUEST_MASTER1021行中106行有关联ID、70行非零积分门槛。ENEMY_DROP_MASTER1808行没有积分数量字段；后台未来显式配置的数量属于本地运营规则，不是恢复出的历史积分。没有根据字段名虚构每日任务或独立积分领奖接口。

纯政策模块event_points.py：freeze返回原event_id及已出现敌人积分上界（<=999）；apply只接受0..冻结上界，持久state.sp_event_points累计至99999；login_points仅排序返回原DTO；require_points不扣点，仅检查新入场门槛。旧状态无字段为空，旧战斗无快照只接受0；坏存储拒绝，不静默清空。字段对象积分须由实际敌人生成器置0，freeze不猜测EnemyInfo未提供的敌人类型。

本轮证据存于analysis/android/flow-runs/sp-event-points-20261027/evidence，包含REA原摘要及视图、原反编译片段哈希、主表计数与测试结果。单元测试均为明确合成边界输入，不是原客户端战斗/领奖证明。

实机补充：13206首次结果请求带原挑战11764/11765/11766，服务端原来拒绝type30，8197由客户端显示2005。现按原BattleChallengeData.CheckChallengeClear及ChallengeData.Add_KnockDown_EnemyCount恢复WANTED：匹配原grade槽位、目标EnemyUnitMaster ID及已出现非宝箱数量上界；没有击杀轨迹，属于有界原客户端声明。原type20检查param0..3全部非零unit_id，包含冻结助战。REA所选三类型匹配，11方法页完整，CheckChallengeClear=0x060004c6/651字节IL，Add_KnockDown_EnemyCount=0x06000ee5/239字节IL；原文件SHA不变。旧ILSpy仅解释方法，不声称REA反编译。

13206 flow164109真实GameClear但首次结算失败；同PID4805由原错误页返回、原存档恢复flow165143最终完成。一场原入场、一次体力扣除、一个唯一回执和全部六账号/配置/完整存档精确核对，首次失败包保留，不将第一次driver写为成功。随后发现原TitleMenu恢复生成一组六槽临时队伍，导致下一关form_units被五槽合同拒绝；存储五队保持，未扣新关体力。先原冷登录重新读取队伍，客户端恢复缺陷将另增量修复。

本轮实机证据：13207 flow170215，原clear挑战11768/11769；13208 flow170722，原clear挑战11771及sp_event_point=5，单场唯一回执/六态审计通过。三关后81run/56receipt、104单位、rank15；13208结算截图是“无Continue”挑战勋章画面，不是5点计数器截图。HTTP重放原13208包、原login DTO均保持100002:5，六态仅允许请求时间的自然AP恢复。

本地实验活动qa-sp-event-13206-8（revision30）明确开放13206/7/8，只有13208所有非地形规则sp_event_point=1；drop0保留原空掉落，缺失原行13206:31147/31503/31509，13207:31147/31149/31504/31510，13208:31167/31169/31505/31511明确配置QA空掉落，不冒充历史概率。这三关保持实验门控，不纳入正式VERIFIED。资源政策基线实测161→165，四新替代11002/11022/12104/12106及九行活动关联，所有非视觉数值原样；固定标记ms02_four_un_01_zako/na沿用户授权。

双端重启：API7412/sp-event-points-v3，首次客户端PID11696在预检前被Zygote记为signal11退出，无新tombstone，零请求/六态精确/原安装APK恢复，未隐藏为成功。一次明确带被动记录的诊断启动PID12082、flow172541/session172539成功进入原账号MainMenu，完整六态AP29→29不变；随后原13208 HTTP回放和原login DTO仍100002:5，81run/56receipt/rev30不变。记录器90秒19帧绑定同PID/出生标识/boot，running_timeout仅表示观测窗内末次仍在，不承诺此后存活。原SIG11根因未修；ioctl提示在此前成功轮也存在，不能当作原因。原件六项哈希及来源QA六态再次核对精确。

最终整体审查C0/I1/M1：原积分字典键、非零冻结事件及门槛身份现均校验原SP_EVENT_MASTER成员；未知ID坏档拒绝8197，不静默清空或发奖，登录/入场/重启结算全事务回滚及同库其他账号保持。已接受数量不因当前配置改变而重算；合法ID间任意本地手改不提供篡改认证保证。225服务端/182Android GREEN，v4/PID22612重启全六态精确，实际原包重放和login仍5分。注意：前述PID11696精确signal11是执行者当时工具观察，未归档Zygote系统原行；可独立复核的档案只证明预检失败、零请求与全部存档不变。完整审查/裁定见../reviews/2026-10-27-sp-event-points-review.md。
