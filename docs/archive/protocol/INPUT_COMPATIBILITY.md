# 旧 Unity 输入兼容

2026-10-27，原API28模拟器，ARMv7客户端2.4.0。原窗口触摸到达Android但游戏不响应；同一进程、同一坐标的真实MotionEvent对照确认source0x5002不响应、0x1002响应。

原native补丁修改原生assets/libs/armeabi-v7a/libunity.so的两个getSource读取调用（0x2e4048、0x2e4178）。32字节ARM跳板仍调用原Android函数，只把精确0x5002返回值改为0x1002，保留其他来源、事件参数和生命周期。此纯native变体的原Java/DLL/资源不变；末尾新增只读observer变体另行列明。不升级Unity、不调用游戏按钮或改写战斗。

选择这一边界是因为实际Activity为NativeActivity，Java UnityPlayer.onTouchEvent先被j门控提前返回；最初Java候选登录可用但点击实验失败，已弃用。原生第一版移动程序头表被旧Unity资产加载器拒绝，新LOAD变体在加载中退出，均未产生API/存档变化，不能记验收成功。最终利用原RX/RW之间32768字节虚拟空隙：文件插入对齐空间、RX延长32、后部文件偏移相应移动；原虚拟地址、两个LOAD、GNU_STACK、动态/异常节及全部原节内容保留，只有两个4字节输入调用跳转改变。失败实验保留日志，不把重试当根因修复。

## 构建与运行

当前完整候选用build-rtd-input-client.ps1（末尾详述）；下面保留纯native诊断构建，该命令会生成不含恢复提示观测的旧候选。纯native构建仅需现有Python标准库；测试依赖已安装到tools/python-native，版本见analysis/android/input-test-requirements.txt。未知/重复补丁输入及覆盖已知原APK/基线客户端会拒绝。构建逐ZIP条目检查，仅上述原生库内容变化。

```powershell
. ./enter-env.ps1
python analysis/android/build_input_compatibility.py
python -m unittest discover -s analysis/android -p test_input_compatibility.py
powershell -NoProfile -ExecutionPolicy Bypass -File analysis/android/run-compatible-client.ps1 -LocalApi -InputCompatibility
```

候选为analysis/android/rtd-local-api-input.apk，显式参数要求LocalApi且先核对清单SHA；保留旧rtd-local-api.apk。沿用已有root QA替换及finally原APK恢复流程，普通APK签名因派生内容变化无效，不能宣称直接安装版。

|身份|SHA-256|
|---|---|
|原APK|1e95f5a91c6d3ead09c7f5462ace6238deda87392621f07758c5dc7439d784ec|
|基线兼容APK|2e09cbda0ff0a147925aa751bcdae7b83601a32811adc46b7ac21f9698d1c2e4|
|最终候选APK|5765baf0564dc4b9caf19a47aea1c503d98489c0f43b17f502b359db5eaa72ea|
|原资产原生库|eb8ab8714c7eda4dbf49c5f032557caba08c4eadfe02742b8337c7f184cf4724|
|候选资产原生库|43b4b4c2375877b35fe5b2a06a76ba7871e966a35f7ae08aa7935d351720d65f|
|未变DEX|7cfdbb82cf81b5ae33a07ec4ce45efca2e4120a3c3ea8484107673570b8cc067|

## 实际验收

### 常用入口（2026-10-27更新）

```powershell
# API/资源已按所选存档启动后：默认使用输入候选，终端须保持运行。
.\start-rtd-local-game.ps1
# 一键会话：不打开scrcpy，使用Android MCP到原主界面。
# 默认选server/data/rtd.sqlite3，实验内容关闭；已有API也必须匹配。
.\start-rtd-session.ps1 -NoControl -Goal main-menu
# 当前隔离QA，须明确选库和实验模式：
.\start-rtd-session.ps1 -Database analysis/android/flow-runs/content-expansion-high-level-20261026/test.sqlite3 -ExperimentalContent -NoControl -Goal main-menu
# 仅诊断旧输入行为，显式回退；不会修改或删除输入候选。
.\start-rtd-local-game.ps1 -LegacyInput
```

一键会话先只读验证本机candidate/manifest，再按原逻辑启动或复用服务；候选缺失/损坏时在启动组件前停止。启动或复用游戏后，核对单一PID、合法pm安装路径、安装APK SHA和probe-pid.txt；未就绪轮询30秒，每条ADB读取另有10秒超时，进行中的检查仍须结束后才能报错。错误包立即拒绝，不自动杀进程/换包或修正玩家存档。驱动通过`--required-client-sha256`在建立MCP连接/输入前再核对一次，同一流程内PID变化继续停止。

