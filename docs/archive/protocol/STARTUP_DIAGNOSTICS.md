# 启动退出被动诊断

2026-10-27。正常游戏启动仍用start-rtd-session；以下是独立的开发只读记录器，不操作或重启应用，不扩大恢复政策。

```powershell
. ./enter-env.ps1
# 在另一终端启动游戏之前运行；output必须是尚不存在的新目录。
python analysis/android/observe_startup.py --serial emulator-5554 --timeout 90 --output analysis/android/flow-runs/manual-startup-capture-20261027-new
```

总观测预算1至120秒，单次读取最多10秒，明确serial和固定ADB只读argv。先读取设备epoch，只看之后的所选PID日志；以boot_id/start_ticks绑定一次进程生命周期，PID/出生变化停止，不跟随新进程。日志读取和库/内存读取前后核验身份；保留此前已验证快照。输出仅保存所选进程的过滤日志、白名单图形库路径、VmRSS/VmSize/VmPeak/Threads和结果；身份UUID/credential标识行排除或掩码，内核boot_id是进程绑定元数据。不会读取SharedPreferences/cookie，也不会把诊断器插入正常输入控制链。

status语义：waiting_timeout是整个窗口未绑定游戏，不冒充退出；running_timeout是已绑定进程后预算耗尽，仅表示最后一次身份采样有效，不保证期限瞬间仍存活，也不是启动失败；exited是已观察进程随后消失；process_changed停止而不混合新进程；read_error保留已有证据并声明采集不完整；单次ADB读取在总预算前超时也返回read_error，CLI退出2。极短进程可能在绑定前消失，不能用记录器缺证据声称没有崩溃。重复读取logcat有诊断开销，正式数据不因取证而改变。

## 三次有限对照

同一API28/Swiftshader/关闭GLDirectMem、候选9230481c，独立完整QA副本startup-exit-observation-20261027；每轮Android MCP正常终止/runner原APK恢复后重新启动。三轮均一次driver、无自动恢复、原账号1/MainMenu/SELECT_AREA；记录器各90秒，仅单PID。

|轮次|PID|原flow|快照数|自然AP|初次VmRSS|
|---|---|---|---|---|---|
|1|30274|20261027-152808|21|14→17|146424 kB|
|2|31427|20261027-152957|20|17→18|146780 kB|
|3|32569|20261027-153149|20|18→18|183616 kB|

六账号/配置/78场/53回执/rev29逐轮完整推导相等，仅上述自然AP更新；源QA、正式库、原APK/DLL/历史基线/候选/observer/DEX哈希保持。没有新战斗/货币/进度夹具。三次成功不能证明永久稳定，PID27508早退仍未复现。

三次成功日志均包含同一`GoldfishAddressSpaceHostMemoryAllocator: ioctl_ping failed for device_type=5, ret=-1`。这直接证明该行不是充分的早退/自动恢复判据，不以其存在改GPU或屏蔽游戏错误。

## 本机库与分析边界

从实际PID库映射只读提取/vendor/lib/libOpenglCodecCommon.so（129220字节，SHA12f6f1147975badfd1b523e2f224f5b591e4b91a1ae1ed1d6dade2d7d8e8aa2f）、libEGL_emulation.so及libOpenglSystemCommon.so，设备/副本SHA完全匹配。REA Windows原生提供器拒绝ELF32 x86；保留完整诊断，没有通过重装注册尝试绕过不支持的目标，也不声称拿到REA反编译。

现有pyelftools0.32/Capstone5.0.3分析相同字节：导出构造函数GoldfishAddressSpaceHostMemoryAllocatorC1/C2位于0x177c0、232字节，已保存原范围SHA、全部所选指令及PLT调用映射。ioctl失败分支0x17853起调用__android_log_print、close、fd置-1，再经正常canary检查返回；不是该分支直接exit/abort。hostFree另有abort分支，但本轮没有观察到PID27508进入它，不能把未观察的下游调用写成根因。PLT映射为ELF静态解析推导，不是动态调用追踪或深提供器完整调用图。

