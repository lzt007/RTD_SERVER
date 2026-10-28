> 审查后范围说明：C0/I0/新M1，原生窗口不覆盖下一order与battle-ready尾段；业务验收独立成立。详见[完整裁定](../reviews/2026-10-28-restored-defeat-continue-review.md)。下文为审查前原记录，较宽窗口表述已在裁定中明确限定。

# 原存档败北、续关与再次入场验收（2026-10-28）

候选36b517db保持原APK业务逻辑。本轮只改诊断工具：增加限定Android9 x86 ARM翻译库的信号链入口记录器；没有修改Unity、战斗结果或通信协议。唯一整体验证审查尚未执行，不宣称SIG11已修复。

## 夹具与人工进度

人工11123进度保留在native-restored-battle-20261027，SHA7677adbf；上一轮89场62回执完整库及偏好另备份。新QA restored-defeat-continue-20261028从完整六账号113单位/115容量源b532b89e克隆，唯一显式差异为现有三个Lv1单位组成第一队，其余四队、单位、另外五账号与配置不变；使用原有1颗免费水晶，未增加货币或改写HP/敌人/结果。API18766/PID19824/run-id restored-defeat-continue-v1，experimental=1。

## 实际原界面序列

1. flow20261028-002048/PID18040：原11000入场，run63e522f539304c4287697f9357e3b3e1，order8544f01a43754af4b8e13d8c6e24bf67，扣3AP至26，88场62回执。原控制解锁并保存后正常关闭。
2. flow20261028-004159/PID20697：原3004恢复相同run及持久令牌，临时三单位，经原面板自然败北GameStateGameOver，再原ContinueYes。唯一continue_quest请求f735e8fc8f0b4e38b59aec17f1744458，floor0/count1/retry0/4096，免费水晶1→0、续关0→1，原控制重新解锁。无新order、结算奖励或operation_receipt；完整六态只有该预期差异及自然体力恢复。正常关闭后业务态保持。
3. flow20261028-004634/PID22210/birth9656696/boot823aea7e-3168-4a17-949f-4967fedea7be：原3004双方续关数均为1，余额0。自然再次败北，原ContinueNo返回MainMenu100/SELECT_AREA，113单位与五队恢复，restoreEnabled=0。无重复continue、新order、clear、奖励或回执，旧run暂时active。
4. flow20261028-005526/同PID：原下一次入场，order07b8b070f54d42e69828e0f7f9bcd520，run aed919613cf941ff9b69df3da460ed96；精确废弃旧run及令牌，唯一3AP扣费29→26，89场62回执。控制解锁、restoreEnabled=1；停止输入并保留新战斗。原旧battle_continue_receipt保留旧run_id，不能作为新run的续关幂等凭据。

四段只读审计逐字段比较完整六账号、配置、run及回执，并与实际原UI序列/请求时间体力对照。请求token已脱敏，只证明数据库令牌延续及新鲜性，不声称原始包token相等。API日志无响应体，4096及持久态不能替代原始响应包。全SQLite一致备份SHA1ebfb82b2deaf06e45dc16d5b53e720bebb4c1650ea6fea3d05c6e7153ca94cf；正式库、原件、三旧QA及人工进度均核对未变。

## 实际启动失败与诊断范围

原计划第二次启动PID19812/birth9537571在新11f6处理器ready之后，设备UTC16:26:25.757被Zygote报告SIG11；没有native-exception或新tombstone，无恢复输入、请求或六态变化。失败77文件单独冻结，未按成功样本覆盖。执行者曾在资格命令失败后仍启动依赖驱动，驱动自己的PID门阻止了全部输入；flow002640保留。后续改为同一PowerShell成功分支检查退出码后才启动驱动。

警告地址0xdf95ac60在成功与失败进程中都出现，属于libndk_translation+0x7ac60的信号处理入口，不是崩溃PC。REA核对本机原ELF SHA c63cc0e4ef992160dec46adeb5fbd84e8f8d771c52be2366050037c0581043b4；本机REA原生反汇编provider不可用，使用现有Capstone/pyelftools及该ELF的.gnu_debugdata。首次忽略PT_LOAD0x6000的线性反汇编不构成证据；修正ELF虚拟地址0x80c60，原符号HandleFatalSignal、164字节及18字节指纹相互一致。失败探索也保留。

新增native_signal_chain.js仅在ia32/4字节指针、固定模块/指纹匹配后Interceptor.attach入口，记录最多4次致命信号的128字节siginfo、128字节ucontext及EIP候选/模块/映射文件/代码；十分钟自动detach。EIP按[Bionic i386布局](https://android.googlesource.com/platform/bionic/+/ndk-r17b/libc/include/sys/ucontext.h)解释，不保证是ARM游戏PC。Hook改变入口机器码与时序；未改参数、返回值、寄存器或游戏数据，也不能保证异步信号安全与完整覆盖。VM测试并非实际致命信号正例。

显式参数-LocalApi -InputCompatibility -NativeSignalChain -NativeStartupOutput <新路径> -ReaRoot <REA6.7.0>才启用。预spawn固定系统库SHA门、有效组合脚本独占保存/三SHA、原native-ready与signal-chain-ready双重正握手及实时PID/birth/boot/APK36检查后才允许原UI输入。默认启动路径保持。新的实际20697和22210启动均通过限定身份/双ready；没有观测到新hook捕获的真实fatal事件。

22210窗口UTC16:46:17.168–16:56:17.706，覆盖原恢复、败北退出及下次入场；两脚本均expired，capture-end=deadline、身份一致，卸载/close成功，无截断或观测到的fault。单窗口未复现不证明根因修复。前两个计划正常关闭使包装器最终在后置PID采集门退出1，但finally已恢复原APK，正常关闭来源/身份/全六态另行核对；不隐瞒为exit0，也不当作游戏新SIG11。

## 测试与证据

新增门与记录器RED71/14fail→71 GREEN；额外映射文件保留用例RED11/1fail→全72 Node GREEN。中间70/1为错误文本断言过窄，修正断言未改业务。189 Android测试重跑72.305秒通过。最终归档审计初次因result=null解析报错，修正宿主审计空值处理后实际通过，未触碰游戏。

证据位于analysis/android/flow-runs/restored-defeat-continue-20261028/evidence，startup-failure与execution分别冻结；源码、原始日志、失败样本、完整快照及逐文件SHA索引保留。历史十项Minor暂不在本轮展开。原生根因、未验收协议仍需继续推进。
