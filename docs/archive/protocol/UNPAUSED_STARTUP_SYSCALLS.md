# 正常启动下的早期内核跟踪实验

2026-10-28，BASE32e23a6。一次默认包装器启动，无Frida、暂停spawn、输入或重试；未改生产源码。

对象PID18843/birth11695296/boot823aea7e-3168-4a17-949f-4967fedea7be，DDC候选。watch-ready22:25:40.140Z，discovered22:26:07.604Z，tracer18955就绪22:26:09.455Z。设备启动epoch1793139956.790，ready后的设备整数秒1793139965，说明取样时距启动约8–9秒；这不是attach时刻精度证明，也没有建立覆盖旧PID19812启动约6秒SIG11的能力。跨主机完整身份/安装包/Android启动记录核验耗时，不能把本轮叫作从出生起全覆盖。

固定110秒guest窗口实际ready至detached110.007秒，trace退出129/306字节，目标仍存活，runner0。只见附加和两个线程正常退出，无所选致命信号。不是旧SIG11复现或根治证据。

window.png实看为黑屏；解除附加后的after-detach.png实看为原LOADING画面。during线程快照中UnityMain和UnityPreload有tracing-stop，其他线程多为等待；单一快照并不能证明持续停住。启动进展与解除附加时间相关，早期ptrace存在明显扰动，不能当作无干扰稳定性验收。没有再启动或通过点击推动。

核对同PID/birth/boot/候选/已发布PID/TracerPid0后MCP正常关闭，包装器0并恢复原APK，无游戏进程。完整SQL/六账号273会话88场62回执/请求/偏好/34保护文件/服务身份/tombstone均不变。maps-before/ready、线程快照、原始trace、系统日志、截图和前后SQL保存在analysis/android/flow-runs/unpaused-startup-syscalls-20261028/evidence/execution。

结论：这种多轮ADB核验加早期ptrace不满足所需早期、低干扰取证目标。下一步先只读检查内核tracepoint/perf能力；不重复同类游戏启动，不修改信号处理器或放宽Android超时。15项历史Minor保留。
