# 系统调用信号取证：隔离正例与启动入口撤回

2026-10-28。最终保留独立的 `native_syscall_trace.mjs` 与21项隔离测试，**没有提供游戏启动追踪选项**。实验中的CLI、PowerShell参数及beforeResume接入已全部撤回，启动器/核心恢复到本轮前的精确源码；未知选项在设备操作前拒绝。整轮审查两项C/I修复后全部原生工具186项通过，没有现场重放。没有修改游戏、服务器或自动重试策略。

审查新增一项Minor暂缓：正例重建文件保存后转为CRLF，归一化LF后才精确匹配运行pin；冻结副本不是字节精确的运行原件。原始归档不修改，准确SHA、两项已修复问题与全部边界见[整轮审查](../reviews/2026-10-28-native-syscall-evidence-review.md)。

## 有限追踪合同

模块只生成固定emulator调用方使用的命令：strace4.21跟踪信号处理注册、发送与退出调用，以及SEGV/ABRT/BUS/ILL/FPE；不使用fault/inject。输入必须是正整数PID和完整出生/boot身份，附加前后核对相同生命周期。专属管道报告tracer PID，预期主任务的TracerPid必须与之相等，且有确切附加回执才能就绪；此模块本身不构成游戏或任意进程的操作授权，调用方必须先完成目标范围资格校验。

guest timeout对它自己启动的strace子进程发INT，必要时备用KILL，**不对被追踪目标发送清理信号**。duration1..90000ms，加20秒向上取整，最长110秒；宿主子进程及完成等待也设期限。原始输出独占创建，最多256KiB，超限/写入失败/身份变化/仍被追踪均拒绝。接受LF或CRLF；分块附加信息不会因后续较大数据块丢失。目标仍存活时，tracer正常提前退出不算完整追踪。ptrace会改变调度及信号投递，不能称无扰动；操作系统强制终止、同步阻塞等不是此合同能原子控制的行为。

## 两份独立夹具证据

第一次PID15065/tracer15155在实际故障命令之前因CRLF标记被严格解析器拒绝；没有syscall-trace-ready，没有私有自触发命令。private STOP/EOF及有限tracer完成清理，夹具exit0。原始intent已在准备追踪之前写入，不能凭intent名称断言故障命令已经发送。失败前缀、退出与全态证据独立保留。

CRLF分块测试RED14项1fail→GREEN14后，新nonce的固定v2夹具PID15329/birth11412280/tracer15424完成一次自触发：

- tracer ready 21:38:55.707Z，随后才通过启动时持有的私有stdin发送一次命令；夹具自行kill(15329,SIGSEGV)。没有向外部数字PID发信号。
- 内核记录SI_USER、发送者15329，Frida2cf记录器同时获得11寄存器；退出139。trace0、9216字节、进程消失、REA关闭、runner0。
- 全SQL/六账号/273会话/88场62回执/请求/偏好/服务/原包及tombstone均保持。

这是独立运行中的ia32夹具共存正例，不能代替暂停的Android应用或ARM翻译链。随后增加的大块附加确认/提前退出防护经过RED17项2fail→GREEN，未重复夹具。两份实际helper源码从改动后文件重建，均以运行时固定的完整SHA核对相等，明确标记reconstructed，未伪称预先保存的原始副本。

## 唯一一次游戏实验：未通过

PID15881/birth11448729/boot823aea7e…；tracer15988。在双观察器就绪后，21:44:59.130Z追踪就绪，21:44:59.557Z恢复执行。系统日志实际显示：

|设备UTC时间|事实|
|---|---|
|21:44:51.127|ActivityManager启动游戏进程|
|21:45:01.129|应用未完成绑定，am_process_start_timeout|
|21:45:01.130–01.175|ActivityManager因start timeout发送KILL；Zygote明确报告signal9|
|21:45:05.475（宿主）|观察器结束identity-unavailable；pidof退出1空结果，绑定/proc目录也不存在|
|21:45:05.840（宿主）|tracer退出0；143字节，仅报告/附加/自身SIGSTOP调用，目标已消失|

不是90秒成功窗口，不是旧SIG11复现。启动仪器化消耗了绑定前时间，ptrace与暂停恢复也可能影响执行；目前不能区分二者贡献，不能称已证明具体阻塞点。截图仅显示模拟器桌面，没有公告或登录成功。包装器退出1（PID发布前进程退出），finally核对恢复原APK；没有向不存在的游戏发MCP关闭，也没有第二次游戏尝试。后续不应再把这个启动前接入作为可用选项暴露。

现场审计在撤回源码之前核对完整SQL、六账号、273会话、88场62回执、请求/偏好、34保护文件、服务25508/26068、tombstone完全不变，且tracer与游戏均不存在。撤回后另存精确源码变更清单，原30保护文件重新全部匹配，当前34项最终清单通过。原游戏实验的6份源码SHA、失败wrapper1及原始日志不随撤回而改写。

证据：`analysis/android/flow-runs/native-syscall-evidence-20261028/evidence/execution`，其中fixture-format-failure、fixture-positive、game-attempt分开冻结。旧SIG11仍未定位；本轮收获是验证独立捕获通道，并排除了把这次启动超时错算成SIG11的结论。未来若追踪游戏，应另行验证绑定完成后的有限接入，并明确早期覆盖缺口，不盲目放宽系统超时、重试或进程门控。
