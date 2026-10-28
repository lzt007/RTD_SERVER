# 11000资源映射独立复核（2026-10-25）

本次以用户指定的`C:/MYDATA/workspace/RTD_FAKE/jp.co.acquire/jp.co.acquire.RTD`为事实范围，重新检查“11000需要ms01_sla_lv3，但现有索引未匹配”的解释。**结论限定为：目前原始客户端、已恢复主表与指定缓存之间的11000资源映射仍未闭合；不能据此概括用户保存的热更新整体不完整。** 下面明确区分观察、代码推导与未知。本次没有修改旧报告、服务端或原始资源，没有操作设备、启动服务或请求补充备份。

## 独立问题与证据身份

问题分为三个可证伪假设：①静态名单误计未选中/rate0敌人；②缓存压缩或内部名字造成旧索引遗漏；③旧客户端有共享模型/fallback而无需目标资源。

REA重新读取原始`jp.co.acquire.RTD/assets/bin/Data/Managed/Assembly-CSharp.dll`，SHA256 `c83aea19ee65ae973815daf6a04e430d9e87b8426b6180c1fe507e4260763ecc`，MVID `81502538-516d-4802-bbff-d4f363e3388d`，不加载/执行目标程序集。保存证据：

- `analysis/unity/resource-recheck-managed.json`：REA `ev_bd8eadaf93ecf8b67cd3e0f36fc4ec9183515ed36cf4c576c12fb3b31e2df5d6`，精确选择EnemyArrangeTable、EnemyData、ClientData、GameManager、AssetBundleLoader。metadata/CIL覆盖完整；此较宽选择的user_strings状态为partial，不用它证明字符串不存在。
- `analysis/unity/resource-recheck-coroutine.json`：REA `ev_b50e5d70e16a60e1ce92a9a18b2393741d477c57ad4f2682b0b197f9b59c3634`，精确选择实际协程类型`<LoadEnemyAssetBundle>c__Iterator7`；metadata/CIL/user_strings完整。尝试的两个带外层前缀类型名未匹配，已显式记录，不当作覆盖。
- `analysis/unity/resource_recheck_20261025.py`及`resource-recheck-20261025.json`：本次重新解析缓存全部容器和所有主要资源对象名字、来源SHA256、头部、__info原始字段、11000构造名单；未重提取位图/模型。
- `analysis/unity/resource-recheck-fallback.json`：独立重新读取mainData ResourceManager，对目标路径及fallback路径逐一解析。

上述文件均位于ignored的`analysis/unity`。反编译文本的行号用于解释，并由本次原DLL CIL锚点/字段读取/调用边交叉核对。

可重放审计脚本已保存在受Git管理的`analysis/resource_recheck_20261025.py`；在根目录用项目Python运行，输出仍写ignored的`analysis/unity/resource-recheck-20261025.json`，不会提取或修改原始资源。

## ① 实际加载名单是否误计

**观察**：`ClientData.cs:3667`的SetupChooseQuest读取所选quest.enemy_table_id并执行`new EnemyArrangeTable(m_EnemyTable)`，没有先按已生成敌人、rate或地图坐标过滤。REA方法token`0x06000767`，CIL SHA256 `aa13b320bd4f6eb565ae231cb7478523d79373c9bbf4bc7dd2b7f9d71c6ac248`，直接构造与写入m_EnemyArrange。

`EnemyArrangeTable.cs`构造18个普通槽及boss/death两槽；GetUniqueEnemyList遍历enemies字典，只排除enemy_id=0，然后Distinct。REA方法token`0x0600086e`，CIL SHA256 `a19f68309a8fa82f8b1f562a91340ee14bda4e724772c1dfee684d54ddd1beb2`；本方法的字段读取只有enemies与enemy_id，不读取arrange_rate或地图。

11000→enemy_table10000的实际非零构造项：

| 字段 | arrange_id | enemy_id | rate | model |
|---|---|---|---|---|
| enemy1 | 1 | 10000 | 100 | ms01_sla_lv1 |
| enemy2 | 2 | 10100 | 100 | ms01_squ_lv1 |
| enemy3 | 3 | 22000 | 80 | ms00_tresure_unit_01 |
| boss | 99 | 31010 | 100 | ms00_death_01 |
| death | 0 | 41221 | 100 | ms01_sla_lv3 |

槽4–18均enemy_id=0/rate0，确实被GetUniqueEnemyList排除。41221不是rate0误计，unique结果是`[10000,10100,22000,31010,41221]`。

**关键语义观察**：表字段名容易误导。`LevelCellManager.cs:40–41`把`enemies[0]`赋给BossID，`enemies[99]`赋给DeathID。也就是说death_set_id=41221是本关实际关底Boss；boss_set_id=31010反而是惩罚Death。不能将41221视为“惩罚怪不会出现”而删除。

**观察**：实际加载协程MoveNext token`0x060012b6`、CIL SHA256 `7ec564cb367fe3240121d073b394252bbe949a8ad9e0ed9e7488ae2cee86933b`，REA调用边明确包括GetUniqueEnemyList→IsLocalAsset→GetEnemyBundleInfo→WWW.LoadFromCacheOrDownload。全局文本检查只发现SetupChooseQuest写入m_EnemyArrange，没有发现后续移除41221或按实际响应敌人重建该表的赋值。

