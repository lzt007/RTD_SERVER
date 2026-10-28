# 原恢复撤退与启动前诊断

2026-10-27 实测：原始入场、正常关闭、重新启动恢复、原界面放弃、下一次原始入场已完成。唯一整轮审查C0/I2/新M1，两项Important已同轮TDD修正；全部28边界及十项延期见[审查裁定](../reviews/2026-10-27-restored-withdrawal-review.md)。不能据此宣布原生崩溃已修复。计划见../superpowers/plans/2026-10-27-restored-withdrawal.md。

用户确认11123是手动操作并授权接管。接管前完整保存实际89场63回执的旧QA、六账号业务态及设备偏好备份；没有恢复旧快照覆盖人工进度。本轮在独立restored-withdrawal-20261027使用113单位/115容量的完整六账号克隆；源native-battle-exit-20261027 SHA b532b89e315e974d6e1be31bb8489abfc0071aec5bf68efec56529ee334e652f、87场62回执及正式库保持。

## 原界面证据

- flow20261027-230931，PID11258：11000原始入场，run d147df718a0048ebbe832829e20d25fe，唯一order，3AP，88场62回执。正常关闭后业务态不变，包装器恢复原APK。
- flow20261027-233614，PID13453/birth9234103/boot823aea7e-3168-4a17-949f-4967fedea7be：原恢复按钮进入同一场，临时三单位保持同一run/token，无新order。MCP BACK与截图确认的“はい”产生GameStateRetire，随后原MainMenu LOGIN恢复113单位、五队，restoreEnabled=0。
- 撤退不产生clear、Continue、奖励或回执；服务端旧run暂时仍active。完整六态仅自然体力恢复至29，未虚构退款或服务端撤退协议。
- flow20261027-234320，同PID：原始下一次order 86deb8f959ce449caa25de43e4f4eda6，run3fc631b5d0ac4c808c5747b7df5b2c91。恰好废弃旧run/token，新入场扣3AP至26；89场62回执，113单位/五队、其他五账号和配置保持。当前停在新战斗可操作状态，未强行胜利或结算。

四个只读审计分别验证入场、撤退、下次入场及原生窗口；完整业务态、原始请求及实际observer序列相互核对。请求日志token原本脱敏，仅证明持久化token的新鲜性与延续，不声称逐包token一致。

## 启动诊断改动

新工具native_startup_capture.mjs复用原native_capture.mjs；初版复用原native_faults.js，审查后修正只读脚本的就绪握手，不修改APK、Unity或业务协议。通过REA6.7.0同一paused-spawn会话，绑定PID/birth/boot、加载只读脚本、确认native-ready与身份后才显式resume；保存有界消息、退出原因、卸载和close结果。关闭暂停spawn本身可能恢复执行，清理失败明确保留，不能保证失败路径绝不执行客户端。

REA构造器注入局部deviceManager代理，仅将固定RTD/模拟器的spawn选为com.prime31.UnityPlayerNativeActivity，绑定原生方法接收者并拒绝其他设备、包及选项。没有修改已安装REA或Frida。默认package launcher会进入旧奖励插件，不等价于原Unity入口。

包装器显式启用：`-LocalApi -InputCompatibility -NativeStartupOutput <全新绝对路径> -ReaRoot <REA6.7.0绝对目录>`。新增严格参数绑定，默认启动路径保持。窗口内输入驱动所用probe-pid须在实际ready/resume及实时身份/SHA核对后发布；包装器本身到采集结束才写普通probe文件。

实际Unity窗口为UTC15:35:49.923–15:45:50.496，覆盖原恢复、放弃及下次入场；native-ready/expired、无异常或截断，卸载/close成功。注入和spawn改变时序，不覆盖所有最早指令，ARM翻译也可能限制栈信息；单次未复现不是SIG11根因修复。

## 分离保留的失败与执行者错误

1. 无注入启动PID11983：UTC15:12:18.475启动，15:12:21.964被Zygote记为signal11，发生在附加前。无新tombstone或可定位PC；旧tombstone09属于13:12辅助sleep，不能当作游戏崩溃栈。原件正常恢复，无请求/六态变化。
2. 默认package paused-spawn PID12966：CARewardPluginActivity内MODE_WORLD_READABLE旧API触发Java SecurityException，AndroidRuntime发SIG9；不是上例SIG11。保留实际ba6bdf7工具源码和原始记录后，才限定Unity Activity。宿主/来宾时钟未经独立校准，不能直接用绝对时间推断精确因果。
3. 首次负向包装器RED测试隔离失误：旧脚本忽略未知参数，意外启动legacy候选12423且测试超时杀掉其包装器。无游戏输入、请求或六态变化；正常MCP关闭已确认的测试进程，仅用SHA核验的备份恢复原APK。保留错误记录；后续测试在同一子进程用抛错adb/node拦截设备副作用，并增加CmdletBinding回归。不能把此误启动作为有意SIG11复现，也不声称客户端本地文件绝无读写。

审查前45项Node契约（新23+旧22）和189项Android测试通过。审查修正新增安装失败、超时器失败、延迟native-error、旧ready与空参数回归；56项中11项先失败，修正后56全通过，Android189项重跑127.927秒通过。RED、隔离RED、handoff/参数/Activity回归及失败样本均保留。其他历史服务端/C#计数不当作本轮重跑结果。

原十分钟样本使用旧SHA199134ce9e811290b47358e7ce737174eca711aeb6703ce6c2cde4e515589f29，原ready早于处理器安装；虽实际收到expired且无native-error，不能追认其采用修正握手。新SHA11f6afe81f3629143561dbfac6ad6b1f6eeae1cbdabbefe3addcbe0e06df1bfc只在处理器/超时器均安装后发handler_installed=true，新门拒绝native-error并在最后身份等待后复核队列。修正后三秒同PID13453只读附加实际新握手/卸载close、六态不变，未重放启动、撤退或SIG11。

证据：analysis/android/flow-runs/restored-withdrawal-20261027/evidence下pre-attach-failure、default-launcher-failure、execution、verification及closing独立冻结索引。只验证本轮原样本，败北/续关与其他协议仍需独立确定实际缺口。关闭scratch仅归档保留，不重试已被策略拒绝的删除。
