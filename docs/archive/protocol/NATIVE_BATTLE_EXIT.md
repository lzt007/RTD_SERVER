# 原生退出诊断

## 当前结论

195345战斗PID25634的Zygote signal11已归档；尚无其PC/故障模块/调用栈。最终客户端36b517db后续真实胜利不等于修复该退出。本轮新增独立Frida观测，不修改APK、战斗状态或服务端规则。

## 版本与安装

REA6.7.0依赖Frida17.23.2；Node24.22.1/npm11.19.1。绑定在忽略目录tools/native-frida，精确版本及package-lock保存在共享证据setup/。REA缓存内原来不存在的node_modules/frida新增junction指向该目录，未修改REA注册或替换现存依赖。当前MCP进程安装后仍报frida/index.js解析失败，使用同一包的全新CLI进程成功；这不代表MCP接口已恢复。

原npm prebuild下载等待被终止，仅停止核对过的自有安装子树。直接下载官方同版prebuild，先校验SHA256，再在最终npm --ignore-scripts安装后解出唯一build/frida_binding.node。后者顺序必要：npm完成安装会替换临时解出的binding。保留两次失败输出，不伪装首次安装即成功。

- 官方Windows包frida-v17.23.2-napi-v8-win32-x64.tar.gz：e9dbc08d386130610430137f0bb31d90af7b08c0f5710942d4313368ada930ea。
- binding：32c73230bdfd4b9a8f1f1871ef616001e486269919f18a111a195854352057dc。
- Android x86 xz：cfe8a5318a4bf35c3d434d12f56f2527c408349e8bec3b00ad81ffd926f4b704；解压server：6a8f2d317d37fc566f9c3a55c265891f46f72c72c8129b2ad222fb73ef52349d。
- guest新增/data/local/tmp/rtd-frida-17.23.2，chmod700，`-D -l 127.0.0.1:27042`，仅来宾回环ADB。启动shell因daemon继承描述符未返回；独立检查server PID30117和监听成功。不会为结束shell而误杀游戏或其兼容包装器。

恢复工具环境时，先确认没有活跃诊断会话、核对server PID命令行，再停止该server；只移除新增junction本身，不递归删除其target。无需改REA注册/游戏数据。工具现在保持可用，未执行清理。

