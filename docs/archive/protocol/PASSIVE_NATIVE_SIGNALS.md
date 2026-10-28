# 被动内核信号记录与新启动卡住样本

2026-10-28，BASE5be0cb8。新增native_signal_trace.mjs为固定独立tracefs实例脚本生成器和完整性解析器，没有新增游戏启动选项、客户端hook或服务端变更。旧186项加14项新测试共200/200 GREEN（9368.4711ms）。缺失模块RED→12GREEN；实际ADB CRLF回归RED13/1→199GREEN；OWNER先于配置的回归RED14/1→200GREEN。

仅使用新nonce实例，boot时钟、每CPU256KiB、信号4/6/7/8/11与进程fork、BEGIN/END标记；独立guest timeout、私有OWNER/READY/DONE、EXIT清理。校验2MiB上限、两个CPU的overrun/commit-overrun/dropped均0、完整单一标记和有效记录；64bit handler/flags保留hex。当前guest的print-tgid接口虽可设置，实际信号TGID字段为空，不能据此许诺通用线程归属。

## 唯一夹具正例

第一次主机调用在只读配置比较中退出1：Python快照统一LF，Node原始ADB保留CRLF；没有nonce目录、意图、推送、内核写或夹具启动。保留原日志，现场复核配置/全数据不变，仅修正scratch读取配置的换行比较。

随后唯一实际内核夹具实验nonce842a73363f5fcf1e469856208c3a8345，自有脚本PID20522。追踪READY22:47:39.515Z，固定v2夹具PID20548/birth11825327/boot823aea7e…核验后，22:47:43.409Z通过持有的私有stdin请求一次SELF11；没有向外部数字PID发信号，也未注入Frida。

原始完整124条记录含唯一fork出生、TID20548生成11/code0/目标20548，并投递11/code0；先调用handler0x63ea7440，后再次生成/投递时handler0。child139，trace脚本0，45秒窗口完整无丢失。初始scratch分类器额外要求非空TGID而退出1；该失败未改写。离线以已核验的自身主线程TID、唯一fork和私有触发链复核同一份原始数据，通过后才放行游戏；没有重放夹具。此证明限于自身主TID的ia32合成SI_USER，不证明硬件SEGV_MAPERR或ARM转换链正例。

实例禁用并移除，全局与既有wifi实例配置保持。夹具新增tombstone_10，文本PID/名称与自身一致，完整保存；不伪称tombstone完全不变或删除记录。

## 唯一游戏窗口：捕获能力通过，游戏启动未通过

新noncea43786d4df183f25d519fb2d727b1119，脚本PID20916，READY22:51:47.566Z后才运行一次原默认包装器。无Frida、ptrace、输入、登录、战斗或重试。游戏PID20976/birth11852317，DDC候选及cmdline/boot/已发布PID核对，TracerPid0。

boot时钟完整窗口120.017622秒；唯一fork出生在BEGIN后23.278724秒，出生后剩余96.738898秒。194条记录均为fork，所选致命信号记录0；两个CPU所有丢失计数0，脚本0、实例禁用/移除。取得了出生之前到早期运行的内核信号覆盖，不把无事件当根治。

两张实看截图均为「ロードラ」灰色启动界面，没有公告/主菜单。窗口结束后仍未进入游戏。之后只读线程快照显示：

|线程|累计用户/内核ticks|当时内核栈|
|---|---|---|
|主线程20976|195 / 14034|mutex_optimistic_spin → transfer_max_buffers → goldfish_pipe_read_write → goldfish_pipe_read → read|
|GLThread20996|95 / 13092|preempt_schedule / try_to_wake_up → wake_up_q → transfer_max_buffers → goldfish_pipe_read_write → read|

ticks是进程启动以来累计值，不是120秒窗口内采样剖析。快照给出图形管道内核等待/自旋的具体线索；单点栈不证明永久死锁，也不能把旧SIG11归因为同一原因。后续应检查当前模拟器图形配置/管道兼容，而不是据此修改业务协议或猜测Mono补丁。

同身份/候选/TracerPid0/实例已移除再次核验后MCP正常关闭，包装器0并恢复原APK，无游戏进程。完整SQL、六账号273会话88场62回执、请求/偏好、保护34+新增2文件、服务身份、全局/wifi追踪配置保持；游戏阶段没有新增tombstone。15项历史Minor保留。

证据：analysis/android/flow-runs/passive-native-signals-20261028/evidence/execution，包含原错误退出、离线复核、实际脚本/原始trace/CPU统计、夹具tombstone、截图、内核栈和前后数据库。原始生成/观测阶段源码逐份冻结，不用后续修改伪造历史源码。此轮增加了有正例的有限取证通道并保存新失败；没有修复SIG11，也不宣称无人值守开发已稳定。

最终审查C0/I1/M1。I1修正使解析记录数（含两个标记）必须同时匹配唯一头部总数、written和每CPU entries；read events与丢失计数均0，拒绝缺失/重复/畸形元数据。新增4项回归先失败后通过，全部原生204项通过；原始夹具126条(80/46)与游戏196条(96/100)离线复核通过，无重放或改写历史原始证据。最终现场全状态/原包/无游戏进程核验通过。新增Minor为极端合成有符号字段Number溢出，暂缓，累计16项；逐项边界及处置见对应review文档。closing保留最终源码和审查修正证据，execution的139份历史冻结文件保持原字节。
