# 原生异常记录器正例验证

后续状态：寄存器采集已在独立增量修复，当前runner观察器pin为2cf85c4a…；v2也已完成一次设备正例。以下11f6/9916记录保留为首次失败的历史证据，当前结果与限定见[不可枚举寄存器修复](NATIVE_REGISTER_CAPTURE.md)。

开发工具，独立于游戏启动/操作。目的：用一个明确的合成SIGSEGV检查现有native_faults.js能否记录真实native-exception。不是RTD崩溃复现，不验证ARM翻译信号链，也不声称修复SIG11。

现有JDK21.0.8、SDK build-tools36.1.0/d8构建固定纯Java临时类，minAPI28。fixture不导入游戏、不联网、不读写业务或偏好文件，最多生存120秒。审查修订v2的Java源码SHA为c71860a3…，DEX为45255d52…；完整源码/编译器/DEX身份在生成manifest中。首次实验使用的v1源码26bd49cc…和DEX6b1f5b73…保留在execution归档，不与修订版本混称。

```powershell
. ./enter-env.ps1
# 只在输出目录不存在时构建；重复使用应verify，不覆盖旧产物。
python analysis/android/build_native_probe.py --output analysis/android/native-probe-build/v2
python analysis/android/build_native_probe.py --verify --output analysis/android/native-probe-build/v2
# output必须是现有父目录中的新绝对JSONL路径。先正常关闭游戏、确认原APK恢复。
node analysis/android/native_fault_probe.mjs --rea-root C:/Users/Administrator/AppData/Local/npm-cache/_npx/a1722018f28f9df2/node_modules/rea-agents --adb $env:RTD_ADB --output C:/MYDATA/workspace/RTD_FAKE/analysis/android/flow-runs/probe-new.jsonl
```

runner拒绝任意PID/程序/信号/脚本参数。随机nonce绑定专用guest目录、Java READY行、完整nice-name及专属stdin通道；核验PID出生/boot/exe，必须是app_process32、原RTD安装包且无RTD进程。通过REA6.7.0加载未经修改的11f6观察器，并核对返回的实际source_sha256。最终重新检查本地源码/DEX/manifest、guest DEX、安装包、进程身份、观察器会话/脚本及晚到错误，先fsync触发意图，再经专属输入管道发送带nonce命令，让fixture调用myPid/sendSignal自行触发一次SIGSEGV。未知发送结果不重试。v2不再向外部可复用的数字PID调用kill。

只有实际native-exception（本PID、PC/SP、有限回溯、无采集错误）和进程退出均观察到，且REA清理成功，才能报告probe-complete；ready、干净超时、fixture退出本身都不算正例。异常观察回调始终返回false，不修正寄存器或接管游戏；[Frida官方API](https://frida.re/docs/javascript-api/)说明未返回true时异常继续交给进程/系统。app_process nice-name位于cmd-dir之后，参考[Android9原实现](https://raw.githubusercontent.com/aosp-mirror/platform_frameworks_base/android-9.0.0_r1/cmds/app_process/app_main.cpp)。

采集预算30秒，服务调用有host wall-clock截止；REA6.7某些清理操作不响应取消，所以核心清理另限5秒，CLI最终关闭再限5秒并记录失败、关闭证据文件后显式退出，避免Frida句柄无限驻留。对仍完整匹配的存活fixture仅经原有专属管道发送STOP，使其自行退出；不向数字PID发送TERM。READY失败时关闭管道，另有120秒fixture看门狗及130秒ADB child超时兜底。明确截断的寄存器/栈记录不得报告正例。不清空tombstone、不重启服务/模拟器/游戏，不删除其他目录。原件、候选、全部SQL及请求必须前后保持。

## 2026-10-28首次实测：正确阻止误报，记录器需修复

唯一尝试PID9916，独立app_process32/随机nonce/出生与boot/就绪均绑定后，持久化意图再发一次SIGSEGV。收到实际native-exception/access-violation，记录PC位置0xf628db39、32字节代码、8帧，errors为空；但context被序列化为`{}`。因此runner明确失败exit1（Invalid native-exception identity/context），没有probe-complete；测试子进程exit139，REA正常关闭，没有TERM或重试。这是具体诊断结果，不冒充正例验收通过。

现有11f6观察器通过`for (const key in context)`采集寄存器，真实GumJS对象未枚举到属性；同一次回调直接访问context.pc仍能读出上述代码，说明空字典不能当作不存在上下文。此前普通JS字面量测试没有覆盖该形态。下一独立增量应新增不可枚举寄存器的失败用例，再修复采集和来源pin；不放宽探针要求，不在本轮暗改观察器或重放。

完整SQL（含273sessions）、六账号、88runs/62receipts、请求字节、SharedPrefs哈希、原件/候选/历史及五旧QA均保持，API25508/资源26068保持，无RTD进程且原APK1e95未变。tombstone目录前后相同，故不把旧文件归因本次合成信号。新fixture专用guest目录保留作证据，未装应用或接触游戏数据。

Task1构建5测试（5.119秒）、新runner24（189.512毫秒）、全部native112（11.676秒）通过；真实实验暴露了已有观察器的覆盖缺口。证据冻结到 `analysis/android/flow-runs/native-fault-positive-probe-20261028/evidence/execution`。不由这次人工合成信号推断RTD原故障地址或ARM翻译信号链是否有效。

唯一整轮审查C0/I5/新增M0；五项Important均在一次TDD修复中处理，不重放设备实验。新runner36、全部native124（8.670秒）、构建及真实JVM通道测试6（5.125秒）通过。v2通道在隔离JVM验证正确nonce只能触发自身PID/固定SIG11或退出，错误nonce/超长输入拒绝；尚未在设备运行。完整审查处置见[审查记录](../reviews/2026-10-28-native-fault-positive-probe-review.md)。
