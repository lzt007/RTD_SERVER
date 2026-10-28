# 不可枚举原生寄存器采集

2026-10-28：修复旧11f6观察器通过for-in漏采GumJS寄存器的问题，当前native_faults.js精确SHA为`2cf85c4ac703fcc01b409c5faa03477bcc78df8f9e7f9fc5b296692b543f6242`。不修改游戏、候选APK、信号链或业务代码；回调仍始终返回false，不编辑寄存器。

采集先显式读取pc/sp，再读取ia32的eip/esp/ebp/eax/ebx/ecx/edx/esi/edi，最后遍历其他可枚举字段。去重，只跳过缺失的可选字段；必需字段读取失败保留错误。寄存器64项、枚举扫描128步、错误16项、回溯16帧、代码32字节、事件16次、时长600000ms均有上限，截断明确标记。PC/SP优先，不会排在大量其他字段之后。枚举预算约束采集循环，不声称能终止恶意JS代理陷阱内部执行。

VM测试覆盖不可枚举、继承和代理getter、冻结对象/禁止写入、必需getter失败、优先PC/SP、去重和大量undefined字段扫描。19项中新增6项在旧代码失败后通过；Task1全native130/130（8.588秒），构建/真实JVM通道6/6（4.730秒）。接入检查还发现REA6.7实际状态为running，早先fake使用attached；由归档状态和实际服务源码确认，新增真实状态合同RED→GREEN，未耗费设备探测次数。

## 一次真实验证

固定v2 Java源码c71860a3…/DEX45255d52…，app_process32，独立随机nonce及guest目录。测试PID **11123**（这是进程PID，不是关卡ID），出生/boot/完整cmdline/exe及源hash就绪均核验；最终source/DEX/manifest/安装包/进程/观察器消息再次检查。fsync意图后，通过启动时持有的专属stdin发送一次带nonce命令；fixture调用myPid自行SIGSEGV，未对外部数字PID调用kill。

收到一个实际native-exception/access-violation：11项寄存器，pc/eip=`0xebaa9b39`、sp/esp=`0xffdfe770`，5帧、32字节代码、errors为空且未截断。记录器返回false，测试进程exit139；核心确认自身进程消失、REA正常关闭，probe-complete/probe-host-complete成立，runner exit0，无安全终止或重试。ASLR地址只属于本次合成测试。

完整SQL逐行导出对比（含273sessions）、六账号、88runs/62receipts和原保留战斗、请求原始字节、SharedPrefs哈希、全部原件/当前ddc候选/历史/五旧QA均保持。API25508与资源服务26068未变，无RTD进程，原APK1e95仍安装。tombstone目录完全相同，没有新增文件可归因此探测。

证据：`analysis/android/flow-runs/native-register-capture-20261028/evidence/execution`，包含原始REA消息/加载来源/触发顺序/进程退出、完整前后SQLite备份、哈希和验收证明。早先9916的空context失败样本仍独立保留，不改写为成功。

这次正例只验证通用ia32异常记录器和v2安全触发通道。**没有证明ARM翻译层fatal-hook有效，也没有定位或修复RTD偶发SIG11。** 下一次真实故障可使用已验证的记录器保留实际寄存器；不能凭本测试选择游戏补丁地址。
