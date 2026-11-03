# 神月のケモノ本地修复记录

状态：代码默认关闭；2026-11-03经用户授权部署生产并启用、开放三难度。用户已确认进入关卡成功；完整战斗与通关表现未全部验收。

## 已实现

- 仅为20844、20845、20846补充缺失地图与12个掉落表；原始记录优先，后来找到真实数据时自动采用真实记录，不覆盖源文件。
- 路线位置、狼数量8/14/22、稀有史莱姆支路、掉落权重和Lv1均为推测，不能当作原版。原始敌人等级、属性、奖励、挑战和开放条件保留。
- 挑战22按原客户端规则检查 UNIT_MASTER.style，包含援军，并使用入场原始队伍快照。
- 獣王真实角色模型g01_kn_grt_fire_01已加入资源清单，保持原Boss41102。百獣王只作为上级掉落候选，不替换战斗Boss。

## 资源与临时替代

151-160.unity3d包含獣王，261-270.unity3d包含百獣王；文件SHA256与预制体Transform证据保存在config/shingetsu-character-assets.json。每种角色均有正常朝向和绕Y轴约180度的版本，两者带Animation组件；后者疑似原敌方形态，尚未实机确认动作与朝向。

角色Boss应同时检查角色包、敌人包与原始角色敌人加载路径。其他副本旧“缺失模型”判断需重新审计，未在本轮批量恢复或替换。

现有视觉兼容层在本关使用的临时替代如下（只在内存，不改属性和数值）：

| 敌人ID | 原始模型 | 临时模型 |
| --- | --- | --- |
| 10235 火影狼 | ms01_wolf_sh_fire | ms02_four_un_01_zako |
| 12107 中级银史莱姆 | ms01_sla_lv4_silver | ms01_sla_lv4_gold |
| 14230 火狼S | ms01_wolf_lv4，贴图ms01_wolf_lv4_fire | ms02_four_un_01_zako，贴图na |

这些替代不是原版外观；银史莱姆即使暂借金色外观，属性仍是原始无属性。关闭RTD_VISUAL_RECOVERY后可能因缺失资源而被资源审计拒绝，不代表原始配置被删除。

## 使用与产物

独立导出（输出目录必须不存在）：

```sh
python3 scripts/reconstruct_shingetsu.py --output resources/reconstructed/shingetsu
```

输出candidate.json包含新地图、掉落、来源标记和完整原始目录摘要，maps.txt提供ASCII地图预览。已生成的本地产物位于resources/reconstructed/shingetsu/，受resources忽略规则保护。source-file-sha256.json另记录439个源JSON的逐文件SHA256及导出前后不变核对结果。

试用服务端内存叠加：启动现有服务时设置RTD_SHINGETSU_RECONSTRUCTION=1；缺省为0。不会修改历史时间窗口，不能仅凭该开关进入已过期活动；也不会创建排期。原始前置仍为通关10000，日本时间2013-08-20 10:00至2013-08-22 10:00。

## 验证与限制

- `python3 -m unittest discover -s tests -p test_shingetsu_reconstruction.py`：10项通过。覆盖原值保护、真实数据优先、路线魂与击杀数、敌人抽样、史莱姆属性、原始开放条件、弓队含援军、默认关闭、独立导出拒绝覆盖、三难度入场结算及重试不重复奖励和上级首通虹石。
- 三难度协议测试只在测试作用域模拟开放条件，不修改生产开放逻辑；已过期和前置校验另有独立测试。
- `PYTHONPATH=tests python3 -m unittest test_event_recovery test_quest_content`：17项，16通过，1项既有失败test_unverified_content_requires_explicit_experimental_opt_in（20101可用性预期），先前日志有同名失败。
- 先前全量日志为283项、58失败、2错误，含当时尚未创建本模块的导入错误及既有图标环境错误；不是最终全量通过证明。
- `git -c core.whitespace=cr-at-eol diff --check`通过；现有服务文件使用CRLF，保持原换行。
- 未实机确认场景、狼替代外观、角色Boss朝向／动作、移动操作、死亡续关与客户端挑战回报；服务端验证不等于完整游玩验收。掉落概率不是考据结果。

## 2026-11-03生产部署与开放

用户明确授权部署并开放。生产同步8个代码／清单文件，不替换原始主表、地图源文件、配置或玩家数据库；systemd独立drop-in启用RTD_SHINGETSU_RECONSTRUCTION=1。生产角色包SHA256与证据一致。

