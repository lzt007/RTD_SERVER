# 奖励发放与本地模拟充值

## 奖励

管理页增加“奖励发放”，选择全服或输入一个／多个账号ID。支持金币、友情点、免费水晶和原版角色（可指定合法等级），发到原礼物箱，客户端按既有open_present领取。提交前显示确认；成功后显示批次编号和实际收件人数。

POST /admin/v1/rewards 需要既有管理员认证，正文包含 request_id、message、present_type、present_param_0、present_param_1、target（all或selected）、user_ids。all要求user_ids为空；selected支持1–1000个不重复正整数账号ID。全服只包括提交时存在的真实账号，排除npc_helper_key标记账号；指定助战账号被拒绝。

V003迁移新增admin_reward_batches。一个事务冻结收件人并逐个发礼物，失败全部回滚。请求编号全局唯一，相同编号及相同内容重试返回原名单，新注册账号不被补发；相同编号不同内容409。JSON字段顺序及收件人顺序不影响幂等判断。前端网络失败保留原请求重试；明确的4xx校验失败允许修改。原单账号presents接口保留。

## 模拟充值服务端

config/simulated-store.json 配置enabled和商品。已依据本地原始type 42/43主数据加入六档商品：Android rtd_item_10000/10010/10020/10030/10040/10050，分别发放1/6/12/30/60/85水晶；iOS对应jp.co.acquire.rtd_前缀也可结算。原local.crystals.*测试商品继续兼容。

新增simulate_purchase，请求product_id、transaction_id（稳定唯一），共同ver=2.4.0及会话沿用原协议。直接发放配置的paid_point/free_paid_point，维护total_paid_point，不连接Google、Apple或任何支付渠道。payment_total不增加真实消费金额。账号内事务编号持久化，重启和重试不重复发放；重复编号换商品拒绝。重试返回当前余额，不能恢复已经花掉的水晶。

原google_play_bill_begin/app_store_purchase_begin对已配置商品返回成功空数组，不发奖；google_play_bill_point接受本地JSON signedData，字段productId/orderId；app_store_purchase_point接受Base64本地JSON encoded_receipt，字段product_id/transaction_id。这些是模拟协议，不验证真实平台凭据、不接真实支付；未知商品和非本地格式拒绝。签名和收据字段在诊断日志脱敏。

## 客户端接通

用户提供的原APK现位于相邻RTD_CLIENT的docs目录。通过REA静态检查StoreManager及购买协程，确认原商城请求begin后调用GoogleIAB.purchaseProduct，回调成功后还依赖queryInventory/consumeProduct。客户端已新增RTDLocalStore和LocalStorePatch，商品取原本地主数据，显示SIM和零价格，初始化、购买、消耗均不调用平台SDK；仍经原GooglePlayBillPoint上报本地凭据，由本服务结算余额。凭据先持久化，失败／重启保持同一orderId，服务端幂等避免重复到账。详细证据、验证与设备限制见客户端docs/模拟购买流程.md。

备份检查同步兼容schema 3及奖励批次表，避免新迁移后无法备份。

验证：原始六档商品begin／结算／重复结算、Apple本地凭据、花费后的重放、批量发奖原子性、NPC排除、备份还原后的发奖去重均通过；管理HTTP验证未认证401、首次201、重试200及客户端礼物箱领取。前端Node测试13项通过。最终Python全量265项，58失败／1错误，与改动前基线58失败／1错误一致（既有管理认证假设、关卡／大小写断言及缺少PIL），未声称全量通过。

本次只修改开发代码和临时测试数据库，未向生产玩家发放奖励、未部署生产。
