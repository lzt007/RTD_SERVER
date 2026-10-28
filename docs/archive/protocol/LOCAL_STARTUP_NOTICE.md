# 本地启动公告与共通文本

2026-10-28。原生公告 WebView 已改用本地内容，保留原版标题、关闭按钮及原客户端流程。启动不再为公告请求已失效域名。本增量不涉及支付、存档迁移或普通关卡扩充。

## 内容接口

资源服务仍为 `python analysis/serve_offline_bundles.py`，绑定 `127.0.0.1:18765`，通过原启动器 ADB reverse 提供给模拟器。

|方法|路径|响应|
|---|---|---|
|GET|`/rtd/local-notice`|自包含 UTF-8 HTML，无脚本、外链或外部素材|
|GET、POST|`/rtd/local/common-text4.json`|原 APK com_text 的四字段 JSON，仅 info 改成本地公告地址|

POST 支持原客户端的 `g=g` 表单；单一 ASCII 十进制 Content-Length、最多4096字节、5秒读取超时。缺少长度411、非法/重复长度或Transfer-Encoding400、超限413、短EOF400、超时408；固定内容响应及错误关闭连接，不记录表单正文。UTF-8 Content-Type、字节 Content-Length、no-store。未知路径404。原 unity3d 流式下载保持原逻辑。本接口不提供任意文件、后台写入或新业务数据结构。

原始字段 app/review/home 保持原值，未扩充 CommonText 类其余未恢复字段。源为原 APK `assets/bin/Data/sharedassets5.assets` 的唯一 com_text TextAsset，字节及来源哈希见 `analysis/android/flow-templates/common-text-original.provenance.json`。

## 客户端构建

接受的父 APK 为36b517db…，管理程序集11ff2b64…，完整父 APK/manifest 在 `analysis/android/client-history/36b517dbf73ff3032a3c842c3761666e36fb271980c3e6474a4b4eee2eb719e3/`，排他创建且拒绝损坏历史。受保护原 APK、DLL和2e09基线未改。

REA 原 DLL SHA c83aea19…/MVID81502538…：`ResidentManager.GetInfoAddress` token06000d62 改为本地公告常量返回；嵌套 `<Coroutine_ComTextDownLoad>c__Iterator4B.MoveNext` token0600144e 中IL116、127两处原com_text4地址改本地JSON地址。共两个方法、三个字符串位置。TitleInfo及MMEtcInfo的实际消费者调用该getter；仅修改未使用的默认字符串不足以修复。

新管理程序集 SHA `c000eea4d4f58447627f32802c09cf87db8f92936baa9c8b132ba5fcc20d8026`；候选 APK SHA `ddc68da5ae1fddede3c1ebdd47c40c89a4922bc81309744e094b2e001e81c860`。Cecil静态重建不执行游戏程序集，固定PE时间戳0以确定构建；验证器重建精确预期字节并比较所有非目标方法/局部变量/异常区域。原输入兼容、四处恢复缓存钩子、原生库43b4、DEX7cfd、observer613d、cachehelper7033保持。仅Assembly-CSharp包成员变化，其他ZIP载荷及所检元数据相同。

```powershell
. ./enter-env.ps1
$parent='analysis/android/client-history/36b517dbf73ff3032a3c842c3761666e36fb271980c3e6474a4b4eee2eb719e3/candidate.apk'
python analysis/android/build_startup_notice.py --source $parent --output analysis/android/rtd-local-api-notice.apk
python analysis/android/build_startup_notice.py --source $parent --publish analysis/android/rtd-local-api-notice.apk --output analysis/android/rtd-local-api-input.apk --history analysis/android/client-history
```

先独立构建、全成员验证及临时根目录session能力预检，再发布；两个文件分步替换并在失败时回滚旧对，并非对并发读者的双文件原子事务。发布时应无游戏/控制器。native_startup_capture只接受上述新确定候选，未放宽为任意manifest。

## 实际验收

flow `20261028-033400`，一次新候选启动，PID7105、出生10658816、boot823aea7e…；原资源服务21980经命令/端口所有权核验后替换，新PID记录在证据。业务API25508、quest-departure-guard-v1及原配对QA保持。

原客户端 POST共通文本200（03:33:45）、GET公告200（03:33:52）；`002-check-notice.png`实际显示本地日文正文，没有Webpage not available。较早单独截图处于Loading，另张稍后截图已是原GooglePlay不可用100对话框，不能冒充公告截图；验收以驱动关闭公告前的原始截图为准。

一次现有MCP驱动，resume-only11000、150秒上限，依次关闭原公告、确认GooglePlay不可用、触摸开始、恢复原战斗，03:35:12.830到GameManager/GameStateField/controlsUnlocked。没有战斗攻击、移动、入场或结算输入。完整六账号/config/run/receipt重建一致：原held run54e0746b…不变、88runs/62receipts，只有实际auth时间导致AP26→29及恢复锚变化；两个auth新增session271→273。原三请求auth/auth/get_quest_info全部4096，其他SQL表及非state玩家列不变。正式库、五个旧QA、原件及历史候选均核验未改。SharedPrefs做了前置tar备份，不宣称退出后字节相同。

原生host窗口19:33:18.230Z–19:36:18.826Z，180.596秒，覆盖全部输入及恢复完成；双ready在resume之前、来源哈希/系统库c63/PID出生绑定通过，deadline、unload、close完成，无观察到native/signal-chain故障或错误，无新增tombstone。guest观察器仍600秒，未观察到其expired；host/guest时钟未校准，不声称永久稳定或SIG11根治。

初次只读资格检查发生在首条RTDFlow之前，保留早期日志；未启动驱动、未新增启动，随后同PID完成全部资格核验才发布探针并输入。审计脚本曾误把玩家快照与flow快照同名，修正命名后从已冻结的after-backup重建玩家快照，并重新验证自然AP与完整SQL；未改动存档。另两处审计假设（玩家state列位置、REA unload的null返回）依据实际模式/返回更正，未重放游戏。

最终经Android MCP正常关闭，wrapper39290退出0、原APK1e95恢复、无游戏PID；退出后完整SQL及请求与验收备份一致。API与新资源服务保留供后续开发。

验证：内容HTTP9、管理程序集5、恢复缓存33、打包7（29.297秒）、完整Android225（123.302秒）、原生88（15.582秒）通过。证据、原始记录和源副本见 `analysis/android/flow-runs/local-startup-notice-20261028/evidence/execution/index.json`。这是启动公告验收，未实际打开主菜单公告，虽二者静态共用已修复getter。

最终一次独立审查C0/I3/新M0。三项Important已同轮TDD修复：禁止发布/构建进入默认或配置的历史目录；CLI报告必须是独立新文件并排他创建，不能覆盖DLL；POST改为单调时钟的整体5秒预算，缓慢持续发送也会超时。最终HTTP10/0.300秒、管理补丁8、打包9/27.410秒、Android227/113.743秒、原生88/15.238秒、缓存33通过。候选APK/管理程序集哈希不变，未为工具防护重放游戏。资源服务已在所有修复测试通过后重新加载；原API与验收后完整SQL保持。

审查边界及13个历史Minor见[完整裁定](../reviews/2026-10-28-local-startup-notice-review.md)。另对保留的native JSON作离线复核，按脚本真实事件名native-exception/signal-chain-fatal检查无故障；更正早期审计器错误的native-fault/signal-chain-fault拼写，未把旧条件当作正例验证。closing归档保存正确检查器及结果，execution122文件不覆盖。
