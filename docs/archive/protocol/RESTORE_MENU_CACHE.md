# 恢复战斗后的菜单缓存

> 当前验收版本：final36b517dbf73ff3032a3c842c3761666e36fb271980c3e6474a4b4eee2eb719e3，helper70330ca6，managed11ff2b64，featurev2，四hook。唯一审查三项Important均同轮TDD修复；225服务端/189Android/33恢复C#/15原C#/4资源GREEN。含书恢复flow200350及同PID26584下一场flow201038都真实胜利且全六态通过；107→109→111单位/五队，恢复后原GetUnits/Login各一次，下一普通结算无额外同步。旧版和失败样本下文按历史保留。原生signal11未定位，另行继续，不宣称根治。

2026-10-27：修复对象是原 TitleMenu 恢复战斗时生成的临时单位列表和六槽队伍。服务器的完整单位、五组五槽队伍不改；不能通过放宽 form_units 校验把临时战斗数据覆盖到存档。

候选从已验收 input9230481c 派生，仅在 TitleMenu.Start/Update、MMResult.Update 加三处受校验 hook，另加 RTDRestoreCache.dll。原恢复构造、战斗计算、native 输入补丁、DEX、只读 RTDFlow 观测器保持。Cecil 会重排元数据 token，不宣称托管 DLL 原始字节不变；验证的是三个指定方法外的指令语义、类型/字段/方法布局不变，以及 APK 其他成员内容和 ZIP 元数据不变。

恢复标记只在原恢复分支创建 PartyInfo 时设置。最后一层成功结算、MMResult mode1001 才暂缓原菜单切换，串行执行原 GetUnits→Login。GetUnits 必须得到完整单位、五组五槽及有效活动队长，Login 必须成功；然后允许原切换。中间层、抽卡和未标记普通结果不启动此链。代次和 owner 绑定防止重复请求及失效后的后续 Login/菜单；已经启动的原请求会排空以释放 ComManager 序列锁。失败阻止切换、不追加自定义重试；原错误处理保持。

构建入口 `build-rtd-input-client.ps1` 默认生成独立的 `analysis/android/rtd-local-api-restored.apk`。精确父 APK/manifest 在 `analysis/android/client-history/9230481c02de3da40bc777f58f423b0f646f880f6720244576b1e6dcd3d71bce/`，历史 base2e09 和原件不能覆盖。仅在正常终止旧客户端、wrapper 恢复安装原件、持有输入锁且候选来源核验后提升默认候选。打包发布普通异常会回滚 APK/manifest 对，不提供跨进程崩溃/磁盘故障的双文件原子性保证。

本轮候选 SHA256 `5552773d609bfcd7bba26d62d97dbe30105d5c345ef1d06294061dac3b93f289`，修复 DLL `5d3eabd5b17830ed606d4f09b31ebeb373fdeebebd7c4425fc459a359e62118d`，helper `f2ba3babdaecb54fa7d4dcb113b926bff45a20af1f74414a585bcdbc37fecc1a`；manifest 标记 `post-restore-menu-cache-v1` 并保留真实 base/parent 链。

实测使用完整六账号的新 QA `analysis/android/flow-runs/restore-menu-cache-20261027/test.sqlite3`，源积分 QA、正式库和原件保持。继承的 qa-attribute-11000 空掉落/attribute_exp5000 是明确的本地 QA 配置，不是历史原掉率。原账号104/105容量不足以完成两次验证，先通过原商店消耗一颗已有免费水晶：3→2、容量105→110；其余完整状态精确不变，无支付或直接改档。

冷登录 flow183329/PID16282 全六态不变，60秒13帧被动观察仅证明窗口内仍运行。原入场 flow183830 后正常 MCP 终止，wrapper 恢复安装原 APK1e95。重新启动 PID17848、原恢复 flow184837 同一场真实胜利，客户端临时3单位最终恢复105单位和原五组队伍；post-clear 恰好 GetUnits、Login 各一次，单入场/唯一回执/体力及全六态审计通过。Login 本次无每日、助战或图鉴额外变化；不据此认为 Login 永远无副作用。

同 PID17848 下一次原入场 flow185711 也真实胜利：105→106单位，五队保持；post-clear 无 GetUnits/Login，单场唯一回执/体力与全六态精确审计通过。原入场、恢复胜利、同进程下一场均由 MCP 驱动，未注入战斗结果。证据归档至该 QA 的 evidence 目录；整增量审查记录待最终报告。