共同证据analysis/android/flow-runs/startup-exit-observation-20261027/evidence包含逐轮审计、所选日志/内存/库、三份设备字节副本及SHA、Capstone所选指令、REA拒绝诊断、比较证明。七个既有Minor保留；本轮没有GPU/APK/服务端业务改动，也没有新增未知退出自动重试。原已知ANR的一次恢复和限制见INPUT_COMPATIBILITY及其独立审查。

审查修复：已绑定进程被观察消失时，以及抓日志后身份读取发现进程已消失时，在剩余同一预算内补取一次终段候选。terminal-unverified.txt单独保存、terminal_candidate.verified=false；不增加snapshots，不供恢复决策。补取后检测到替换即丢弃；读取失败保留原快照和terminal_candidate不可用原因。PID-only日志无法在死亡后证明进程归属，前后package为空也不能排除其他进程复用同号，故不得将候选写成原游戏崩溃证据。

Deferred新M1：启动epoch只精确到秒，首次绑定前同数值PID的旧持有者日志可能混入保留区间；出生标识前后稳定不证明每条历史日志归属。当前三次实际样本无此影响证据，仍不作无条件“所有日志均属于同一进程”的保证。旧七Minor继续保留，完整审查与裁定见../reviews/2026-10-27-startup-exit-observation-review.md。


## 2026-10-28 有限原生冷启动采样

启动器显式原生模式新增 NativeStartupDurationMs，默认600000，范围1..600000；孤立参数或越界在环境/ADB/APK操作前拒绝，原生CLI已有时限实现不变。实际PowerShell隔离包装器RED6项失败→6项GREEN/5308.0234ms，全部78native/12015.4022ms、218Android/129.657s通过。ADB、Node、环境脚本、sleep全部隔离，测试无真实设备效果；只有新增包装器诊断参数，无客户端/原生脚本/业务变化。

沿用quest-departure-guard-20261028同库/run-id/API25508及其配对缓存，原30882本场完整SQL/六态/8项偏好文件先备份。正常MCP关闭、旧包装器exit0、原件1e95/noPID后才开始；本轮每次关闭均保存原MCP结果及包装器exit0。

原生候选36/11f6+既有信号链/c63/REA6.7.0/新PID出生boot、双ready/resume全部核验，零UI输入。三轮PID2611/3492/4240分别采集90.255/90.696/90.741秒，原RTDFlow持续更新TitleMenu，原生公告WebView覆盖其上（截图确认为停服域名DNS错误），不是三次登录或主菜单可玩验收。每轮deadline/unload/close后仍确认同身份与候选，随后正常关闭、原件恢复。最终无客户端进程，普通API25508/18766保留，同QA88场62回执/113单位五队/原本场及全部SQL（含会话）、所有账号/请求日志完全不变，正式资产/人工11123/五旧QA保持。

宿主90000ms只控制采集；客体观察器预算仍为600000ms，三轮未观察到expired，不能声称双expired或十分钟覆盖。宿主时间未与客体hook时钟校准。三次仪器化启动成功不是SIG11根因修复或永久可靠性证明；没有实际fatal hook正例。第一轮漏采启动前tombstone目录，保留明确的post-start列表，不将已有tombstone归因首轮；后两轮有完整前后目录。总审计初次stdin importcommon失败，移为自有脚本后正常完成，无重复启动。先前13Minor继续保留。

当前证据analysis/android/flow-runs/bounded-native-startup-20261028/evidence/execution；本轮唯一整轮独立审查待执行。实际新通信缺口为原公告页外部URL失效，后续单独设计恢复；本轮仅静态定位，未改公告或候选。

最终唯一整轮审查C0/I1/新M0，独立105哈希、3时间线、原状态重建、冻结完整SQL及安全包装器探测通过。I1为[int]先将小数舍入再校验范围；单轮TDD修复为原始字符串的纯数字/1..600000校验，新增字符串和数值小数用例RED16项8fail→GREEN16，包含上下界有效值。首次GREEN尝试3个旧断言依赖英文validate措辞而失败，保留原日志并按稳定Validation错误类别修正；副作用断言仍严格。最终88native/10724.285ms及218Android/84.820s GREEN。原三轮用准确整数90000，仍有效，不为输入校验修复重复启动；没有二次审查。全部25边界逐项裁定见../reviews/2026-10-28-bounded-native-startup-review.md。先前13Minor保留，原生SIG11仍未定位。
