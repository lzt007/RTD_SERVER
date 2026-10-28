# T12 战斗资源前置证据（2026-10-25）

2026-10-25补充：用户指定目录已逐个解析全部90包，加载链、prefab fallback及boss/death arrange_id复核见[独立复核](RESOURCE_RECHECK_20261025.md)。最新结论是客户端/主表/缓存映射未闭合，不能笼统判定整个热更新不完整。11000的缺失41221是arrange_id0实际Boss；不能按主表boss/death字段名猜实际用途。替代方案等待用户决定，未实施资源覆盖。

状态：**调查中，不能标记 DONE，也不能据此放行普通战斗**。本次仅做本地静态读取；没有操作设备、启动服务、修改运行代码或提交 Git。固定下一验收候选为第二教程 **10001「戦技指南」**及原始普通关卡 **11000「旅立ちの平原」**。

## 证据范围与复核方法

- 复用 `analysis/master-data/individual-textasset-provenance.json`、`analysis/level-data/provenance.json`、`analysis/unity/bundle-names.json`、现有离线 transport manifest；未重跑全量提取。
- 定点重新读取 type22 两份及 type70 的 Unity TextAsset，逐份校验 source/payload SHA256；读取候选地图来源并校验 source SHA256。派生完整行级比较保存在 ignored 的 `analysis/unity/battle-resource-audit.json`，复核脚本为 `analysis/battle_resource_audit.py`。
- 定点读取 `mainData` 的 ResourceManager，以其资源路径、外部文件编号及 pathID 解析 MapTable、地图、主表、敌人 prefab/texture、伤害效果；不凭资源文件名猜测。派生 `analysis/unity/battle-fixed-resource-manifest.json` 包含逐项来源 SHA256、类型和外部依赖文件存在性；脚本 `analysis/battle_local_audit.py`。
- REA 只读重新确认原始 `Assembly-CSharp.dll` SHA256 `c83aea19ee65ae973815daf6a04e430d9e87b8426b6180c1fe507e4260763ecc`，MVID `81502538-516d-4802-bbff-d4f363e3388d`。本页行为解释复用对应反编译文本，不把静态解析当作 Unity 运行时加载成功。

当前关联主表沿用已恢复的 `sharedassets5.assets` 快照（source SHA256 `840a5a34feaaf8eef057f919361f98a2e407927fa8c99e692b391d575b9f3e1f`），以下payload/导出文件SHA256与现有index一致；不表示它们和任意type22属于可证明同一发行批次：

| 表 | type / hash / pathID | payload SHA256 |
|---|---|---|
| QUEST_MASTER | 30 / 2988722424 / 8 | 0cc688c59a71bf58bdc9884fa4afc6528dc0f6cac72ec0443439d4c2d38637b1 |
| ENEMY_TABLE_MASTER | 21 / 458932175 / 25 | 4103df785607d4681a9ae182110fb62892975932243079d300aedcad295b20ff |
| ENEMY_UNIT_MASTER | 20 / 700614136 / 10 | 9c2941fd6cfe0a9e0e6b5baba44c6a73d14d6c239d16f51f915477f98b40d93f |
| UNIT_MASTER | 10 / 1104834672 / 20 | 2aea32f37f30bc2a5fbadf96c47c4c217cea610acba80c0bf3f3d9cd628bd638 |

ResourceManager 来源mainData SHA256为`f6c354bd726b4c1fc99baa0a454f1104f5cfa1e1370a5dd2f6fb6b6ff66ad0e7`。AudioClipManager与ms00_death_01的原缓存payload及当前离线transport文件均已重新计算SHA256，与manifest相符；这仅证明文件身份。

## type22：观察、选择及保留冲突

下列两份都为 code4096/type22，绝不是把名为 MAX 的文件当作另一种表：`MasterDataRTD/MASTERDB.cs:30` 明确 `MAX = ENEMY_DROP_MASTER`（22）。ResourceManager 同时收录两个不同路径。

| 标识 | ResourceManager 路径 | 协议 hash | 行数 | Data 文件 |
|---|---|---|---|---|
| A | database/enemy_drop_master | 861272216 | 1808 | f0f5d87be8f5824469c4b4dbac5a7e4f |
| B | database/max | 593280423 | 1939 | f26bd4b111d3a7442b775e2c299cf3c2 |

| 标识 | source SHA256 | payload SHA256 |
|---|---|---|
| A | ccbb718a1a21ee4d073da5bb0dc6c9b373f1a66d99aa58130145f2cdaed304dc | aca59f65d9f22a24dd91307a75337864ab05001c4e7f5afa804be845eaa20b25 |
| B | 81ee4dca14a36952f0b836de16b0867abfd3d69e9115eff17909966948deff97 | 2497da088518f74145bd51f27dd8ab01b24714b978778309ed5dcc050095b292 |

