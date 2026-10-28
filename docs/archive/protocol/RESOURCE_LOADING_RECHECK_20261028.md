# 原版资源加载流程与全量离线复核（2026-10-28）

## 结论

此前把“进关加载资源”概括为“进关下载资源”不准确。原版使用 APK 内置资源、基础包启动预载、敌人包按关卡读取缓存三条路径。读取缓存并不等于网络下载；预载完成也不表示全部资源一直驻留内存，或已经下载了声明表中的全部敌人包。

## 原版代码证据

- `analysis/decompiled/TitleMenu.cs:205` 调用 DownloadStart；`AssetBundleLoader.cs:145` 的 FILESET 用 `m_BasicBundles` 的 URL 和版本检查缓存，未命中时调用 `WWW.LoadFromCacheOrDownload`。第 0 包即便命中也调用该 API 来获得音频包对象，不能据此判定网络下载。CheckLoadingFinish 遍历全部 76 个基础包（1 音频、75 角色组）。FINISH 保留音频，释放本次加载的其他包对象；磁盘缓存与内存对象是两回事。
- `GameManager.cs:97,127` 进关检查的是内存中的音频/角色包是否存在；缺少对象就通过 LoadAssetBundle_Single 再调用缓存 API。它不证明磁盘缓存不存在。
- `GameManager.cs:168,233` 从当前关卡敌人表提取唯一模型，跳过五个内置模型，并向 `GetEnemyBundleInfo` 查询其他敌人包，再调用 `WWW.LoadFromCacheOrDownload`。因此首次遇到未缓存敌人包确实可能产生下载；后续命中缓存则从缓存读取。反编译代码中 `m_EnemyBundles` 只被定义与名称查询使用，没有发现启动遍历整个敌人列表的预载循环。REA 对原 Assembly-CSharp.dll 的迭代器 MoveNext 调用边确认了该缓存 API 调用。
- `LevelResources.cs:98` 等地图贴图/背景/天空入口走 AssetLoader；`AssetLoader.Load` 实际为 `Resources.Load`，使用 APK 的资源索引。
- `AudioClipLoadHelper.cs` 从已经加载的 AudioClipManager 执行 `AssetBundle.Load` 获取 BGM/SE；没有看到按关卡逐首下载音频的路径。
- `Enemy.cs:252` 需要替换纹理时，在对应敌人包中按 `enemyData.Tex` 原名 Load Texture2D；没有敌人包时从 `Prefab/Enemies/Textures/` 的 APK 路径加载。不能把模型名与纹理字段随意拼接。

原 DLL SHA256：`c83aea19ee65ae973815daf6a04e430d9e87b8426b6180c1fe507e4260763ecc`。本轮 REA 敌人迭代器调用边父证据：`ev_4899ba5edd95018f2ef1caedb629e4083846286fec517e05c4999349cf06334a`。

## 扩大后的离线检查

执行 `analysis/audit_resource_flow.py`，输出 `analysis/unity/resource-flow-recheck-20261028/`。只读原文件，没有启动游戏或修改设备数据。

| 检查项 | 结果 |
| --- | --- |
| APK Data 目录直接文件 | 2,869 个，105,394,696 字节 |
| Unity 序列化文件 | 2,866 个，全部解析，33,066 个对象 |
| 其他三个文件 | PlayerConnectionConfigFile、settings.xml、splash.png |
| APK ResourceManager 索引 | 2,250 条，全部解析到存在的源文件和对象 ID |
| APK Texture2D / AudioClip | 1,033 / 3 个对象 |
| 原始缓存包 | 全部 90 个，均解析 AssetBundle 容器与对象名称 |
| 缓存 Texture2D / AudioClip | 1,091 / 26 个对象 |
| 解析和名称读取错误 | 0 |

数字为对象数，不代表去重后的图片或歌曲数。90 包中全部 26 个音频对象来自 AudioClipManager；敌人包也包含 Texture2D、材质和网格，不是只有空模型引用。APK 五个内置敌人 prefab 的资源索引均存在，与代码白名单一致。

APK 序列化文件的外部文件引用均能找到普通源文件，唯一特殊路径为引擎内置的 `library/unity default resources`；不能把这个虚拟路径当成丢失的游戏下载文件。

本轮比早期只扫 7 个 sharedassets 加 mainData 的资源清点更全面：覆盖了 Data 下大量哈希命名的独立序列化文件。找到了 `ms01_sla_lv3_tob` 与 `ms01_sla_lv3_tob_6` 动画资源，但 APK 与全部 90 包的具名对象检查，仍未找到 `ms01_sla_lv3` / `ast_ms01_sla_lv3` 模型或名为 `fire` 的纹理；APK 对应模型/纹理 Resources 路径也未找到。因此有动画不等于有该模型及贴图，不能据此撤销此前已授权的视觉替代。

## 边界与解释

这是文件解析、资源索引和加载代码的交叉检查，未逐张解码贴图，也没有验证所有 prefab 的每一个组件依赖或游戏内实例化。不能推导出“全游戏已无资源缺失”。本轮没有新增设备端完整缓存命中验证；此前探针未获得完整结果的边界仍然保留。

完整拷贝一台已正常更新手机的缓存，能够保存该手机当时实际缓存的内容；原版基础预载范围并不覆盖全部敌人包，所以它不必然包含所有未游玩关卡资源。另一个已确认问题是备份包与当前 APK 存在版本差异（音频 12 对 6，741–750 为 11 对 10，并含当前 APK 表外的 751–820 组）；这可能影响缓存命中，但不能仅凭差异断言原手机遗漏或备份不完整。参见 `ORIGINAL_CACHE_IDENTITY_20261028.md`。

后续区分三类问题：资源实物缺失、版本/缓存键不匹配、存在但加载或渲染失败。进关 Loading 或看到代码调用缓存 API，都不足以单独证明在重复下载大资源。
