# 角色型Boss修复参考核对

核对日期2026-11-05。已修正离线动作验证器，并于本轮同步生产工具、文档及审计元数据；未改模型资产。发布验证见model-audit-deployment-20261105.json。

## 兽王可复用证据

- docs/superpowers/specs/2026-11-02-shingetsu-reconstruction-result.md:10-14：41102獣王保持原记录，g01_kn_grt_fire_01在151-160；百獣王g02在261-270。两套各有正常方向及Y轴180度版本，敌方版本尚未实机确认。
- config/shingetsu-character-assets.json：151-160 SHA256=8ee34859e01f71985f023f255933c838ff30da80848cf0efd0cdc9bda6b5dac8。兽王普通path128；敌方疑似path609，根scale(1,1,.01)、rotation(0,1,0,0)，两者有Animation。
- 原DLL证据 /tmp/rtd-shingetsu-original/book-loading-evidence.json：Assembly-CSharp SHA256 cd8969401672485c95dbc8336864bfe54a1bfce242f4048b32341a2ab0953ac2。引用EnemyArrangeTable.GetUniqueEnemyList与原LoadEnemyAssetBundle协程。
- 文档:63-69实际HTTP缺口是ms00_book_el_05，不是151-160角色主体。symbol14映射书本5；旧加载失败回退索引重试。

## 正确加载链

loading-chain/loader-definitions.tsv的U类型为22,24,30,31,33,37。角色身份由EnemyData.IsUnitEnemy/原type决定，而不是名字有没有ms。

audit_loader_requirements.py:30-34 已提炼原链：symbol10..15映射book1..6，其余6；角色先加载ms00_book_el_0N。chara_g_id>0，角色分组 start=((g_id-1)//10)*10+1，下载start-(start+9)；g_id<=0则独立模型包。版本和URL从B定义查，不硬编码所有资源版本。分组容器可能含同名正常/敌方导出，必须检查原ResourceLoad实际选取路径、方向、Animation及引用闭包，不能用名字首次命中代替。

## 扫描盲区及潜在回退路径

rtd/policies/event_visuals.py:13只以ast_ms构造候选；34-40按前两段猜family，无匹配退野猪ms02_four_un_01_zako。角色实际在数字分组包，仅用旧普通模型清单判定存在潜在误判风险。root已对最新生产有效主表核对：185条非ms敌人model/texture与原表相同，因此不能声称这些角色当前已被此路径退成野猪。恢复时应回原记录model/texture，保留type/chara_g_id/symbol与数值，先验证角色包/书本/动作/特效整体依赖。不能只增加ast_别名。

## 书本工具应选择新版

scripts/reconstruct_shingetsu_book.py文件头明确为历史复现，禁止再部署旧兽王外形地图标记。当前应复用scripts/prepare_event_reconstruction_resources.py和reconstruct_gacha_book.py生成原抽卡书本图集的推测平面标记（仍非原地图书本模型）。需确认生产优先目录原包不会遮住新版重建层。

## 首批具体对象

同兽王151-160包且symbol14→书本05：41073恶食王クトゥール(g_id154)、41104骑士王155、41106隐王156、41108料理王157、41110英雄王158、41080机王159、41112冥王160。它们最适合先作实机依赖验证：角色主包和共享书本已有工作参考，不需人为扩大种族推断。其他161-170组含41114猟王161、41116海王162、41118铁王163、41075处刑王164、41120罪王165、41122教王166、41124精灵王167、41100书王168。本轮主审计已确认全部所需角色组包文件及HTTP路径存在，不再把这些分组当成当前缺包。

## 未确认事项

本核对未新运行Android客户端，不能宣称朝向、待机/攻击、特效和释放已获实机验收。必须针对真实角色选择路径解析闭包、动画与效果对象，当前保存加载证据并不足以替所有185条非ms敌人作全量动作与特效绑定结论。角色分组包有正常方向模型不等于存在敌方面向版本，容器同名多条不能简单set去重。

## 41317 オル・ガディア实际加载补证

原type33、kind6、symbol15、gid0。/tmp/resource-original-fresh.il:101270 ChangeUnitEnemy：gid0分支IL00b2-00d1读取`ast_`+PrefabName，因此原包已有ast导出是正确的，不需盲加plain/_e。gid>0分支IL0147从数字DLC组包取对象，IL0156按plain PrefabName直接Load。二者统一IL0183后镜像root.x、强制root.z=.01并置y=.6；不能把源包180度副本直接当必需敌人模型。

ChangeUnitEnemy IL0257-02c4加载Resources AnimationData/DirectionAnimation/el_boss_tob（PT_NUM=6追加_6），直接调用root.animation.AddClip(toBattle)，因此模型根节点必须有Animation，只有move子节点Animation不够。

原APK catalog已经具有Resources绑定和真实AnimationClip：org_wait_swd_01(file277:0/path1)、org_atk_swd_01(662:0/path1)、ms03_org_run_01(621:0/path1)、el_boss_tob(597:0/path1)、el_boss_tob_6(732:0/path1)。转换器以ms03_sen前缀猜动作所得not_present_in_original_apk是假阴性，应按type33原MotionAssign映射修复。

41317 atk_ef_id10由原E表解析为ef_atk_blade_02_ms，sub为空。原APK具有Resources绑定prefab/particleeffects/ef_atk_blade_02_ms及真实GameObject（file1839:0/path3），因此不能判定原资源缺失。

## Orlgadia原动作骨架核对与最小修正

scripts/audit_orlgadia_motions.py从原APK逐一解析实际AnimationClip曲线，再与当前转换包实际Transform树比对；结果见orlgadia-original-motion-audit.json。wait/attack各19条路径全部匹配move层级；el_boss_tob及_6仅操作根路径，均匹配。根Animation存在，原ChangeUnitEnemy会重新AddClip(toBattle)，因此源包嵌入ms02_four_tob不能单独证明错误动作。

run的左右脚踝曲线拼成anckle，而模型及wait/attack拼成ankle，产生两条不匹配。未改骨架或曲线：原IL中直接调用CharacterAnimation(Run)的这一战斗分支限制type16，不是type33；尚无证据该角色使用此run clip。不得为了此未用分支破坏已匹配的wait/attack。

通用验证器现仅对精确model ms03_sen_olgadia_01选取原type33的org_atk_swd_01、org_wait_swd_01，要求两者都确实来自原APK，并记录original_motion_clips；其余模型维持既有路径。旧验证器按ms03_sen猜名得到not_present_in_original_apk，已由失败测试复现。本次不需要修改任何模型、贴图、朝向或动画资产，也不等同实机验收。