**观察**：A 的1808个 ID 都在 B 中，1792行完全相等，16行不同；B 另有30921–31051共131行。冲突 ID 为22228、22231、22232、22235、22236、22239、30715–30719、30873、30882、30891、30900、30909。差异包含掉落单位、概率和等级，不是仅添加行。例22232：A 包含15012/15013/15014/13120，概率50/20/3/2；B 包含13120/15013/15014，概率2/50/8。

**观察**：现有 ENEMY_TABLE_MASTER 共引用2411个不同非零 drop ID，A 缺1493个，B 缺1396个；这些是整份表的非零引用全集，不是已放行关卡的运行需求。B 覆盖较广仍不完整。协议 hash 是不透明版本标识，数值大小、文件名和文件时间均不能证明时间先后。

**有限选择建议（推断/本地策略，尚未实施）**：10001/11000的普通、boss、death全部掉落引用在A/B中均存在且逐行相等，可固定 A/hash861272216 为这两个候选的本地来源，依据是明确的 ResourceManager 主路径加候选引用逐行一致；B及16行冲突完整保留。不能把此选择扩展成“原服唯一权威版本”，不能混合两表后沿用任一原 hash，也不能以B行数多就全局替换A。版本先后及16个冲突的原服适用范围仍未知。

## type70 与413张地图

**观察**：`database/leveldata_list_master`→Data/`00b8d6a648d6b174a948c9cdb44a461b`，pathID1，hash797777103，269行。

- source SHA256：`9514c94e168f3a6e204b1c2c7a57962a0f59cffa6ef4c4b8f5948d075f12d46f`
- payload SHA256：`2ce629564ec288d1f3b4813af2ef2493f1ec18f79f879a2137fddb22275f249f`

269个清单 ID 全部包含于现有413张恢复地图；没有“清单列出但地图未恢复”的项，另144张恢复图未列入该清单。因此不是269对413的同键地图内容冲突，而是清单覆盖范围不同。现有 QUEST_MASTER 有1021关，其中608关没有对应恢复地图；不能由413张图推导1021关都可运行。

**有限选择建议**：保存原type70的269行及hash797777103，不把413个恢复ID合成一份仍使用原hash的清单；144张额外地图按单图provenance隔离保留。10001及11000两者均在原269行中，避免此次验收依赖清单外扩展。额外144张与清单的发行时间、适用版本未知。

## 固定候选及依赖

| 项目 | 10001 | 11000 |
|---|---|---|
| 选择依据 | 原教程下一关，open依赖10000 | category100、display_order0、difficulty1、非活动、open依赖10001；相邻11001同体力/距离，11002体力更高；固定最早普通关避免扩大测试面 |
| 体力 / 距离 / 人数 | 1 / 18 / 4 | 3 / 22 / 4 |
| 地图 / 格式 / 尺寸 | map1 / format0 / 8×31 | map1 / format0 / 9×35 |
| 地图 hash | 4081725474 | 45167553 |
| enemy_table_id | 10970 | 10000 |
| 普通槽 | 1–4 | 1–3 |
| 普通 enemy IDs | 12010–12013 | 10000、10100、22000 |
| 普通 drop IDs | 110–113 | 30195、30140 |
| boss_set / drop | 31010 / 0 | 31010 / 21096 |
| death_set / drop | 12021 / 114 | 41221 / 21000 |
| 挑战 | 无 | 10、11、12（后续需与领取生命周期一起验收） |

地图来源：

| 关卡 | Data 文件 / pathID | source SHA256 | payload SHA256 |
|---|---|---|---|
| 10001 | 82aed4de941062d4bbd14c8f53d8db7f / 1 | 57aabca94e615c8698274042869dc5d531ddd614867c615d09c6f380f2ee9dd5 | c2e61efc76f894b03debafe2aad22148ba768c5aaea89a5e06e4459ecaf6090b |
| 11000 | 0b48ccff3f789ba4aa1a5c1a2b0beed1 / 1 | 93e017e919e0ec50bb828d537b4e607fe9dcc72654115fb4f7f0efebec173859 | 52f61e4a76b651bc91b284f17e007ccaad7a56385959989d582fe248c504afd2 |