边界：有界成功不代表旧启动故障根治。恢复后败北/撤退不经过成功结果门，本轮尚未实际验收；静态路径显示它可能直接回 MainMenu 并由原下载链刷新，但恢复标记可能留到后续成功结果，造成一次额外同步。不得将本次胜利路径验收扩大为这些分支已修复。

## 唯一审查后的修复轮（进行中）

审查C0/I3/M0：原掉落书会设置RESULT_MODE，因此初版排除标志错误；瞬态结果页被销毁会停止原请求外层迭代器而遗留序列锁；败退直接返回MAIN_MENU会遗留标记。这三项均接受Important，原先败退限制的说明不再作为排除理由。

修复版改为原持久ComManager调度同步及原请求外层协程；MMResult成功边界不再根据书展示旗排除；新增第四处GameManager.StartTitleMenu入口hook，只读原ClientData.m_BattleWin，false清标记，true保留。31项合同已先RED后GREEN，含两种书、两种在途owner销毁、撤退/拒绝继续/胜利保留及精确四hook。测试是独立自有桩，不冒充真实网络错误或真实败退复现。

修复候选SHA256 `33a632b012189db036640bfb92b109835362e4218cfd58dd0a4411062e92e64d`，helper `faff2119a2026fe9bb7b272135d1da7e576af5ae1f15a6e5743307aecfb4fc4d`，managed `11ff2b6483ac0754c64dceef3fd0d71e599340ae1f9dafa582cae90cc35bda0b`，功能v2。仍从精确923父候选派生；旧555 APK/manifest已内容寻址保留，原件/父/历史base及native/DEX/observer不改。

新的完整六账号book QA为restore-menu-cache-book-20261027，从已审83场/58回执/rev30克隆。经原后台仅把11000的Boss drop21096设为已有单位20000、等级1、权重1、空权重0，配置rev31；明确本地必掉书回归夹具，不是历史掉率。所有玩家/场次/回执不变。原商店容量110和已有免费水晶2保持；冷登录flow192718全六态审计通过。新的含书恢复胜利验收正在运行，不预先宣布成功。

原审查283文件证据及index保持原样；修复轮另存evidence/review-fix及独立索引，不覆盖已审原证据。全部报告/裁定见../reviews/2026-10-27-restore-menu-cache-review.md；一次Important修复轮结束后不另派复审。

修复轮证据更正：初次rev31把掉落配置到99号特殊敌人（21096），原恢复flow193319虽全六态通过，但clear.units为空，仅106→107，不能作为含书证明；原DropManager以enemy_id0查Boss。rev32改为必经Boss0/21000，99行恢复空掉落，完整业务状态不变；原商店扩容110→115、已有免费水晶2→1已全六态审计（flow194122）。错误样本和配置前后档案保留。

I2同一修复轮再补两项：Unity对象销毁但Title.Start尚未Reset的间隙，原引用仍非CLR null；Current须用Unity owner!=null阻止后续Login/菜单。两项先RED31/33后GREEN33/33，仍由持久ComManager排空已启动原请求。最终helper70330ca6、managed11ff2b64、候选36b517db，featurev2。候选33已存内容寻址历史；原未结算入场不重发。

最终候选flow195345/PID25634在战斗中途退出，completed=false；原Zygote系统行10-27 11:56:20.646确认signal11，已保存，未产生新tombstone/可定位堆栈。Chrome构建指纹不是原因证据。仍85场/59回执/原活动战斗，不将失败样本写成胜利。相同36候选仅做一次有被动出生标识记录的诊断恢复；不宣称原生退出根治。最终全门225server/189Android/33C#已绿；实际含书验收仍待完成。

最终实际证据：诊断恢复flow200350仍为原入场061b6a1d，期间中断控制器与signal11均未新入场/重复扣费；原clear09731242提交单位20000等级1并成功4096，unique receipt/full six states/AP均精确。下一flow201038的clear de0a1bd1同样提交原书，109→111，全态精确且post-clear无同步。最终86场/61回执/rev32、活动积分100002:5、容量115/免费水晶1；与正式库无关。被动120秒25帧绑定PID26584/start7956283/boot823aea7e，仅有界成功。三项审查修复已关闭，原生退出问题仍继续诊断。
