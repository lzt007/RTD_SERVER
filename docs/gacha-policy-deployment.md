# 本地重建卡池规则与生产部署

这是本地设计，不代表原服历史概率。当前角色主表751条：素材40，关卡可得普通角色及四个初始角色合并排除201，其余普通角色510。

- 友情10000/30000：40素材合计90%，510普通角色合计10%；各组内等概率，每次独立抽取，十连无保底。每素材权重459，每普通角色权重4。
- 稀有20000：510普通角色等概率，无素材。所有结果等级1。
- 费用不变：单抽100友情点、十连1000友情点、稀有5水晶。
- 新教程首抽同样使用稀有池；已有教程首抽回执保持有效。
- 素材明确列在rtd/policies/summon_catalog.py的MATERIAL_IDS中；material_type只能辨识DX素材，不足以完整分类。
- 对全部已恢复关卡的敌人表及死亡怪/首领掉落、首通单位奖励、挑战单位奖励进行排除，不受开放状态限制。类型20/21为场景对象而非角色掉落。概率为0或累计概率已满的掉落槽不算可获得。
- 各进化形态按独立角色ID判断；没有因基础形态可掉落而连带排除所有进化形态。
- 未恢复的历史途径无法推定。逐角色ID及关卡来源在gacha-classification.json。运行时活动增加额外角色掉落时，迁移会报错停止，避免静默违反规则。

## 生产替换文件（以RTD_SERVER为根目录，保持目录结构）

1. config/local-gacha-pools.json
2. rtd/policies/gacha_pools.py
3. rtd/policies/summon_catalog.py
4. rtd/operations/configuration.py
5. rtd/services/rewards.py
6. scripts/apply_gacha_policy.py

可选保存 docs/gacha-policy-deployment.md 和 docs/gacha-classification.json 供审计。
不需要替换rtd.config.json、任何鉴权文件、角色主表或客户端APK。不要用本地数据库覆盖生产账号数据库。

## 执行

停止生产服务，在RTD_SERVER根目录，用生产服务使用的Python执行：

```sh
python scripts/apply_gacha_policy.py
```

数据库位置默认读取当前生产rtd.config.json的paths.database；也可显式传入：

```sh
python scripts/apply_gacha_policy.py --database /absolute/path/to/rtd.sqlite3
```

脚本先创建SQLite一致性备份（原数据库名.gacha-时间.bak），再原子更新已有数据库三个卡池的entries，并增加revision。保留卡池开放时间、启用状态、名称、活动、玩家数据和回执。再次执行无内容变化时不再增加revision。默认JSON只影响新数据库，已有库必须执行该脚本。

成功应输出counts为total=751/materials=40/excluded=201/eligible=510，changed首次应为true。之后启动服务，在后台确认10000/30000各550条、20000为510条。若主表版本不同导致默认文件不匹配，脚本会停止，需重新整理而不能强行应用。

回滚：停止服务，恢复六个旧文件及脚本生成的数据库备份，再启动。数据库回滚应在重开服务前完成，以免丢失更新后产生的账号进度。

## 验证记录

包含精确90/10权重、完整分类与初始角色排除、单抽/十连、余额扣除、教程首抽回执、运营配置持久化和迁移幂等的针对性测试。
全量测试在现有工作区另有后台鉴权401及Windows临时SQLite文件占用失败；未修改这些无关功能。
