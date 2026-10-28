# 11000普通关实现与证据

用户2026-10-25明确批准同类原版视觉替代，优先可玩。原始ENEMY_UNIT_MASTER文件不改：内存派生type20只替换enemy41221的model=ms01_sla_lv1、texture=ms01_sla_lv1_fire。原模型和纹理名称保留在manifest；所有其他字段与行保持一致。派生hash为规范化data_list的CRC32十进制，另记SHA256；启动日志打印LOCAL VISUAL SUBSTITUTE。RTD_VISUAL_RECOVERY=0关闭替代并禁止11000入场。其他未支持关卡不会因此放行。

APK mainData ResourceManager的两个目标均已解析到真实对象：Prefab/Enemies/ms01_sla_lv1 → Data/09fe8f7a7301a0a43872be7902714b97/pathID1/GameObject；Prefab/Enemies/Textures/ms01_sla_lv1_fire → Data/31adf56cc15e7604ca8d48fddcb9fd3a/pathID1/Texture2D。原始APK本地模型名单含ms01_sla_lv1，仍走正常加载分支，不删Boss或跳预加载。

入场前置为10001完成位；floor0/resume0/helper0/无活动加成、14个hash及11000地图hash匹配，三自有角色完整且唯一，按原表扣3AP。地图每个敌人候选按arrange_rate抽样；掉落按unit1..4权重累计抽样，剩余概率为空，非空单位等级在原始闭区间均匀选择。随机源为SystemRandom，属于本地抽样政策，并非原服随机算法。抽样结果只在新运行生成一次并持久化，同GUID重试/API重启不重抽或重复扣AP。特殊敌人使用原表arrange_id，不按boss/death前缀猜测。

奖励目前有界支持单层clear_quest2：经验50，金币500–17500，依代经验符合0–99魂、reward_soul30的原客户端公式；最多5本书且为该运行掉落单位/等级的子多重集。level>1书单位的累计经验按UnitData.GetLevelExp(level-1)与原category/grow算出，包含Single精度截断；依代经验保留客户端公式结果。完成位、升级、书/依代、挑战位、清活动和回执在同一事务。11000的present_type=0，不虚构首通水晶。

## 挑战支持范围

原表挑战10为type40“不续关”，11为type10“剩余魂至少10”，12为type31“击败至少5个敌人”。BattleChallengeData.ResultChallenge只提交新完成的ID，未带击杀明细；参考BattleChallengeData.cs、Challenge/ECHALLENGE_TYPE.cs与CommunicationRTD/QuestChallengeState.cs。

- 只接受本关10/11/12，不接受重复ID或其他挑战；10须服务端继续计数0，11须提交的依代经验能对应魂>=10。
- 12采用明确的本地客户端申报政策：当前快照至少有5个可能击败的普通/Boss敌人，排除宝箱与arrange_id99惩罚敌人。没有逐击杀轨迹，不能证明实际击杀5个，不能声称战斗重演防作弊。该限制是恢复旧客户端可玩性的一项取舍。
- 成就位以quest_id/challenge_id持久保存，重刷重复申报不增加记录；登录及主表同步返回已完成位。挑战奖励领取接口/礼物箱尚未恢复，此处不发伪造礼物或标记奖励已领取。

当前19项临时库测试通过，包含概率边界、禁用替代、单位经验、真实HTTP生命周期与事务回归。一次独立整体代码审查未发现Critical/Important/Minor问题，另核对非法奖励、挑战边界与故障回滚。模拟器首通已通过，重复挑战及重启验收仍在进行。

## 实机证据

- 隔离库analysis/android/flow-runs/ordinary-11000-20261025/test.sqlite3，由已验收rank2库SQLite backup生成，原账号3和此前检查点不改。
- flow-runs/20261025-164554：真实地图11000/hash45167553，正常加载替代Boss、推进战斗并直接收到clear_quest2=4096；经验100→150、金币80500→81750、单位8→11，新增15012、11030及依代50000/exp435，battle=null、挑战10完成。未修改完成位或重发结算。
- flow-runs/20261025-165254：补齐MMResult502挑战勋章确认后回到SELECT_AREA。不能称首次全程无间断输入。
- 首通后列表将新关11001置顶；旧ClientData.m_SelectedQuest字段在出发才更新，因此新增只读MainMenu.m_SelectedQuest及MMQuest列表ID/坐标。自动输入依据实际ID11000选择，出发前核对，未知条目不猜测。
- 已发现客户端自然恢复与服务端旧AP不一致；600秒/点来自ClientData.RecoverPlayerAP，另立2026-10-25-stamina-recovery计划处理，不擅自加AP掩盖差异。

第二次验证补充：20261025-170803正常重刷成功，经验200/金币83150/16单位；20261025-171912由脚本按实际关卡ID完成选择、出发、战斗、结算和回SELECT_AREA，经验250/金币84400/20单位、挑战10/11、battle=null。11000累计三次cleared运行、全库5条结算回执，说明正常重刷未被旧回执误去重。第二次重刷使用新自然体力政策，入场双方18/21AP、recover1792920044一致。两次重刷的奖励不同，不以此单独证明“相同奖励”分支；相同奖励正常重刷另由HTTP测试覆盖。

观测修正证据：questRows最初投影Transform原点导致三次点空，改为collider.bounds.center后真实行中心944命中；静态审查通过不代替实际点选。此修正不改变其他既有按钮的Point行为。

双重启20261025-172628再次回SELECT_AREA，完整存档state SHA256前后均afa6cbb0e0d7f97a8ac52197c5401cc57ba897593fab64125cbd8a451b668dc3，3条11000通关与5条全库回执保持不变。该证据是已结算后重启，不代表恢复中途战斗进度。

独立断连回归：停止API后通过MCP选11000进入助战请求，客户端出现真实“通信エラー／再接続”；恢复API并点击该按钮后，客户端重新认证并成功get_helpers（ordinary-network-api.log，17:30:38），显示LOCAL_HELPER。经验/金币/水晶/单位/活动battle/回执均未改变，见ordinary-11000-20261025/network-reconnect-verified.json及前后截图。此验证为无扣费助战请求重连，不代表丢失战斗快照后的任意恢复。

原版替代源文件SHA256：GameObject 54587b5f261feb3611b76718d3c251efbd48cf838d90ffadf99862c871530781；Texture2D 3f9aaf2622c77fcbe4f646b47b1c05f8e7254669c66e978a6eb19f0f750d7e36。
