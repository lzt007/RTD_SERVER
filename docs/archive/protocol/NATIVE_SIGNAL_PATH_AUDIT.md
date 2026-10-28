# 原始 Unity/Mono 信号路径静态排查

2026-10-28，仅分析原始二进制与独立有限寿命的 sleep 子进程，不启动游戏、不修改游戏/服务器。证据目录 `analysis/android/flow-runs/native-signal-path-audit-20261028`，脚本和逐字节 SHA 索引保留。

原APK assets/libs/armeabi-v7a/libunity.so 为6847860字节，SHA eb8ab8714c7eda4dbf49c5f032557caba08c4eadfe02742b8337c7f184cf4724；libmono.so 为3815628字节，SHA4e7490e69dc9bae5537d39339ded11ce6b5a84f751a7868951cb83cd2b68529a。APK lib/armeabi-v7a 下同名库是较小的不同字节，不能混为同一个目标。REA打开两份目标并确认ARM/SHA，但Windows原生分析provider不可用；未重复安装，用已有pyelftools与Capstone进行有界范围分析。

Unity导入mono_set_signal_chaining、raise、pthread_kill和kill。按每个.rel.plt的GOT目标验证ARM PLT计算后，只扫描.text中直接ARM BL候选：

|调用地址/目标|前置参数|本次能支持的结论|
|---|---|---|
|0x5ea474 → raise@0x4a414|r0=8|这处不是直接raise(11)|
|0x44c7c0 → pthread_kill@0x4a570|r1=19|这处不是直接发送11|
|0x21b618 → kill@0x4a8dc|r1=9|这处不是直接发送11|
|mono_set_signal_chaining@0x4a93c|未发现直接ARM BL候选|不能说函数从未被调用，仍有Thumb/间接/外部调用边界|

Mono导出mono_set_signal_chaining（0xbf494，60字节）及mono_do_signal_chaining（0x3aee2c，4字节），同时导入sigaction/bsd_signal/raise/pthread_kill/kill/abort。所选setter机器码将传入参数写到经GOT取得的地址，没有在该范围直接调用sigaction。尾随literal pool也包含于符号范围，不能将反汇编器显示的每项都当作可执行指令。Mono内部多个sigaction候选与可变信号参数存在；目前没有运行时调用证据，不能证明重置了Frida处理器，也不能据此提出修改Mono全局开关。

当前模拟器内置strace4.21、debuggerd和simpleperf。记录了现机帮助及版本。独立sleep6秒子进程PID14695，toybox timeout向它自己启动的strace发送INT（1秒、2秒备用期限）；strace attach成功，timeout实际返回129，随后sleep同一进程仍存活且TracerPid=0，最后自然退出0。没有给游戏或外部数字PID发送信号。此单次探测只证明本机这条有限寿命链的正常脱离，尚未证明Frida暂停进程与strace兼容、多线程完整附加或SIG11正例。

[strace4.21官方手册源码](https://raw.githubusercontent.com/strace/strace/v4.21/strace.1.in)说明它记录系统调用与收到的信号，附加模式可中断脱离。这里优先保留本机实际结果，不把当前新版手册的额外选项套用到4.21。ptrace会影响调度及信号投递，不能称零扰动。

结论仍是未定位RTD SIG11。已排除“这些Unity直接调用必然自行发送SIG11”的推断；观察器未收到异常也不能证明没有信号。后续若使用系统调用追踪，须先核验自己的完整进程身份及有限期限、确认可脱离，不以任意PID附加或无限重启扩大诊断。保护30文件再次核对一致，游戏没有运行。