`-NoControl`仅省略scrcpy，操作仍由MCP；不传时保留原控制窗口。Goal默认仍account-ready，需要到主界面时明确传main-menu。显式相对`-Database`按调用者当前目录解析；`-Database`默认server/data/rtd.sqlite3，`-ExperimentalContent`默认false；运行中的API必须同时匹配路径身份和严格布尔内容模式，旧health缺字段也拒绝，且不自动停服或改存档。API未运行时明确传入绝对数据库路径，只对子进程设置实验模式并恢复父环境；连接就绪轮询窗口10秒，每次HTTP请求另限3秒，进行中的请求结束后检查截止时间。路径身份仅为规范化绝对路径SHA256，不校验数据库内容，不是身份认证；纯解析不创建目录/数据库。输入候选不自动重建，固定基线SHA不匹配时需重新分析，而非绕过门控。一键会话不复用LegacyInput进程；先正常关闭旧runner、等待原APK恢复，再启动候选。

默认入口验收：v64 PID10016由常用local-game默认启动，一键会话NoControl/Goal main-menu复用并完成flow20261027-112453。完整六账号/配置/运行/回执精确不变（AP28→28，图鉴/关卡位无变化）；随后source5002从SELECT_AREA进入ETC_MENU成功，三设置仍true，原件SHA不变。共同证据analysis/android/flow-runs/default-input-launch-20261027；独立审查记录另列。

共同证据目录analysis/android/flow-runs/input-compatibility-20261027：

- 原版同进程26286两轮来源对照；第一轮ETC_MENU不变/SELECT_AREA，第二轮原MMEtcMenu场景，均非战斗输入。
- 最终候选v60 PID361，原登录flow20261027-090133完成MainMenu；同坐标两种来源都从其他菜单进入SELECT_AREA，patched-comparison.json。
- 内核/dev/input/event1真实多点触摸序列也能切换菜单；Android观察到deviceId0/source0x5002/xPrecision30.3/yPrecision17.1/policy0x62000000，与旧原窗口路径一致，kernel-before/after/input留证。这比仅应用层注入更接近原窗口输入，但未声称已由第二人手动复核Windows鼠标。
- v60实际源0x5002点击BGM/SE/GUIDE关闭，三个本地SharedPreferences逐项false；正常终止、原APK恢复SHA核验、v61重启flow20261027-090825后原UI和偏好仍全false。随后三个均通过原UI恢复true，与初始设置一致。
- v61 PID1325的0x5002真实拖动540,1150→540,650改变原区域列表，drag-before/after/input留证。
- v60登录全六账号/配置/运行回执精确比较，仅自然AP23→25；v61设置重启仅自然AP25→26；无新图鉴位/关卡位、无单位/币/战斗历史变化。v57 Java候选登录的实际1个图鉴发现位另有原线包解释，未忽略。
- 实际候选栈映射rw-p，未授予可执行栈。7项构建/拒绝/ELF/ZIP/启动契约通过，含40次Unicorn实际ARM执行；原取源调用一次，精确来源转换、返回/栈/需保留寄存器均正确。

REA核对了原生文件身份；当前Windows原生深度provider不支持本目标，地址/指令分析来自明确标注的本地Capstone/pyelftools，不称REA反编译。任意新Unity版本/新APK不能套用固定地址；原件SHA门控会拒绝。输入修复不代表此前独立原生SIG11已被根治。

默认入口整增量审查发现并修复两项拒绝路径问题：保留已核验PID并在MCP初始化后再次确认；login-checked仅清理本次成功创建的探针，已有标记直接拒绝。修复后128 Android/179服务端/3资源/15 C#全绿，暖启动flow20261027-114947通过。驱动二次检查仍复用原20秒单命令超时，已作为第六项Deferred Minor登记；独立session_client读取为10秒。完整裁定见[入口审查](../reviews/2026-10-27-default-input-launch-review.md)。

显式存档绑定验收（2026-10-27）：原v64正常退出并核对原APK恢复后，仅重启已识别QA API为PID15096。默认目标拒绝复用QA；正确QA路径但默认实验关闭也拒绝，均无游戏请求且六账号/配置/历史精确不变。正确路径加ExperimentalContent完成flow20261027-120233（候选PID12397）；登录仅原9个请求，完整六账号/77场/52回执/rev29精确保持，AP28→28、图鉴/关卡位无变化。暖会话独立进程退出0。181服务端/133Android/3资源/15C#全绿，原件SHA保持。证据analysis/android/flow-runs/session-database-binding-20261027。

整增量审查修复相对选库基准后，从docs目录传../analysis/...实机暖启动退出0；完整134 Android/181服务端/3资源/15 C# GREEN。审查与逐项裁定见[存档绑定审查](../reviews/2026-10-27-session-database-binding-review.md)。


## 体力出售提示观测候选（2026-10-27）

历史兼容基线rtd-local-api.apk固定2e09cbda，禁止为了更新观测DLL重建或覆盖它。运行`.\build-rtd-input-client.ps1`可用原Unity引用确定性编译只读RTDFlow.dll，再将已知SHA DLL和原native输入补丁覆盖进新候选。构建失败不替换候选；未知编译输出必须重新分析，不得修改SHA门控绕过。SDK不同可能得到不同输出，应保留已验收候选用于启动。

