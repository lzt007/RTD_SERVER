# 好友协议与补齐记录（2026-11-01）

## 客户端契约

证据来自归档 `docs/archive/protocol/index.json`，原 ComManager.cs SHA256 为 11cff27fbd5c0a5adfc42680f896a60dcb0762baf9e3c5390b3cf3bb0a1986dc。本次未取得原 DLL 或设备运行记录，不把静态分析与 API 测试作为实机验收。

|功能|操作|请求专有字段|成功 result|
|---|---|---|---|
|好友及申请列表|get_friends|无|FriendData 数组，状态0好友、1发出、2收到|
|搜索|select_user_code|user_id，十进制字符串|SearchedFriend，未找到 null|
|添加／发申请|send_friend_request|friend_user_id，十进制字符串|空数组|
|接受申请|accept_friend_request|friend_user_id，整数数组|count 对象|
|取消／拒绝／删除|delete_friend|friend_user_id，整数数组|空数组|
|助战列表|get_helpers|无|HelperData 数组|
|借用角色|order_quest|helper_user_id 及既有订单字段|既有订单结果|
|友情点|clear_quest2 / login|既有结算／登录字段|结算余额／friend_point、help_count、received_friend_point|

共同字段 ver=2.4.0、retry；响应包含 code、session_id、result。好友查询和搜索分别保留13及10个公开字段，不泄露账号身份或会话。客户端 MMHelperRequest 与 MMFriendSearch 都调用 SendFriendRequest，没有独立“战后加好友”接口。SendFriendRequest 明确识别8704（好友满）和8706（已是好友）；AcceptFriendRequest 另识别8705（对方好友满）。现修正发送申请时对方满额的返回码为8704，避免返回该操作未识别的8705；接受申请仍保留8705。

## 根因及修改

默认 NPC 的 ID 为0，原来 friend=false。客户端战后可进入申请流程，服务端正整数校验拒绝0，产生无法完成的通讯。NPC 改为 friend=true 表示无需申请的助战关系，仍不加入真实好友列表、不占容量、不发友情点；旧客户端的0号申请返回已识别8706。此兼容含义是本地策略，需要设备验证提示文案与分支。

原助战只列出已接受好友，无法从真实陌生账号借用再申请。现追加最多20名无关系的本地账号，按ID排序，排除自己与申请处理中账号；只有一个账号时仍只有NPC。单层、多层根订单都可借用真实其他账号，冻结角色与好友身份，重试及后层沿用旧快照。借用后发送申请、对方接受、双方查询仍使用既有原子事务。

基础友情点按入场时身份：好友10，陌生人5，NPC0；每日有向账号对仅成功结算一次，跨日以根订单入场日为准。好友关系改变不追改当前场次，也不重置当天领取记录。type10加成及10000上限沿用现有规则。提供者下次login领取10点，是明确的本地策略，不能声称恢复了陌生人原服提供者奖励规则。

既有搜索、批量接受、拒绝、取消、删除、容量、送角色及双方事务回滚继续保留。支付没有纳入此次修改。

## 验证边界

新增覆盖 NPC 标志与0号申请、真实陌生人借用→通关→申请→接受→提供者登录领取、入场后接受仍5点、同日不重复与次日好友10点、多层陌生人快照。沿用原好友与助战奖励回归。未操作正在运行的服务、实际账号数据库或客户端安装包。
