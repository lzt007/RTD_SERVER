# 被动信号取证能力检查

2026-10-28，只读查询，未启动游戏或改变内核追踪配置。当前Android9用户态ia32，信号tracepoint格式的unsigned long为8字节，不能据此把用户态寄存器改称64位。

已观察：/sys/kernel/debug/tracing存在且有独立instances目录；已有wifi实例，必须保持。全局tracing_on为0。signal_generate事件ID53包含sig/errno/code/目标comm/pid/group/result；signal_deliver事件ID52包含sig/errno/code/sa_handler/sa_flags；sched_process_fork格式可读。支持userstacktrace、print-tgid等选项，时钟列出local/global/counter/uptime/perf/mono/mono_raw/boot/x86-tsc，当前local。只证明接口存在，未证明新实例可写、用户栈有效或正例可捕获。

simpleperf list tracepoint一次只读调用超15秒，主机ADB被超时终止；随后pidof simpleperf退出1空结果，无残留。原部分输出保留，不重跑list。record --help通过独立guest5秒timeout返回0，perf_event_paranoid为3；没有进行perf录制，也未修改系统属性或权限。

共享原始输出：analysis/android/flow-runs/passive-signal-capabilities-20261028。第一查询批在list超时处终止，故queries.json未形成；second批明确记录超时并保存实际结果。不得把缺失输出当成功。

下一条可检验路径是独立nonce实例，仅开启信号/线程创建事件，先用自持私有stdin的独立ia32夹具验证SIG11正例、字节上限/丢失计数和关闭恢复，再考虑一次游戏默认启动。该路径不使用ptrace或Frida；需独立测试和有限生命周期，不能仅凭目录存在直接用于无人值守。