**观察：地图及普通敌人静态可解析**。两个关卡均map1，`LevelLoader`使用map-1，MapTable第0项为ground/object/sky=0，cliff/under=-1。ResourceManager确实能解析到`Level/GroundTextures/field_a_01`（Texture2D）、`Level/Background/bg_field_a_01_tree`及`Level/Sky/bg_field_a_01`（GameObject）。所有对应来源、SHA256与外部文件记录在固定资源manifest。

10001普通敌人都用`ms01_squ_lv1`及fire/water/holy/dark贴图；11000普通敌人为`ms01_sla_lv1`、`ms01_squ_lv1`及`ms00_tresure_unit_01`。这些模型及10001的`ms02_four_un_01`均列在`AssetBundleLoader.cs:88`的五个local模型名单中，并已经ResourceManager解析到真实GameObject/Texture2D。不要将“bundle inventory中没有普通敌人”误判为缺失：它们走Resources本地加载。

**观察：必须包含boss/death，不可只看地图普通槽**。`EnemyArrangeTable.cs:185`起构造boss/death记录，`:206`的GetUniqueEnemyList对全部非零enemy_id去重；`GameManager.cs:168`会为此列表加载资源，即使地图字节没有直接写入某个普通槽，仍不能忽略这两个分支。10001及11000都需要非local的`ms00_death_01`；已有精确匹配缓存及离线封装，其payload SHA256为`fd7bd0199ef65c1d2f8afd8ec6b9f4221f5705e6fd87a3b6cb8c3eed19829373`，transport SHA256为`b44bbc07fb1b93f94814844a319aa6d521fb36a46c9442cd652d96026ec63d1a`（`analysis/unity/ms00_death_01-transport.json`）。本次未实测加载。

**阻塞观察**：11000的death_set41221使用`ms01_sla_lv3`、`ms01_sla_lv3_fire`。该模型不在五个local名单，`AssetBundleDefine.cs:222`要求V1011 bundle；现有`bundle-names.json`及离线映射没有精确命中此模型，ResourceManager也没有其prefab/texture路径，只有相关方向动画。这里的“未找到”仅限已有索引覆盖，尚未证明所有原始备份都不存在。不能拿slime lv1替代、忽略此分支、或因同关普通敌人齐全而宣称11000资源已齐。

**观察：掉落单位数据存在**。10001掉落10020–10023；11000涉及10000、15012、10004、10014、10024、10034、11030（含boss/death）。都存在于UNIT_MASTER；其模型可在已有bundle inventory中精确匹配，group涉及11-20、21-30、31-40、41-50、161-170。具体队伍/helper尚未固定，不能只凭这些掉落模型覆盖就认为玩家队伍资源已完整。

**观察：效果静态入口存在**。候选敌人atk_ef_id主要为1（ef_damage），10001的12021为2（另需ef_fire_01）。ResourceManager解析到了ef_fire_01及ef_damage_01–04的GameObject。它们部分外部引用为`library/unity default resources`，这是Unity内建资源引用，普通磁盘exists=false不能直接判为缺失；需在目标Unity运行时验证。没有递归验证所有材质、shader、animation、UI/图标和场景序列化引用。

**观察：音频/玩家bundle仍是进入场景前置**。`LevelLoader.cs:93`先等待audio、player、enemy三段；AudioClipManager声明V1016，已有离线manifest payload SHA256 `be05c63635ad04bd13b8b1d6341b2c6f50cea90614f1055d71dee92a7c09a0c6`。前置已有首教程动态成功，但本次没有固定第二教程/普通关队伍、helper、所有所选技能与BGM2/3的运行加载证据。

`SaveDataManager.cs:218`的地图加载会在请求图不存在时回退11000；后续验收必须核对实际Record.level_data_id/hash，不能只看“场景显示出来”就认为正确地图已经加载。

## 扩展普通关候选与原始备份覆盖

复核脚本`analysis/battle_candidate_scan.py`读取现有表/地图与bundle inventory，对**303个ID≥11000、sp_event_id=0且已恢复地图**的关卡检查每个非零`*_set_id`，包括boss/death，完整结果及每个原始缓存文件SHA256保存在`analysis/unity/battle-candidate-scan.json`。

**观察**：只有12170、12206、13100、13232、11298、13102这6关的全部模型都命中local名单或已有缓存容器。仅11298为`kind=0/division10000`普通关，但两份type22都缺31536及32216；其type2通关前置递归链共120关（含目标），开头10000→10001→11000→11001→11002，末端11297→11298，且存在额外type4/type6条件。它不是简单、完整或能绕过11000资源阻塞的验收备选。

