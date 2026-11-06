# 原版客户端放弃副本与服务端记录生命周期

## 原客户端证据与问题

分析目标：原 `Assembly-CSharp.dll`，SHA256 `cd8969401672485c95dbc8336864bfe54a1bfce242f4048b32341a2ab0953ac2`，MVID `81502538-516d-4802-bbff-d4f363e3388d`。

`BattleMenuManager.Update` 的确认放弃分支（IL_04e8～04f5）设置 `ClientData.m_BattleWin=false` 并进入 `GameStateRetire=13`。`GameStatus` 随后关闭确认框、FadeOut，整理本地结果并回主菜单。

`MainMenu.Start` 在非胜利路径清除本机恢复存档。`MainMenu.Update` 的 IL_036c～03a3 根据 `m_BattleWin` 分流：胜利进入菜单44（RESULT），非胜利进入菜单46（LOGIN）。`MMResult` 的 `QuestClear2` 调用仅属于前者；不能把弃权解释为 `clear_quest2` 的零奖励列表。原 `RequestClearQuest2.Quest` 没有 quest_status 字段。

`MMLogin` 仅在 `ClientData.IsNeedLogin()` 为真时发送 Login。原 `CreateRequest_Login` 只写版本、设备、时间等信息，没有明确弃权字段；`CreateRequest_GetQuestInfo` 也没有清理标记。因此非胜利退场可能没有发送任何专用的副本终止请求，服务端仍保留 active run。用 login 自动清战斗会混淆正常重登恢复，不能作为可靠修复。

启动恢复提示还依赖本机 RESTORE_H / RESTORE 与版本校验，并非单由服务端 quest_status 决定。

REA 静态证据 summary：`ev_5f6385f7e589e0bc7582245420c5a26aa94af62de9c6b1632cf35abdc1e7e3bd`；完整 retained parent：`ev_e0befbc935051e17cc899bde965f79f689f43460d178befb864f5e3a8e57cde1`。选择覆盖 MainMenu、MMLogin、BattleMenuManager、GameStatus、ComManager 与 RequestClearQuest2。嵌套 Quest 类型的 `+` 名称未匹配，字段结论另核原 IL，不把未匹配当作类型不存在。

## 修正后的判断

原版客户端是兼容依据，不新增 abandon_quest，也不修改确认放弃流程。

原版 GetQuestInfo 调用集中在 TitleMenu 的教程和战斗恢复路径；战斗恢复先由本机 CheckGameRestoreActive 门控，再检查服务端 IsBattle。主动放弃清除本机恢复存档，因此服务端尚有 pending 记录不等于客户端仍在战斗内。原版每次新 OrderQuest 生成新 UUID。

当前服务端已有处理下一次新订单的机制：新 UUID 且 retry=0，在完整验证新订单后原子地将旧 run 标为 abandoned，再创建新 run；旧 run 不结算、不退体力。保留 pending 记录也让真正断线的客户端可以按原流程恢复。不应在 login 或 auth_user 中无条件删除。

已证实的错误是本地服务端使用 pending battle 作为抽卡和恢复体力的全局禁用条件。应移除这些不符合原客户端菜单流程的限制，同时保持订单身份、重试幂等、冻结队伍和结算校验。静态证据不能还原官方服务端数据库实现；上述是与原客户端行为兼容的本地生命周期方案。

新增弃权扩展的路由、模块和测试已撤回；未部署到生产，未修改客户端。本轮未再次清除玩家记录或重启服务。