新候选SHA256：01d0a928f2718b8db3736b74d97f3480ce092993f18f7b134abb314715ddeb03。observer固定00c24394def83fd2e45812a0a4b349c3de0e351eb0dc4086eab612479832c0e5，仅对MMUnitSell mode600选择m_ApRecDialog；无游戏行为修改。与历史基线相比ZIP只允许assets/libs/armeabi-v7a/libunity.so和assets/bin/Data/Managed/RTDFlow.dll变化，DEX及其他资源逐项保持。旧纯native候选5765baf0已单独备份。

2026-10-27好友奖励观测增量：当前候选SHA9230481c02de3da40bc777f58f423b0f646f880f6720244576b1e6dcd3d71bce，observer固定613dde3dfacad40265c51af6df6c271232d93973f9181675c676fd4130da96f9。新增只读helpCount/receivedFriendPoint；原MMLogin101提示必须与人数、实际点数、余额整除100的可抽次数全部相符才确认。manifest同时声明sale-ap-dialog-v1与helper-login-v1，出售独立Dialog、原生输入补丁和DEX保持。前一01d0候选及清单/DLL另有备份，不重建历史2e09基线。构建入口仍为build-rtd-input-client.ps1；此处构建与合同测试通过，实际验收另记好友规则。

普通出售默认恢复0；体力素材必须显式`--sale-instance ID --sale-price 1 --sale-recover-point 1 --goal main-menu`，且只在明确的隔离测试账号使用。脚本在MCP建立前验证manifest能力、ZIP唯一observer实际SHA、候选SHA及实际安装进程/PID；缺失或伪造标签拒绝输入。独立Dialog的文本金额和ok坐标与普通出售确认框分别读取，不回退到通用buttons的旧ClickOK。

原mode600仍保留旧显示面板，mode501才SetUnitListSellAfter；因此提示阶段核对真实全局库存数量、选中清空、现金、AP与原文本，关闭后回到mode100再检查目标行消失，不能把未刷新的渲染行误当存档仍拥有该单位。未知错误、无baseline、恢复量不符或进程变更均停止留证。


## 登录前已知ANR有界恢复（2026-10-27）

`start-rtd-session.ps1 -Database <明确存档> -ExperimentalContent -NoControl -Goal main-menu` 沿用原参数；默认数据库和内容模式不变。入口现在经 `analysis/android/drive_session.py` 调用原单次driver，正常只执行一次。直接使用drive_startup的行为不变，不转发战斗/消费参数到恢复器。

只有原公告关闭的MCP agent输入超时、TitleMenu2001/userId0/restoreEnabled0、同候选/探针PID、新的本次ANR和特定主线程QemuPipe→gralloc→Surface.lockCanvas→drawSoftware栈、API库绑定及完整玩家/配置/run/receipt都不变才允许一次Android MCP terminate。最多等120秒只读取证，原runner恢复原APK后按名义30秒轮询（读取可超时延长，见M1）；同一输入锁下重新启动既有runner并等待新候选/探针。第二次失败停止，不盲发点击、Back或业务请求，不重启API，不写恢复标志。其他账号原有活动战斗通过完整状态比较保留。

诊断在 `analysis/android/session-runs/<时间>/result.json`，原driver证据仍在flow-runs。不匹配/缺失报告、旧trace、错误PID/栈/时间、未知错误、候选/存档/服务身份变化均停止；这不是图形ANR根因补丁，也不涵盖候选预检前的进程退出。不要把自动恢复扩大为任意失败重启。

实机flow20261027-144904/session20261027-144903-877954单次成功，六账号全态仅自然AP9→14。第一轮预检前PID27508退出零存档变化，保留证据后另起新尝试；本轮没有自然复现已知ANR。恢复分支以旧真实ANR主线程和隔离子进程/设备边界端到端合同验证，不能称本次实机触发恢复。共同证据 `analysis/android/flow-runs/startup-anr-recovery-20261027/evidence`。原件和9230481c候选不变。


最终独立审查后的加固：启动前排除已有ANR文件，绑定boot_id与/proc start_ticks，校验设备墙钟相对单调时钟的5秒误差；文件名日历及header秒级一致。最后guard以SQLite只读data_version捕捉读期间提交，并复验安装包/探针/进程/API。任一检测变化都拒绝恢复；多进程最后观测与动作之间不具全局原子性，不应并行手工控制。完整裁定见[审查记录](../reviews/2026-10-27-startup-anr-recovery-review.md)。新增M1为Minor暂缓：原件恢复的30秒是轮询预算，逐命令10秒读可能使总等待超出，合成复现55秒；不能称硬30秒期限。最终168项Android通过，修复后暖会话一次成功/零请求，全态保持。
