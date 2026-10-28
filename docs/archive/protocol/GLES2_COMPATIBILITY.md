# GLES2 compatibility experiment

2026-10-28，独占模拟器，BASE3576d27。只增加可选启动参数 ForceGles2 → -GLESDynamicVersion，保留SwiftShader、DirectMem关闭、4096MiB/2CPU、无快照与用户数据。默认启动参数不变。实际PowerShell参数构造回归先2项失败、后全部原生207/207通过（10168.1276ms）；没有修改业务协议或游戏源码。

原boot823aea7e…正常关闭，唯一GLES2启动新boot8146dc91-580b-4b86-838e-15963def87ec。sys.boot_completed=1且ro.opengles.version131072。重新提升adbd为root以读取既有诊断/偏好，不改SELinux/perf/security属性。全SQL、六账号273会话88场62回执、请求、偏好、原APK、服务身份及保护38项通过；内核信号格式逐字节匹配已验证正例。旧正例来自共享冻结档案，没有重放夹具。

唯一内核实例nonce4d9583b93d062f7f871d676cde7834f1/脚本3560，READY23:22:03.356Z后才启动原默认LocalApi/InputCompatibility包装器。无Frida/ptrace/输入/登录/战斗/重试。完整窗口120.104931秒，1243事件+2标记，CPU624/621，与头部和统计完全对齐，丢失/此前读取均0；脚本0、实例禁用移除、全局与wifi配置保持。

唯一游戏PID4248：Android start1793143340.262、bound3341.464，实际游戏PID4248/TID4309的EGL日志3346.131确认maj2/min0。内核唯一fork出生166.135355，4248在170.675138创建4309；同PID/TID游戏EGL记录提供交叉归属证据。没有及时取得存活时start_ticks/maps/task快照：后续身份采样因游戏已经退出而失败，保留为失败，不伪造完整身份。

|boot时间|GLThread4309记录|原始code|handler|
|---|---|---|---|
|172.645692|生成SIG11/目标4309/group0|196609|—|
|172.645756|投递SIG11|196609|0x5b19f440|
|172.647153|再次生成SIG11|196610|—|
|172.647215|投递SIG11|196610|0x0|

所有这些记录TGID字段均空；归属来自独立fork和AndroidPID/TID日志，不能把整个系统的其他信号算成游戏崩溃。窗口另有webrtc-thread3728产生42次SIG11，未归因于RTD。Zygote3346.803明确记录游戏4248因signal11退出（出生后约6.51秒），不是9，也不是手动关闭。没有新游戏tombstone。截图为桌面及System UI未响应对话框，不是游戏主界面。

原始code保留196609/196610（0x30001/0x30002）；旧Android内核头文件的__SI_FAULT高位规则与MAPERR/ACCERR低位一致，这是参考源码解释，尚未匹配本机精确内核二进制，不能据此给出fault地址、PC或具体责任模块。[参考定义](https://android.googlesource.com/kernel/common/+/9e695d2ecc8451cc2c1603d60b5c8e7f5581923a/include/asm-generic/siginfo.h)。更不能把先前自身SI_USER正例推广为ARM硬件故障链已验证。

包装器返回0仅表示退出后原APK恢复成功；游戏启动失败。已不存在的游戏不再MCP关闭，不重放。记录完整结束后正常回退到原GLES3启动参数。最终回退/全状态核验记录与审查另附。结论：GLES2限制真实生效但未修复SIG11；新证据把本次失败缩小到GL线程的两次信号投递及handler变化，仍缺PC/地址/当时maps。不能与旧灰屏管道卡住或旧SIG11直接判定同因。

证据：analysis/android/flow-runs/gles2-compatibility-20261028/evidence。历史16项Minor暂缓；本轮本地Git，未merge/push，按既有删除拒绝只归档。

最终回退boot4c6e3e3a-40c2-49af-a36d-33f509b82bc1，实际原启动参数及GLES196608核验通过，无游戏重试。完整SQL/六账号273/88/62/请求/偏好/保护38文件/两服务身份/原APK/无游戏进程/无新增tombstone全部现场核验通过。只读诊断使用的adbd root在回退后重新启用；未恢复旧Frida守护进程，游戏实测无Frida。当前已恢复原GLES3环境。

最终审查C0/I0/M1，无C/I修正或重审。新增Minor：scratch启动循环的同步ADB及包装器调用不能构成通用主机硬时限；本次实际完成和回退证据有效，未来复用前应补足监督。累计暂缓17项。审查及逐项边界见docs/reviews/2026-10-28-gles2-compatibility-review.md。
