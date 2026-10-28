# 本地登录奖励边界

UTC自然日为服务端日界，月内实际登录次数作为原login_days，跨月重置；sequence跨月连续，断登重置。原51表只有1/2月数据，按原UI忽略年份、当前月份/第N次登录匹配。其他月份不生成虚构日历；原主表不变。每个登录日的奖励快照与礼物同事务持久化，同日并发/重启/重试不重复，时钟回退不补发。迁移旧账号当天无快照时不补发礼物或启用新属性，下一登录日才启用，避免原客户端已缓存当天0加成。

原52表1–7项为生命+1000、攻击+500、回复+500、关卡经验+50、关卡金币+500、好友点+50、掉落额外一次空抽重试。按min(连续天数,7)选择是本地重建政策，不能声称原官方超过7天算法已恢复。属性由原MMLogin应用且存入LOGINBONUS_PARAM；同日原客户端通过LOGINBONUS日期缓存跳过应用。服务端返回同日快照，已有bonus_flags不清零。

GameStatus的金币/经验是固定加值并按关卡limit封顶，不是倍率。10001/11000下单时存battle_login_bonus，重试不改变、跨日登录不修改旧关加成，结算后清除；旧关无快照按0兼容。掉落按原空抽最多两轮，已有书立即停止且每敌人最多一本，出现概率独立。原服务端提供drop_unit_id时客户端直接使用，故加成需在服务端抽样。类型1/2/3由客户端战斗属性应用；类型10原这里只存在显示/缓存，现有本地助战不计官方好友收益，不额外伪造点数。

post_bonus原唯一bit0调用在MMQuest category3000推广按钮，成功后直接OpenURL原商店。支付/评价/跳转凭据不在本增量伪造，仍明确8197，移交T25本地平台政策，T22总任务继续DOING。

REA原DLL SHA c83aea19ee65ae973815daf6a04e430d9e87b8426b6180c1fe507e4260763ecc；parent ev_c5120cad916318648dc3f719883fe2fe21b599257141baf15ba76e2dae78a661（MMLogin/UILoginBonusDialog/MMQuest及PostBonus DTO）与ev_a04916b320440706a196edcdde18960f81dd8dce1b56d9a6430dede5a304e594（GameStatus/DropManager/LoginData及2主表类型），各5类型匹配，metadata完整，各#US一处terminal flag异常。

服务端66项回归43.271s通过，独立审查66项46.557s通过且无重要问题。17项Android工具测试0.654s通过；实机首次遇到奖励弹框时保护停止，新增严格匹配已收到bonus类型/天数及确认点的安全处理后，MCP自动确认成功，原客户端appliedLoginBonus[8]=50。

login-rewards-20261025隔离库使用明确的昨日/连续3天/月内3次夹具，仅调整登录时间与计数，币/单位/奖励档未改；不声称真实经过4天。备份原私有prefs后仅移除LOGINBONUS/LOGINBONUS_PARAM以验证原版登录弹框和应用逻辑，不改全局时钟。21:02:18全自动11000结算4096：exp100（原50+50）、金币1250、依代exp435、3本书；玩家exp350→450、69575→70825金币、5→9单位，订单已清除，after-bonus-battle.sqlite3留证。

客户端/API双重启后完整存档相同，原客户端从当日缓存恢复appliedLoginBonus[8]=50，没有重新发奖励或结算。after-login-restart.sqlite3及restart-verified.json留证，状态SHA b7ee2f38afaa2cbd64d8b52e4640d1d0061c9aff49226b807de06183e3a1b51f。原版日历弹框仅原月份有数据，当前10月未触发；实际验证的是连续奖励弹框与经验加成，未冒称全年日历实机验收。
