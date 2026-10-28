# 原保存点恢复的原生诊断

新计划native-restored-battle沿用原36b517db客户端和22合同采集器，不改APK/业务代码。前轮普通战斗及辅助SIG11正例的限制见[NATIVE_BATTLE_EXIT](NATIVE_BATTLE_EXIT.md)。本轮只采一个原保存点恢复样本，不自动重启。

## 原入场与正常关闭检查点

从native-battle-exit-20261027完整SQLite一致性备份到native-restored-battle-20261027，完整SQL dump和全六业务态相同；源文件SHA b532b89e315e974d6e1be31bb8489abfc0071aec5bf68efec56529ee334e652f保持。新API18766/PID23064/run-id native-restored-battle-v1/experimental=1，启动后六态相同。

原MCP flow20261027-212956/PID26584，依原auth_user→get_helpers→get_level_master→form_units→order_quest，全部4096。原关11000入场一次，request8a3522027c484475a58fd27c1caa7fc4，run4b2a1b39147a472080ecd4b5591ed4bb，原3AP消耗后25；88run/62receipt，只有新增active，无clear。完整原入场态（含冻结敌人/掉落/属性/事件/伙伴/队伍/主表hash）及六态审计通过，restoreEnabled1/controlsUnlocked，单位113/115、五队保持。

请求日志按既有安全政策把token替换为redacted；检查了持久token为未完成/未废弃的新UUID，并将在恢复中核对保持，不称与日志中不可见的原token逐字相同。NPC伙伴last_play_date按入场原时间重算，不按审计执行时当前时间生成。ID请求为原字符串形式，规范化数字比较。

随后由Android MCP正常terminate_app。等待原包装器finally，未杀包装器；已验证无游戏PID，安装base.apk恢复原1e95f5a91c6d3ead09c7f5462ace6238deda87392621f07758c5dc7439d784ec。关闭前后全六业务态完全相同，仍是上述active run/88run/62receipt，没有凭关闭写入胜利或清除进度。

## 后续观测边界

同36候选由原包装器重新启动为PID4014/start_ticks8529181/boot823aea7e-3168-4a17-949f-4967fedea7be，安装SHA与原入场相同。全六态在启动后与关闭时完全相同。REA6.7.0/Frida17.23.2使用b0f9636版采集适配器，先attachment-validated/native-ready，再由原MCP控制器执行恢复。启动到attach前仍未覆盖；注入会改变时序，不能由未复现排除缺陷。

## 实际恢复与结算

原flow20261027-214223在21:43:13输入原3004恢复入口，get_quest_info成功；中途快照保留同一active run与持久token、88场62回执，体力自然恢复25→26，无新order。原地图/战斗继续，21:47进入GameStateGameClear和MMResult，21:48:34返回MainMenu/mode100/SELECT_AREA，无Continue。没有写地图、HP、Soul、胜利或服务端战斗状态。

完整六态verify_victory通过：仅一个原order、原run4b2a1b39147a472080ecd4b5591ed4bb、一个clear请求28e3d92fc43f4a2fa535d8d7023bcc2d及唯一回执，累计88场63回执。原3AP只扣一次，按原请求时间自然恢复后26。库存113→115/容量115，原五队完整一致；原结果之后get_units→login各一次，无重复结算。其他五账号、rev32配置、源QA与八个受保护文件均保持。此轮继续使用已标注的本地必掉书/属性奖励夹具，不称历史掉率。

十分钟实际窗口为UTC13:38:43.797–13:48:44.364，覆盖原恢复输入至完整返回。完整REA队列只有native-ready/native-expired两个消息，无native-exception、truncation或工具错误；原unload/close完成，结束时仍为同PID。采集脚本SHA199134ce9e811290b47358e7ce737174eca711aeb6703ce6c2cde4e515589f29保持。22合同测试通过；没有新增生产代码、APK或业务变更。未捕获原SIG11故障地址，不宣称根因修复。

一次审计提前于驱动写出result.json启动而失败，原失败日志/当时快照保留；驱动完成后重新审计通过，不把早期失败抹去。证据冻结在analysis/android/flow-runs/native-restored-battle-20261027/evidence/execution，含原流、全快照、原始采集、只读审计与hash清单；整轮独立审查另记录，不能把未审查状态提前标记为已审。

唯一整轮审查C0/I0/新M0；153文件hash、全六态原结算和原入场由审查者独立复核，22 Node通过。20项边界全部接受、旧九Minor保持，见[全部裁定](../reviews/2026-10-27-native-restored-battle-review.md)。未修改生产代码，无C/I修复和复审。关闭工作目录按既有自动清理拒绝仅归档保留，不重试删除。
