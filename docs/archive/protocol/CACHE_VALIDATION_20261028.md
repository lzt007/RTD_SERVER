# 原缓存恢复与客户端资源需求核查（2026-10-28）

本轮仅静态分析与历史证据复核，未复制、覆盖或清空模拟器缓存，未启动游戏。

后续更新：原生键规则现已还原，90 个原缓存目录已全部唯一命名，8 个原包补齐发布。另行执行的设备诊断未得到完整结果且均已回滚。下文为最初调查时状态；最新结论及边界见 ORIGINAL_CACHE_IDENTITY_20261028.md，不能继续把“键算法未知”当作当前状态。

## 已确认

- 原缓存应按完整 UnityCache/Shared/<原哈希目录>/__info 与 CustomAssetBundle-* 的结构恢复，不能把 90 个裸载荷平铺到 HTTP 下载目录，或简单改名为 .unity3d。备份是 Unity 缓存展开后的 SerializedFile；当前 HTTP 服务提供的是重新封装的 UnityWeb 传输包。两条恢复路径不同。
- 历史设备缓存校验记录 analysis/android/offline-cache-verification.json 有 76 条，全部与原载荷 SHA256 一致。但它不是对“全部 90 份原目录原样恢复后均被游戏命中”的验收。analysis/archive_checkpoint.py 当时仍标注 runtime retest pending。
- AssetBundleLoader.cs:154 起对 URL 和整型版本调用 Caching.IsVersionCached，未命中时使用 WWW.LoadFromCacheOrDownload(URL, version)。基础包首项即使检查命中仍进入该 API；这不等同于必然联网。
- GameManager.cs:170 起由当前关卡敌人列表选择所需 bundle，调用同一双参数下载 API，并检查 loader.error。成功后使用 loader.assetBundle。资源清单已经在客户端代码中，不需要靠猜校验值恢复名称。
- 此下载调用没有传入显式 CRC；不能由此推断底层 Unity 完全没有格式、解压或完整性检查。现有托管调用证据也不支持声称存在完整的服务端 SHA/MD5 文件清单。
- AssetBundleDefine.cs 声明 76 条基础资源定义与 313 条敌人资源定义。后者含 17 条 .meta 名称；它们是原始表项，不表示运行时必定请求。SystemUtility.GetPlatformURL() 返回 Android/。URL 包含原 CDN 根、版本目录与文件名；GetVersion 返回枚举序号（V1011=1 … V1020=10）。
- 导出清单：analysis/unity/client-resource-requirements-20261028.csv，389 条定义。当前服务目录覆盖基础 76 条和非 meta 敌人 7 条。其余“未发布”只代表对应文件名未出现在当前服务目录，不代表备份中没有所需内容；本表也不是包内对象和依赖的完整清单。

### URL 与缓存格式的来源边界

CSV 的 original_url 是严格按原 APK 的 GetURL()、GetPlatformURL() 和 VersionDir 常量表求值生成，不是根据缓存文件名猜测，也不是当年网络抓包所得。倒数第二层 V1020c7R7HlupcYzJ80UutCh3B4HQc9MEHUvf 是原代码中的版本目录常量，不能把其外观相似的后缀视为缓存文件名或哈希算法证据。末尾 .unity3d 是原代码固定追加的后缀，但后缀本身不证明 HTTP 响应的内部格式。

备份是下载后保存在 Unity 缓存中的结果，与当年 HTTP 响应不必逐字节相同。现有本地恢复路径将原 SerializedFile 载荷封装为 UnityWeb/LZMA，客户端下载处理后，已有音频缓存 SHA256 与原备份完全一致（见 ANDROID_MCP.md）。这验证了“传输封装 → Unity 处理 → 原缓存载荷”的可行性；不证明本地重建包与当年 CDN 响应完全相同，也不能据此判定当年具体压缩参数。当前未见托管游戏逻辑自行拼装所有资源的证据；缓存键与存储转换仍需从 Unity 层验证。

## 尚未验证，不能当作结论

- Unity 原生缓存键的具体推导、__info 每个字段含义及原缓存到当前 URL/版本的对应关系。不能仅因 CDN 根变更就断言缓存键必然改变。
- 当前 APK 与历史手机缓存是否覆盖同一版资源；完成强制更新不能单独证明按需敌人包的覆盖范围，但也不能据此认定用户备份缺失。
- 90 份缓存与全部 APK 内置对象、外部引用、预制体、材质及纹理的完整关联。现有资源名检索失败不能等同于物理文件缺失。

## 后续验证方法

在保留现有缓存及状态、可回滚的隔离环境中恢复全部 90 个原目录，逐条执行客户端自己的 IsVersionCached(URL, version)，记录缓存命中结果，再针对所需资源调用原加载 API 并记录错误、对象名和依赖解析结果。先定位“未命中”“命中但不可加载”“加载成功但对象/依赖未匹配”，再决定是否调整目录映射或 HTTP 发布。不能用 389 与 90 相减推断缺包数。

## 静态证据

- 原 Assembly-CSharp.dll SHA256：c83aea19ee65ae973815daf6a04e430d9e87b8426b6180c1fe507e4260763ecc。
- 本轮 REA inspect_managed_members 保留证据：ev_873aa01c4f595d17155ce688ff7b7bba86e58bcf55bdb95a2467114cae3a40ca。选择 AssetBundleDefine、AssetBundleLoader 命中；带斜杠的两个嵌套类型名称未命中，不能把该调用说成已覆盖全部嵌套类型。加载流程细节结合已有反编译文件核对。
- 20103 的 ms01_sla_lv4_gold 曾在原缓存存在但没有发布，补充映射后可继续战斗，见 MULTI_FLOOR.md。因此发布遗漏是已出现过的实际原因。
