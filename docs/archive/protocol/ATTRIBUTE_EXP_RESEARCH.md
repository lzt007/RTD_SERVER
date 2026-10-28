# 属性经验恢复研究（本地配置获取已实机验证）

特殊强化和究极进化的提交、费用、材料及存档已实现；新增原客户端战斗获取本地配置经验→重启→究极进化闭环。起始等级与材料仍为隔离QA夹具，不代表全自然养成链完整。

原客户端静态证据：Assembly-CSharp.dll SHA256 `c83aea19ee65ae973815daf6a04e430d9e87b8426b6180c1fe507e4260763ecc`，REA成员证据 `ev_a1929c1b0e11e1f156fa780bdcce11cbd0e99abaeafc1bbba79d301ef574e53f`（Party、PlayerData、BattleManager、ComManager；仅静态解析，无执行）。既有反编译参考显示：

- `BattleManager`击败敌人后，取已下发的`EnemyInfo.add_attribute_exp`，按敌人原属性传给`PlayerData.AddAttributeExp`与`Party.AddAttributeExp`。
- `Party.AddAttributeExp`跳过助手；己方单位原主属性相同得到两倍，否则一倍，并受原单位`max_attribute_exp`限制。临时属性不参与。
- `PlayerData`分属性累计，单属性上限999999；`ComManager`提交none/fire/water/shine/dark五字段，使用原客户端属性编号映射。

当前恢复的master22有1808条记录，全部**缺少**`add_attribute_exp`字段，不是显式写有零。原模拟实现以`drop.get('add_attribute_exp',0)`回退且拒绝非零结算；因此不能把零值当成原版掉落概率或经验数量的证据。限定搜索`analysis/master-data`及已迁移游戏files目录的JSON/XML未找到包含此字段的掉落记录；未据此宣称所有二进制缓存均无数据。

后续应先寻找原掉落数据版本及数量来源，再以入场敌人快照约束可报告的分属性累计、整链原子更新己方三个实例、上限、重试和重启。若原数量确实无法恢复，可另行提供明确标记的本地配置，但不能默认为历史原值。当前多层六出口与下一批普通关验收先继续，运行服务未因本研究切换。

补充缓存审计：对`analysis/unity/bundle-names.json`列出的全部90个缓存包，UnityPy读取成功且无异常，TextAsset数量为0；没有另一份type22主表或包含`add_attribute_exp`的TextAsset。机器报告`analysis/unity/attribute-exp-cache-audit.json`。此结论限于该90包的TextAsset，不把任意二进制内未识别结构等同于不存在。

后台新增可选活动掉落`attribute_exp`，默认0，明确是本地数值。入场冻结分属性上界、三个己方实例/身份/属性/上限，多层逐层快照；结算按原同属性双倍更新并共享原事务和回执，助手不加算。定向11项覆盖重启/重试、后层及末尾写失败回滚、真实好友不变、上限和非法报告；全量157项回归通过（102.996秒）。旧战斗结束后，API已切换到完整实现与135条视觉清单；零经验11000原客户端实战胜利已通过。

隔离QA的非零经验已完成原客户端真实胜利、原请求重试无重复、六账号/配置/回执完整重启核对，以及原菜单究极进化提交。5000是明确后台指定的本地每敌数量，初始等级与材料为QA夹具、初始属性经验为0，无新增AP或金币；不能宣称原服数量已恢复或起始资源自然取得。详细数值、边界与证据见`SPECIAL_EVOLUTION.md`。
