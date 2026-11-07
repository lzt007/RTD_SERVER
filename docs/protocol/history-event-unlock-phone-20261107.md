# 真实手机活动积分复核（2026-11-07）

## 已核实的部署状态

同步服务端 `856e37c`、客户端 `4ecc010` 的远端排查与回放方案。实际部署的四个积分源码与仓库语义一致，API 进程在文件更新时间之后启动，健康检查为 HTTP 200、RTD-2.4.0。原修复已在运行，不另改计分公式、不重写旧战斗快照或历史余额。

读取实际部署数据库的 runtime_config revision 40：36 组、103 个开放关卡，其中 15 个关卡关联已登记积分。使用实际部署的主表、重建开关及生成器，固定随机种子重新生成，15 关均可产出正积分。原始目标、显式运营值（包括零）、原始门槛及排期保持不变。生成审计不等于真实击杀或通关。

魂之塔的该开放列表不含零积分入门关；对余额为零的新账号，这是独立的排期限制。没有据此擅自开放资源受阻关卡或降低原门槛。

## 可回放工具

- `scripts/audit_event_unlock_points.py`：必须显式指定实际部署根目录和只读数据库，运行初始化只使用临时 SQLite，避免误用开发库推断开放范围。
- `scripts/android_event_unlock_device.py`：记录安装 APK 哈希、启动、截图、已观察的点击及临时显示尺寸；测试后通过 display-restore 恢复原尺寸。
- `scripts/android_event_unlock_replay.py`：菜单、已确认文本的教程对话框、结算及重登后的关卡列表回放。
- `scripts/android_event_unlock_play.py` 与 `scripts/android/RTDInput.java`：正常选路、连线战斗和原生治疗，不写游戏字段。

教程由用户手动完成，未冒充脚本回放。后续活动操作使用 ADB 回放。手机回放读取实际截图及应用窗口边界，将游戏窗口坐标转换为屏幕坐标；不再按模拟器宽度截断。日志先在手机侧冻结再传输，避免低带宽下持续追赶新日志。原始日志、截图和设备地址保存在 ignored logs/，不得提交。

诊断 APK 保持游戏 Assembly-CSharp.dll 及其他原始 ZIP 条目不变，仅修改 RTDFlow.dll 并新增只读积分探针。Linux 构建显式从输入目录解析原 Unity 运行库，保留纯 getter、全部原辅助方法及异常区域校验。

## 验证进度

- 30 项现有积分、分层、真实历史关卡及协议回归通过。
- 9 项高分辨率、MIUI 兼容窗口、无线治疗延迟、无对应职业换盘及混色八格连线回归通过。
- 真实手机已正常通关 20710：8 分到账，清关回执 4096，存档余额 8、通关位及 run cleared 均确认，无活动战斗及冻结积分残留。完全停止并重新启动、重新登录后余额仍为 8，20711 解锁，20712 因不足 50 分保持锁定。

## 手机回放命令

设备标识只在本地设置 `RTD_TEST_SERIAL`，ADB 路径由 `RTD_ADB` 提供。先完成教程并进入对应活动列表，根据已观察的助战列表选择索引，不把账号或设备地址写入脚本。

```bash
python3 scripts/android_event_unlock_device.py --adb "$RTD_ADB" --serial "$RTD_TEST_SERIAL" --action record-points --output logs/event-unlock-phone
```

另一个终端中执行菜单、战斗及结算；每一步会校验实际观察到的界面，未知状态停止。`helper-index` 示例为已人工核对的可见 80 级助战位置，其他设备应先 inspect。

```bash
python3 scripts/android_event_unlock_replay.py --adb "$RTD_ADB" --serial "$RTD_TEST_SERIAL" --action enter-history --stop-at-list --output logs/event-unlock-phone
python3 scripts/android_event_unlock_replay.py --adb "$RTD_ADB" --serial "$RTD_TEST_SERIAL" --action quest --quest 20710 --output logs/event-unlock-phone
python3 scripts/android_event_unlock_replay.py --adb "$RTD_ADB" --serial "$RTD_TEST_SERIAL" --action helper --helper-index 1 --output logs/event-unlock-phone
python3 scripts/android_event_unlock_replay.py --adb "$RTD_ADB" --serial "$RTD_TEST_SERIAL" --action confirm --quest 20710 --output logs/event-unlock-phone
python3 -X utf8 scripts/android_event_unlock_play.py --adb "$RTD_ADB" --serial "$RTD_TEST_SERIAL" --quest 20710 --input-mode native --battle-strategy all-panels --screenshot-every 10 --use-cure --minimum-points 5 --timeout 1800 --output logs/event-unlock-phone
python3 scripts/android_event_unlock_replay.py --adb "$RTD_ADB" --serial "$RTD_TEST_SERIAL" --action stage-clear --output logs/event-unlock-phone
```

真实手机使用 stock `input swipe`／`input motionevent`，不要求运行自定义 app_process DEX。治疗使用原 Cure I，等待原弹窗 OPEN 后确认，允许无线采集延迟但不重复点击；全盘无对应职业时正常消除换盘。截图可按输入次数采样，每次选择依据、实际触摸坐标及积分变化仍记录；不能声称采样间隔内每步都有截图。

结算服务端回执及只读存档核对成功后，再执行强制停止、重新启动和登录列表检查：

```bash
python3 scripts/android_event_unlock_device.py --adb "$RTD_ADB" --serial "$RTD_TEST_SERIAL" --action relogin --output logs/event-unlock-phone
python3 scripts/android_event_unlock_replay.py --adb "$RTD_ADB" --serial "$RTD_TEST_SERIAL" --action enter-history --stop-at-list --output logs/event-unlock-phone
```

只读持久化核对使用 `scripts/audit_event_unlock_account.py`，需显式指定目标数据库、部署目录及本地 private observations 文件；输出不含玩家标识、会话或其他账号资料。旧战斗冻结数据不改写，达到门槛后仍须正常通关。

脱敏机器可读结果见 [真机验收摘要](evidence/history-event-unlock-phone-20261107.json)。最终 Boss 使用两次正常八格连线击败；并未把本次过程的全部战斗都记作八格策略，前段使用估伤选板，途中修正了回放兼容性后继续同一局。50 分门槛仍只有 49/50 隔离协议测试，本次未在手机刷到 50 分。

清理完成：恢复普通客户端，手机安装 APK 的 SHA-256 与原普通包一致；恢复原显示尺寸、停止遥测，保留账号及正常取得的 8 分。实际 API 健康检查仍为 HTTP 200、ok。