**推导边界**：以当前恢复的type30/hash2988722424、type21/hash458932175、type20/hash700614136为输入时，41221确实进入该原客户端预加载路径。这不是对未知版本主表、现运行patched DLL或尚未观察动态状态的证明。

## ② 指定缓存是否因压缩/内部名字漏索引

**本次重新观察**：指定目录内90个CustomAssetBundle全部解析成功；每个顶层都是Unity`SerializedFile`，不是尚未打开的UnityWeb/UnityFS传输压缩包。直接读取AssetBundle.m_Container全部键，同时对GameObject、Texture2D、Material、Mesh、TextAsset、AnimationClip、AudioClip读取对象名字；90个文件零名字读取错误。重新解析得到的容器名与旧bundle-names索引差集为0。

90文件的原始字节及解析对象名均未命中`ms01_sla_lv3`；也未在某个“别名bundle”的内部对象中找到`ast_ms01_sla_lv3`或`ms01_sla_lv3_fire`。实际可见slime模型相关名字包括`ast_ms01_sla_lv1_gold`、`ast_ms01_sla_lv4_gold`等；名字相似不能当作精确对象加载成功。每个载体的SHA256及全对象名已保存，可复核而无需依赖本结论。

**__info的观察与限制**：90份__info都为4行，第一行为`-1`、第二行为整数、第三行为`1`、第四行为对应CustomAssetBundle文件名；其中没有URL字符串。没有取得该格式解码证据，因此第二行不强称特定时间语义，第三行不能盲认成业务bundle版本。音频声明V1016而__info相同位置也为1，尤其不能把此字段直接等同AssetBundleInfo.GetVersion。缓存目录的40位hex也未被证明是URL哈希；对已知bundle名的两个候选根做SHA1实验均未匹配，所以本报告不靠目录hash反推URL。

代码可证明的**请求身份**是AssetBundleDefine.GetURL拼接：`http://www.acquirespdl.jp/RTD/DLC/Android/V1011/ms01_sla_lv3.unity3d`，GetVersion返回枚举V1011的整数1。它来自代码声明，不是__info恢复出来的实际历史请求；现有缓存不能据此宣称已映射/已命中这个URL版本。

**未知**：指定缓存与目前APK内置主表是否属于同一运行时组合、是否曾使用不同动态主表、Unity3.5缓存内部URL/version索引如何映射这90个payload，仍缺可验证证据。这些未知与“用户保存的是完整热更新”并不逻辑冲突；可以是当前恢复的版本组合或缓存映射方法尚未恢复。

## ③ 共享模型/fallback能否解释现有资源

**观察**：EnemyData构造函数直接令PrefabName=master.model，Tex来自master.texture；41221 type=1，不进入22/24/30/31/33/37的unit-enemy/book替换分支。AssetBundleLoader的local名单仅5项，不含ms01_sla_lv3；本次没有发现从该目标映射到slime lv1/lv4、共享bundle或另一个prefab名的分支。

**此前遗漏、此次确认的fallback**：`EnemyData.cs:160`的LoadPrefab在Resources加载失败/异常时尝试`Prefab/Enemies/ms02_four_dark_01`。REA方法token`0x060006b4`，CIL SHA256 `1bb718d01c4180bda723d4c9e5fe06afbb8beb2a6610bd3739a5e0de4d8f9539`，调用AssetLoader.Load并有异常区域。不能再说旧客户端完全没有fallback。

但它与“非local bundle下载失败回退成功”是不同条件：

- `GameManager.cs:233–260`的非local预加载先等待WWW；loader.error时`k--`重试同一bundle，没有调用EnemyData.LoadPrefab。
- `EnemyManager.cs:423`在已有对应bundle时精确Load(`ast_`+模型名)、精确纹理及材质；只有取不到对应bundle时才走EnemyData.LoadPrefab。
- 重新读取ResourceManager确认：目标模型路径、目标fire纹理路径及fallback的`prefab/enemies/ms02_four_dark_01`都没有条目；`prefab/enemies/ms02_four_un_01`则有真实GameObject、pathID23、Data/dec7ba846e371474fbb94a5a79fc1601、SHA256 `a2d61b2becb37728aa330e8082ba9d078319a21d4f31a4730cd3e61513e445eb`。不能把dark和un两个字符串当作同路径。

**推导**：这些原代码分支不能解释“精确目标载体未匹配却仍保证11000加载成功”。这不等于动态运行必然失败：仍应以实际请求、缓存命中与加载对象身份观察来闭合，尤其要确认当前安装客户端是否与本次原DLL一致。

## 结论与下一步

保留已证实的窄结论：当前恢复主表会让原客户端请求ms01_sla_lv3；这不是rate0/未选中敌人误计，独立重读90个缓存也没有发现旧索引漏掉同名内部对象。修正此前过宽表述：有客户端fallback，但尚无证据证明它在这条预加载路径成功；没有依据宣布用户的全部热更新不完整。

后续应在已有文件范围内先恢复“实际运行客户端身份→动态主表版本→缓存URL/version→容器对象”的映射，再做隔离加载验证。具体观察目标为11000使用的type20/21/30 hash、m_EnemyArrange五个ID、请求上述精确URL/version、Unity cache是否命中、返回payload SHA256与`ast_`模型/纹理加载结果。此轮没有设备授权操作，也没有以资源替换或删除boss分支来绕过未知。

T12仍未得到“每个使用资源可加载”的证据；保持调查状态。旧报告未改动。
