# 原生取证宿主截止时间

native_capture.mjs及native_startup_capture.mjs的CLI现共享宿主预算：合法观察时长1–600000整数毫秒，加45000毫秒准备/清理余量。校验在REA读取和输出创建前完成；空值、小数及越界拒绝。预算包围REA setup/capture/closeAll，而非只包围采集循环。

异步REA操作不返回时记录native-host-timeout，关闭证据输出并以1退出；正常完成以0退出，保留的Frida句柄不再阻止宿主结束。观察错误在等待关闭前记录为native-host-operation-error，关闭错误另记并合并，不用后续清理异常遮掉主错误。该机制不宣称所有Frida资源均已优雅释放，也不是对阻塞JS事件循环的本机代码执行提供抢占。包装器自己的finally负责恢复安装原包，正常取证完成后仍须关闭其游戏会话。

新增16项隔离测试：挂起setup/closeAll、计时器取消、超时/错误时输出关闭、原始及清理错误、晚到拒绝、真实Node子进程保留句柄仍能按0/1退出，以及两个真实CLI在无REA目录时先拒绝非法时长。RED9/9→GREEN9，补充RED16/7fail→GREEN16；全部native147/147（8.842秒）。业务/游戏/观察器代码未修改。

## 实际窗口：提前停止，未判定为游戏崩溃

2026-10-28计划最多3次90秒零输入冷启动；第一轮遇到身份读取异常后，立即停止整个连测，没有进行第二或第三次。

- 原生候选ddc、记录器2cf、信号链a4f0、桥库c63，实际PID12041/birth11125690/boot823aea7e…；双ready及resume来源绑定。
- host UTC20:51:07.028恢复进程，20:51:07.174一次身份读数返回通用Startup RTD PID changed or unavailable，20:51:07.281采集结束，reason=identity-unavailable。不是90秒完整窗口。
- 原始消息没有native-exception或signal-chain-fatal；不能由此说该窗口外没有故障。一次pidof的实际返回值未被旧代码保留，不能断言是空列表还是额外PID。
- 后续只读检查证实同一PID、同一出生、同一boot、同一cmdline及安装候选仍存活；系统日志有该进程正常显示/加载WebView的记录，没有本次退出证据。故不把这一读数直接解释为SIG11、进程重建或永久修复。
- 完整身份再次核验后通过Android MCP正常关闭，包装器exit0并核对原APK1e95恢复，无RTD进程。REA卸载结果null，关闭回执targetResumeObserved=true，照实保留，不编造false。

全SQL逐行、六账号/273会话/88场/62回执、请求字节、SharedPrefs、29项原件/当前候选/历史/旧QA/诊断源码、API25508及资源26068保持；tombstone目录相同。证据位于analysis/android/flow-runs/native-host-deadline-20261028/evidence/execution。该轮是具体诊断停止，未冒充冷启动通过或崩溃复现。

剩余可操作问题：身份读数需要保留实际值/读取阶段；连续观察应以已绑定PID的出生/boot/cmdline验证为依据，不能把一次全局枚举差异无证据地当作进程死亡。任何后续调整仍须保留PID重用及外部进程门控，先隔离测试后验证，不能放宽检查直接重试。

唯一整轮审查C0/I1/新增M0。I1指出真实capture内部先存bodyError再await核心清理，若该清理挂起，外层适配器无法及时写出原始错误；现于两个核心catch中先写native-operation-error/startup-operation-error，再保持原清理/抛错顺序。真实导出采集函数及挂起清理回归RED19/3fail→GREEN19（1.485秒），含真实子进程失败退出；全部native150/150（8.790秒）。仅增加诊断事件，不重放设备窗口或修改身份判断。原执行证据保留，两项源码修订另列精确哈希，审查处置见[整轮审查](../reviews/2026-10-28-native-host-deadline-review.md)。