官方来源：[Frida Android](https://frida.re/docs/android/)、[JavaScript API](https://frida.re/docs/javascript-api/)、[17.23.2 release](https://github.com/frida/frida/releases/tag/17.23.2)。Node包完整性和官方release元数据保存在setup证据。

## 被动附加验收

`analysis/android/flow-runs/native-battle-exit-20261027/evidence/setup/index.json`包含逐文件哈希。REA CLI对PID26584附加3秒，只枚举模块，然后cleanup_error=null。工具normalized_result.state为running（清理前观测值），不是额外的detached回执。游戏PID26584/start_ticks7956283/boot823aea7e-3168-4a17-949f-4967fedea7be前后一致；六账号/配置/86run/61receipt完全相同。213模块，未截断，包含libndk_translation和libmonochrome；原ARM Unity未在该x86模块枚举中出现，不能据此否认其映射存在。

## 异常采集合同

脚本analysis/android/native_faults.js独立于只读RTDFlow。最多16异常，每条16帧、32字节PC代码、64寄存器，启动256模块，10分钟到期。初始化不读代码；异常发生时才有界readVolatile。未知模块/range为null；错误文本有界。不改context、不调用原业务函数；所有正常/错误/超预算路径均return false，让原处理器或OS决定后续行为。注入和异常拦截本身会改变时序，不声称零扰动。

事件native-ready/native-exception/native-limit/native-expired/native-error含PID/设备时间。Backtracer.ACCURATE可能为空或无法展开翻译代码；native-exception也可能是原本可处理的信号，不能单条认定为崩溃。最终归因必须结合外部同PID+birth+boot及Zygote退出时间。消息预算耗尽和传输失败会限制覆盖；窗口未复现不能证明修复。

`node --test analysis/android/test_native_faults.cjs`10项VM合同RED→GREEN；VM不证明真实Android注入/展开能力。实际REA原始消息/源hash/进程身份单独存档。

## 完整窗口与生命周期

REA临时CLI单次最多60000ms；600000ms请求被校验拒绝，未附加（失败原输出battle-rea.json保留）。因此新建native_capture.mjs，直接导入已安装REA6.7.0的FridaInstrumentationService/Manager持久接口，保持原provider/Evidence实现，不是修改REA，也不把自制结果称为MCP返回值。新Node进程能正确读取已安装依赖，不需要重配或重启用户的Codex。

适配器输出JSONL：配置/源码SHA、外部PID+start_ticks+boot_id、原REA load/status Evidence、卸载/关闭结果。status在消息数或状态变化时完整保存，避免重复写同一批消息；原provider截断标志原样保留。每次先排空所选会话消息，再检查进程身份，以免进程消失时丢掉最后排队的故障。PID更换或读取失败立即结束，不附加替代进程。finally依次卸载和关闭，一项失败仍尝试下一项，并明确报cleanup-error。REA自身closeAll作为进程结束前的最后释放。

7项生命周期合同及原10项合同共17项GREEN，包括进程两次轮询间死亡仍保留队列证据。真实10秒菜单探针成功，源QA完整复制后测试API切到native-battle-exit-20261027，PID13784/run-id native-battle-exit-v1；探针期间六账号/配置/86run/61receipt不变，PID26584身份一致。正式库/旧QA/客户端未改。后续战斗沿原PID，隔离副本继承明确的本地必掉书/属性奖励夹具，不代表历史掉率。

## 当前真实战斗

原MCP flow20261027-205134已在20:56:20返回SELECT_AREA，PID26584，原GameClear→MMResult→MainMenu，正常胜利、无Continue。原order a250e2b42184418da8616975ee8b6bbf，run a9ef3e846b6042f59cc2c70a223bd8f7，唯一clear cea97a47307241d59e5ce1222a40b45a。完整quest_acceptance.verify_victory通过：全六态、原体力规则、冻结掉落/奖励和唯一回执，111→113单位/五队保持、87场62回执。旧QA文件SHA及原件清单仍相同。结果文件pid本来是字符串，验收按规范化字符串比较；胜利以steps中的原GameClear和结算为依据，不猜result内不存在的battle_outcome。

10分钟窗口已结束：host12:51:08.917Z–13:01:12.150Z，只有native-ready，无native-exception/native-limit/native-error、无provider截断；脚本卸载和关闭成功，PID身份及战后六态保持。未收到native-expired，不能把VM中的到期合同冒充实际收到到期事件。主机限时清理已执行；没有复现源195345故障，不是根因修复。

收尾发现最后一次存活检查与消息入队之间仍有竞态，补第8个生命周期测试RED→GREEN，在finally卸载前再drain一次，原10+新8共18 GREEN。最终3秒真实探针清理/全六态通过。这项改进没有倒写原10分钟结果；execution/native_capture.used-in-10min.mjs保存当时d4f7b92的适配器，runtime-source-provenance.json区分原窗口/最终探针版本。主采集器native_faults.js没有变化。完整执行证据按execution/index.json冻结，旧setup/index.json保持。

## 唯一审查与最终修复

独立整增量审查C0/I2/新M0，两项Important均接受，同一轮4个回归RED→GREEN：附加异步返回后必须先复核PID/birth/boot，才能加载脚本并归属Evidence；不匹配/不可读则不加载、不保存原生观测，关闭会话并明确attachment-unvalidated。成功后Evidence绑定已验证身份，最终capture-end分开baseline与validated身份。原始attach动作可能已注入Frida agent，不能承诺完全不曾接触替代进程；新的门阻止加载采集器和错误归属。

卸载也是异步间隙，原provider在其间仍接收消息，因此保留卸载前drain并增加卸载完成后、关闭队列前drain。卸载失败仍排空可用消息和尝试close，completeness=unknown，不伪装覆盖完整。最终22 Node与189 Android/116.816s GREEN；修复后3秒真实探针验证attachment-validated先于rea-load、正常清理、六态及八原件/源QA哈希相同。原10分钟窗口不追认修复，未复现游戏SIG11。

全部33裁定、25排除判断和九项历史Minor在[完整审查记录](../reviews/2026-10-27-native-battle-exit-review.md)。没有第二审查；原审17+92文件保持，单轮修复证据独立归档review-fix/。

## 真实信号正例的范围

另建aux-positive/六文件档案：新建且核对身份的临时sleep120进程PID1793，确认同一采集器native-ready后，仅向该辅助PID主动发送SIG11。REA确实记录native-exception/access-violation及PC/range/寄存器/回溯/代码数据、errors=[]，随后detached并成功close。游戏PID26584及完整六态均未变。该主动信号是隔离诊断正例，信号解析的memory字段不等于RTD发生了某次真实内存访问；它不证明ARM翻译栈可完整展开，也不是游戏故障复现。独立审查报告形成后追加，未冒充审查者实机执行或覆写其原报告。