活动ID shingetsu，三个难度20844/20845/20846立即开放，不设结束时间；排期通过Operations.update及revision冲突校验保存，revision 34→35。其他活动及卡池保持原值。原始历史日期保留在源主表，仅对本地排期下发的主表副本覆盖日期／停止条件；通关10000前置保留。

部署前发现旧排期不会更新神月客户端主表，因此补充仅针对这三关的排期支持。新增测试先因hash不变失败，修正后验证不mock入场、前置保留、关闭标记及源表不变。神月专项11/11；活动和排期组合20/20；生产Python神月专项11/11。独立增量审查无Critical/Important。Minor暂缓：关闭测试核对客户端停止标记，尚未直接尝试关闭后的入场，通用关闭逻辑已有旧测试。

备份目录：生产backups/shingetsu-20261103-000651，包括代码归档、部署前SQLite一致性快照和停API后的快照，完整性检查ok。停服期间核对players与quest_runs全部行逐值不变。只重启API，资源服务保持active。8文件部署SHA256核对通过。

首次用回环地址探测健康未命中（生产绑定其他地址）；改用现有配置绑定地址后HTTP200、status=ok。两个服务active，运行API进程已确认环境开关为1。未使用真实玩家账户进行测试，未重新构建APK。玩家重新登录／重启游戏获取更新主表；客户端实机验收仍待完成。

## 2026-11-03读取卡住：书本依赖404

生产日志显示客户端get_level_master成功后，在角色敌人加载阶段反复请求/Android/V1011/ms00_book_el_05.unity3d并得到404。原客户端LoadEnemyAssetBundle遇下载失败会回退循环索引重试；獣王symbol14通过UnitEnemySymbolToBookColor映射为5，加载该地图书本包，然后独立加载151-160角色包。此前只核对角色本体的审计不足，已补充AGENTS约束。

原APK、恢复bundles/cache名称清单中未找到原书本模型。按用户已有“确实缺失资源可临时替代”授权，生成独立推测包：以原151-160包内path609为临时兽王地图标记，发布客户端要求的ast_ms00_book_el_05预制体名；地图书本暂显示兽王外观，不宣称恢复原版书本。实际战斗仍用原角色包，不修改敌人主表、属性或战斗数值。派生包使用独立内部序列化文件名，避免与真实角色包并载时同名冲突。

复现生成：scripts/reconstruct_shingetsu_book.py；需要离线工具UnityPy。输入SHA256、原预制体ID、派生SHA256和内部文件名见config/shingetsu-book-marker.json。生成器拒绝覆盖任何已有目标。UnityPy专项先因实现缺失失败，再通过；最终1/1验证资源名、Animation组件、原文件不变、拒绝覆盖、原生bundle格式保持以及内部文件名与原包不相交。独立审查无具体阻塞问题；仍不能以静态解析证明Unity运行时成功。

生产已添加原先不存在的resources/bundles/ms00_book_el_05.unity3d（612227字节），实际原请求URL返回HTTP200且内容SHA256匹配；原151-160包SHA256保持不变。审计目录backups/shingetsu-book-20261103-002751。未重启任何服务、未改数据库或战斗记录、未修改客户端APK。原始依赖加载证据归档在本地/tmp/rtd-shingetsu-original/book-loading-evidence.json。等待客户端重试以确认下一加载阶段及实际渲染。

## 实机结果与归档提交

2026-11-03用户确认补充缺失书本依赖后成功进入关卡。此结论仅覆盖进入关卡，不扩展为所有难度、完整Boss战及通关奖励均已实机验收。源资料与推测继续区分；本次按用户要求整理提交到远端。

书本派生包不纳入Git，随resources目录保持忽略。可使用独立离线环境安装UnityPy==1.25.4，再运行：

```sh
python scripts/reconstruct_shingetsu_book.py \
  --source resources/bundles/151-160.unity3d \
  --output resources/bundles/ms00_book_el_05.unity3d \
  --report /tmp/shingetsu-book-generated.json
```

输出与报告路径必须不存在。预期SHA256见config/shingetsu-book-marker.json；已有真实文件不得覆盖。该离线工具不是生产服务运行依赖。生产配置、环境开关和活动排期属于部署状态，未将真实连接信息或数据库提交仓库。

提交前验证：使用生产Python和离线UnityPy工具，运行神月、书本资源及现有活动／排期相关测试，21/21通过（test_shingetsu_reconstruction、test_shingetsu_book、test_live_operations、test_layer_operations）；106组归档正文SHA256再次核对一致。原始HTML保持逐字节归档，Markdown保留必要硬换行。敏感信息扫描和逐项审查不包含任何生产数据库、凭据或实际服务连接配置。
