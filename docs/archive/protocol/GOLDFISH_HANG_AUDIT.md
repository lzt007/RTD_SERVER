# 图形管道卡住的只读复核

2026-10-28。游戏20976关闭、原包恢复后，只读保存当前模拟器进程/配置/guest属性；未重启或修改模拟器。

当前进程1124/emulator、21704/qemu，实际参数RTD_API28_ARMv7_16G/4096MiB/swiftshader/no-snapshot-load/no-snapshot-save/-WiFiPacketStream,-GLDirectMem。AVD2CPU；guest uname报告4.4.124+、2019-01-30构建、i686，ro.opengles.version196608（GLES3）。getconf命令不存在，故前文CPU用原始ticks，不臆定频率。

已安装host advancedFeatures.ini中GLESDynamicVersion=off，guest文件中on；当前实际属性是GLES3，不能仅据host默认文件声称已限制GLES2。GLAsyncSwap/GLDMA/RefCountPipe等已列原文件，未随意切换。早先-feature-list不支持，改用当前二进制-help-feature确认显式特性开关；错误SDK变量调用发生在只读帮助查询，后以enter-env.ps1提供的ANDROID_HOME定位。

官方[特性说明源码](https://android.googlesource.com/platform/external/qemu/+/emu-master-dev/android/data/advancedFeatures.ini)说明关闭GLESDynamicVersion会限制所公布的最高GLES版本；[当前GPU配置说明](https://developer.android.com/studio/run/emulator-acceleration)也列出swiftshader及其他软件后端。这里只把显式关闭GLESDynamicVersion作为下一项可回退的单变量候选，需要同时验证guest属性和实际EGL上下文，不能把一个启动参数当作修复证据。

官方[goldfish管道源码](https://android.googlesource.com/kernel/common/+/8c51adb100d9453a35a66c6336d2ca33321673e7/drivers/platform/goldfish/goldfish_pipe_v2.c)显示该路径负责guest↔host管道传输，并串行化每个pipe命令；这支持把已观测内核栈定位于管道路径。未匹配当前kernel精确源码/二进制，不断言某个上游版本的静态page数组或循环就是本机根因。

结论是后续优先测试图形兼容配置，保留SwiftShader/既有DirectMem关闭/数据/原APK，只改变一项显式GLES能力；如果上下文仍未按预期改变或再次卡住，就保留具体失败并回退。旧SIG11与本次灰屏是否同源仍未知。原始只读证据analysis/android/flow-runs/goldfish-hang-audit-20261028（21文件SHA索引）。