| 模型命中候选 | 类型/前置字段观察 | 掉落表检查 | 结论 |
|---|---|---|---|
| 11298 | kind0；120关type2链；map65，体力16 | A/B均缺31536、32216 | 普通关，仍不完整，不能替代11000 |
| 13100 | kind1000/division20000；type2=10000、type1=1；map1、体力10 | A缺30981–30984，B完整 | 特殊关，若另行授权可研究B版本验证，但不是普通关验收 |
| 13102 | kind1000；type2=10000、type1=1 | A/B均缺31206、31227–31229 | 不完整 |
| 12170 | kind1000，情人节名称；type6=1，map35 | A/B均完整且一致 | 特殊/季节关；未证明当前开放、地图依赖全加载 |
| 12206 | kind1000，白色情人节名称；type6=1，另type4/type5日期字段 | A/B均完整且一致 | 特殊/季节关，不能冒充普通关 |
| 13232 | kind1000；type2=13227，type9、自身ID、活动点及日期字段 | A/B均缺31428、31967 | 不完整 |

这里不擅自赋予type1/type4/type5/type6/type9字段原服语义。`UtilQuest.GetOpenQuest`依赖服务端下发active list；上表只证明主表条件字段，不能证明当前账号已解锁。**当前未发现同时具备地图、全部敌人模型及全部掉落行的可达普通关备选**；这使保留11000作为补齐目标更有依据，而不是跳过其death分支。

原始备份范围已进一步实查：

- `jp.co.acquire`树共有180个文件、282579649字节，均在`jp.co.acquire.RTD/files/UnityCache/Shared`下，为90个CustomAssetBundle与90个`__info`；没有额外hotupdate/Backup目录。已有bundle-names的90条恰好覆盖全部非metadata缓存文件，没有漏索引bundle。
- 对该180个原始文件逐份读取并保留SHA256；`ms01_sla_lv3`不在其中任何文件的明文字节中。结合容器inventory精确无匹配，证据强于“仅查文件名”，但仍不排除未取得的外部备份或未知编码内容。
- `archives/2026-10-24-phase1/phase1-workspace.zip`中的180个UnityCache文件与当前工作区逐项SHA256相同；没有额外缓存成员、没有不同版本。另一个checkpoint zip没有UnityCache成员。`device-account3.tar`成员表没有UnityCache/hotupdate/Backup路径。
- 原始APK Data的ResourceManager缺此模型/纹理，只有方向动画；已有`AssetBundleDefine`明确要求该非local模型的V1011 bundle。因此当前具体阻塞仍为原始`ms01_sla_lv3`及其fire纹理/依赖载体，不能通过重封装其他模型解决。

## 精确下一步与验收门槛

1. 在T11验收后，把上述A/hash861272216及原type70/hash797777103作为**限10001/11000**的版本决策输入；为导入另行记录实际主表envelope/hash一致性，仍保持普通战斗关闭。保留B及行级冲突，不混表。
2. 针对缺失`ms01_sla_lv3`定点扩大已有备份/缓存资产容器索引覆盖，记录每个覆盖根和hash；查到后须验证容器内模型、fire贴图、材质/动画依赖及V1011 URL映射。未找到则作为11000明确阻塞；不能合成替代品或把T12标完成。
3. 固定验收账号、队伍四槽与helper，按其unit.g_id和技能构造完整资源清单；加入AudioClipManager、map1、ms00_death_01、10001本地四属性敌人/12021、11000的41221及全部效果/UI依赖。对清单内每个对象验证实际Unity加载/实例化成功。
4. 用隔离验收环境依次跑10001、11000，保存请求的表hash/地图hash、实际level_data_id、全部加载URL/缓存版本/错误、boss/death预加载结果及截图。正式普通服务仍只允许10000，直到资源门槛与T13输入/快照实现共同验收通过。
5. T12 DONE须同时具备版本决策记录及**每个使用资源可加载**的证据；本报告仅收敛静态版本/候选，不满足后者。

后续实现更新：`analysis/recover_battle_masters.py`按上述source/payload SHA256恢复A及原type70，现已通过catalog导入。HTTP契约核对hash861272216/1808行、hash797777103/269行；原始冲突报告仍保留。服务仅新增10001的有界入场，未放行11000或其他普通关卡。

2026-10-25动态补证：测试账号1选择LOCAL_HELPER后，实际get_level_master及order_quest(10001)成功；请求地图hash4081725474、14张主表hash与本地一致。截图analysis/android/flow-runs/battle-entry-20261025/second-tutorial-first-dialog.png显示10001第一条教学对话、原始四人队伍和地图。AP从19减至18，15条敌人/掉落快照已持久化。此证据覆盖当前入场加载，不证明未遭遇的全部效果/掉落表现、结算或普通关资源已通过；T12整体仍未DONE。
