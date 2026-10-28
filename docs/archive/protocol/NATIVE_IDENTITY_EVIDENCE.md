# 启动进程身份差异取证

2026-10-28。本轮保留严格身份门控，新增可注入的只读取证适配器，不改变游戏、服务器、安装包或异常观察器。前轮 PID12041 的通用身份错误没有保存原始 pidof 输出；随后同一 PID/出生时刻/启动 UUID 的进程仍然存活，所以既不能称为崩溃，也不能追溯断言具体原因。

## 读取与拒绝规则

`native_process_identity.mjs` 的 `readStartupIdentity` 只在 pidof 退出0、去除首尾空白后的 stdout 等于预期单一 PID、stderr 为空时进行正式身份读取。空结果、多 PID、其他 PID、非零退出或 stderr 均拒绝；不重试、不选择其他 PID，不用诊断读数覆盖拒绝。

差异记录包含序号、预期 PID、退出码以及最多各512字符的 stdout/stderr，并标记截断。传输异常另记最多1024字符的错误，不伪装成进程不存在。仅对结构有效且退出0/1、stderr空的差异，额外只读采样已经绑定的 PID，标记 `diagnostic_only:true` 后仍抛错。

正式读取和诊断采样均按 boot/stat/cmdline/stat/boot 顺序核对：命令名必须为 jp.co.acquire.RTD，stat 中 PID 正确、出生 tick 为正、前后不变，启动 UUID 前后不变，拒绝死亡/僵尸状态。初次无游戏进程门控以及 MCP 关闭前完整身份/候选包校验不变。逐次读取不能证明整个读取间隔不存在任意变化；这不是操作系统原子快照。

## 唯一一次真实窗口

证据目录：`analysis/android/flow-runs/native-identity-evidence-20261028/evidence/execution/`。只有一次启动意图，没有输入点击、战斗、重试或第二轮。

|项目|结果|
|---|---|
|身份|PID13278；start_ticks11245539；boot823aea7e-3168-4a17-949f-4967fedea7be|
|观察器|native_faults SHA2cf85c4a…；signal_chain SHAa4f03080…；双 ready 无错误，REA 加载源码 SHA 与配置一致|
|候选/桥接|APK ddc68da5…；ARM 翻译桥 c63cc0e4…；原活动 com.prime31.UnityPlayerNativeActivity|
|恢复执行|2026-10-27 21:11:06.279Z（本地10月28日05:11:06）|
|窗口结束|21:12:37.191Z；deadline；恢复后90.912秒|
|界面|window-near-end.png 显示原生「運営からのお知らせ」及本地公告 HTML；startup.png 只是早期 LOADING|
|消息|没有 native-identity-discrepancy、native-exception 或 signal-chain-fatal，没有观察器错误/限额或宿主超时|
|结束|完整身份及候选包重新核对后 Android MCP 正常关闭；wrapper退出0，恢复原APK且无RTD进程|

全量 SQL（包含273会话）、六账号快照、88场/62回执及保留战斗、请求字节、SharedPreferences、30个保护文件、API25508与资源服务26068身份/健康、tombstone列表前后不变。正式数据库未修改。原生工具八套165测试通过；新身份模块15测试先失败再通过。

这次窗口未重现前次差异；无法证明其原因，也不能据此称 RTD SIG11 已修复。通用 ia32 正例仍不能代替真实 ARM 翻译链异常验证。宿主135秒预算仅约束可调度的异步流程，不抢占阻塞的 JavaScript/文件写入或模块加载；本轮不声称已覆盖600秒客体到期。不要无依据反复启动或放宽门控。
