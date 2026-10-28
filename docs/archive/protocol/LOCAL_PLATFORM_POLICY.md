# 离线平台策略

用户明确排除支付/充值。原平台支付API不开发，原支付入口不作为可用功能，不伪造支付记录或凭据。现有本地水晶/FP的消费和存储独立工作。

local-api派生客户端的MMShop.OnClickReview及OnClickNoahOffer只显示原Dialog直接文本：LOCAL MODE，评价和广告奖励不可用，货币没有变化；使用原303关闭流程。MMQuest.SetEnableInductionButton强制false，关闭分类3000外部商店推广。原APK/DLL不变，其他构建模式不应用本补丁。第三方广告入口原本隐藏时不强制开启。

不伪造review_bonus已领取或bonus_flags已访问，不虚构推广礼物。post_bonus与post_review_present仍未实现，不能把本地入口禁用称为原奖励协议恢复。原日志奖励/礼物/挑战不依赖它们。

REA parent ev_f4bbceb7c6c86e1b3124ca39f5a51cf5e65b979deadefcc533aaf3f9eb9b20a3，6类型匹配，metadata完整，#US两处terminal flag异常。原DLL SHA c83aea19...63ecc保持。派生APK SHA5903f44ae23cffb7c0ac443f9e3da3a1fce2e0d97b804d044e738264ce1c3685。

契约验证：`. ./enter-env.ps1` 后 `dotnet run --project analysis/TracePatcher -- verify-local-platform analysis/android/Assembly-CSharp-trace.dll`。旧派生DLL先失败，重建后通过。独立审查无发现，独立81服务端测试通过，最终25工具0.658秒。

实机flow20261025-223007：open-local-review-notice→confirm-local-platform-notice→return-after-platform-notice，全部MCP自动、driver exit0。原303提示视觉检查通过。前后完整存档相同SHA4b752db0ac0297ee8e70fdbca5eaef69d91ced364d9c606bb13d607a095522d2；零post_bonus/post_review_present请求。证据local-platform-policy-20261025/verified.json。
