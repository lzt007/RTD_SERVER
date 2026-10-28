# 协议静态索引

生成：`analysis/build_protocol_index.py`。47项地址，不代表全部联网面或全部契约已确认。
完整构造代码、响应消费分支、DTO嵌套源码和来源哈希见 index.json。调用位置是静态候选，未证明运行可达。

| 操作 | PHP序号 | 入口 | 构造器 | DTO数量 | 响应分支 |
|---|---:|---|---|---:|---:|
| create_user | 1 | CreateUUID:521 | ResponseCoroutine_CreateUser | 7 | 1 |
| auth_user | 2 | ResponseCoroutine_Authorize:2044 | ResponseCoroutine_Authorize | 6 | 1 |
| login | 3 | Login:531 | CreateRequest_Login | 7 | 1 |
| get_friends | 4 | GetFriends:970 | CreateRequest_Common | 8 | 1 |
| send_friend_request | 5 | SendFriendRequest:1007 | CreateRequest_SendFriendRequest | 2 | 1 |
| accept_friend_request | 6 | AcceptFriendRequest:1031 | CreateRequest_AcceptFriendRequest | 4 | 1 |
| delete_friend | 7 | DeleteFriend:1054 | CreateRequest_DeleteFriend | 3 | 1 |
| get_master | 8 | Sequence_GetMasterDB:1644, GetMasterDBHash:1781 | CreateRequest_GetMasterDB, CreateRequest_GetMasterDBHash | 6 | 1 |
| get_helpers | 9 | GetHelpers:957 | CreateRequest_Common | 2 | 1 |
| order_quest | 10 | Coroutine_OrderQuest:1258 | CreateRequest_OrderQuest | 5 | 1 |
| clear_quest | 11 | QuestClear:1344 | CreateRequest_QuestClear | 7 | 1 |
| continue_quest | 12 | ContinueQuest:1465 | CreateRequest_ContinueQuest | 1 | 1 |
| get_units | 13 | GetUnits:734 | CreateRequest_Common | 9 | 1 |
| form_units | 14 | FormUnit:765, FormUnits:804 | CreateRequest_FormUnit, CreateRequest_FormUnits | 6 | 1 |
| compose_unit | 15 | ComposeUnit:848 | CreateRequest_ComposeUnit | 4 | 1 |
| evolve_unit | 16 | EvolveUnit:874 | CreateRequest_EvolveUnit | 3 | 1 |
| sale_unit | 17 | SaleUnit:825 | CreateRequest_SaleUnit | 4 | 1 |
| get_shop_list | 18 |  |  | 0 | 1 |
| buy_recover_ap | 19 | BuyActionPoint:1491 | CreateRequest_Common | 1 | 1 |
| buy_max_unit | 20 | BuyMaxUnit:1504 | CreateRequest_BuyMaxUnit | 1 | 1 |
| buy_max_friend | 21 | BuyMaxFriend:1527 | CreateRequest_BuyMaxFriend | 1 | 1 |
| buy_gacha | 22 | PlayNormalGacha:1550, PlayRareGacha:1593 | CreateRequest_NormalGacha, CreateRequest_RareGacha | 10 | 1 |
| get_presents | 23 | GetPresents:1186 | CreateRequest_Common | 2 | 1 |
| send_present | 24 | SendPresent:1199 | CreateRequest_SendPresent | 1 | 1 |
| open_present | 25 | OpenPresent:1225 | CreateRequest_OpenPresent | 12 | 1 |
| app_store_purchase_point | 26 | AppStorePurchasePoint:1077 | CreateRequest_AppStorePurchasePoint | 2 | 1 |
| save_tutorial_flags | 27 |  |  | 0 | 1 |
| accept_invite_usercode | 28 |  |  | 0 | 1 |
| select_user_code | 29 | SearchFriend:983 | CreateRequest_SearchFriend | 2 | 1 |
| get_level_master | 30 | _getLevelDataMasterAll:1675, _getLevelDataMaster:1733 | CreateRequest_GetLevelDataMasterAll, CreateRequest_GetLevelDataMaster | 5 | 1 |
| get_quest_info | 31 | GetQuestInfo:1321 | CreateRequest_GetQuestInfo | 4 | 1 |
| app_store_purchase_begin | 32 | AppStorePurchaseBegin:1132 | CreateRequest_AppStorePurchaseBegin | 2 | 1 |
| google_play_bill_begin | 33 | GooglePlayBillBegin:1159 | CreateRequest_GooglePlayBillBegin | 2 | 1 |
| google_play_bill_point | 34 | GooglePlayBillPoint:1105 | CreateRequest_GooglePlayBillPoint | 2 | 1 |
| post_review_present | 35 | PostReviewPresent:1897 | CreateRequest_ReviewBonus | 2 | 1 |
| sp_compose_unit | 36 | SpComposeUnit:902 | CreateRequest_SpComposeUnit | 3 | 1 |
| save_local_flags | 37 | SaveLocalFlags:567 | CreateRequest_SaveLocalFlags | 4 | 1 |
| post_quest_challenge_reward | 38 | PostQuestChallengeReward:1920 | CreateRequest_PostQuestChallengeReward | 1 | 1 |
| clear_quest2 | 39 | QuestClear2:1390 | CreateRequest_QuestClear2 | 8 | 1 |
| make_password | 40 | MakePassword:1944 | CreateRequest_MakePassword | 4 | 1 |
| move_save_data | 41 | MoveSaveData:1963 | CreateRequest_MoveSaveData | 4 | 1 |
| save_unit_favorite_flags | 42 | DiffFavoriteFlag:588 | CreateRequest_DiffFavoriteFlag | 2 | 1 |
| change_user_name | 43 | ChangeUserName:1986 | CreateRequest_ChangeUserName | 0 | 1 |
| ultimate_evolve | 44 | UltimateEvolve:928 | CreateRequest_UltimateEvolve | 3 | 1 |
| save_quest_new_flags | 45 | SaveQuestNewFlagsAll:2010 | CreateRequest_SaveQuestNewFlagsAll | 5 | 1 |
| post_bonus | 46 | PostBonus:3289 | CreateRequest_PostBonus | 3 | 1 |
| buy_gacha_special | 47 | PlayNormalGacha_10:1573 | CreateRequest_NormalGacha_10 | 11 | 1 |
