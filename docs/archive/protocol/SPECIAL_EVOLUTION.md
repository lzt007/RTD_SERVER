# 特殊强化与究极进化

原DLL：`c83aea19ee65ae973815daf6a04e430d9e87b8426b6180c1fe507e4260763ecc`。本轮REA元数据证据见内容扩展设计，规则参照原`MMUnitSpComp`、`MMUnitEvo`与`ComManager`导出；客户端验收另列，不能以接口测试代替。

## sp_compose_unit

请求：`ver="2.4.0"`、`retry`、`dst_unit_instance_id`及**单个整数**`src_unit_instance_id`。成功响应保持原DTO：`{"code":4096,"session_id":"…","result":[]}`。

素材主表`material_type`20/30/40分别增加目标`bonus_life`、`bonus_attack`、`bonus_heal`一个**计数**。单次费用为`(life+attack+heal+1)*25000`；上限为`bonus_limit_base+bonus_limit`。50分支增加`bonus_limit`一个，当前主表没有该类素材，不伪造新单位。计数不等于直接增加一点HP，实际属性换算仍由原客户端和全局参数处理。

目标须普通单位；目标与素材必须持有且不同。收藏素材和任一编队前三主槽受保护；消耗素材后清除其副槽引用。保持目标等级、经验、属性经验、收藏、实例及其他元数据。金币不足、满上限、错误素材均不写入。以目标/素材实例组合保存回执，重试和重启不重复扣费；材料实例不复用。

## ultimate_evolve

请求：目标实例、1–4个唯一素材实例数组、`ultimate_evolve_attribute`；**没有add_point字段**。原协议属性值2/3/4/5分别映射主表`ultimate_rev_unit_id_fire/water/shine/dark`，与客户端内部属性枚举不同。缺失分支拒绝，不能退回普通进化。

目标满级，`attribute_exp>=max_attribute_exp`；普通素材点数总和满足`need_pt`，金币费用`need_pt*100`。素材点数使用既有float32算法。收藏/编队主槽/特殊素材及携带bonus或属性经验的素材保护沿用普通进化。目标保持实例、编队、收藏和bonus，变更单位类型后`level=1, exp=0, attribute_exp=0`。图鉴更新、消耗、费用和带属性分支的回执在同一SQLite事务。

## 测试与范围

`server/test_special_units.py`覆盖三类强化、费用递增、保护/上限/非法输入、究极属性分支、缺失分支、属性阈值、实例保留、重启回执、并发及写失败回滚。独立测试存档位于`analysis/android/flow-runs/content-expansion-20261026/`；准备的单位、等级、属性经验与金币是明确标记的UI测试夹具，不能作为正常玩法产出证据。

2026-10-26 原客户端菜单经 Android MCP 实际验收：实例1038使用15025素材，预览/结果HP1250→1650，生命bonus计数0→1，消耗25000金币且素材删除；实例900001的16500满级/满属性夹具使用15532素材，预览819点满足500点，选择火分支后变为16501、等级1、经验及属性经验0，消耗50000金币且素材删除。两项均由客户端发出请求、服务端返回4096；客户端和API重启后46单位、1925000金币及两目标状态一致。证据为该目录下`before/after-special.json`、`before/after-ultimate.json`、`special-restarted.json`和对应预览/结果截图。此验收不涵盖正常战斗获得属性经验。

源码已新增本地活动掉落`attribute_exp`及有界原子结算，见`docs/api/ADMIN_OPERATIONS.md`和`docs/protocol/ATTRIBUTE_EXP_RESEARCH.md`。默认数量0，不猜原服数值。

2026-10-26新增战斗获取闭环，隔离库`analysis/android/flow-runs/content-expansion-high-level-20261026/`：准备16500/Lv50实例900301和15532/Lv99素材900302，初始属性经验均0，未添加金币/AP。通过后台HTTP显式配置11000每敌5000本地属性经验；原客户端flow20261026-184935实际胜利，报告none5000/fire30000，其余0，目标达到原上限5000，零上限队员与助手不加算。原请求重试后六账号和回执不变，API及客户端重启完整状态一致。随后Android MCP原菜单选择火分支2、819素材点满足500点，原`ultimate_evolve`返回4096：同实例16501/Lv1/exp0/attribute_exp0，删除900302，2026400→1976400金币，单位55→54。证明正常战斗获取经验可满足进化条件；不证明起始满级单位、素材自然取得或本地经验数量是原服数值。

证据：`attribute-exp-fixture.json`、`attribute-exp-earned.json`、`attribute-earned-restart-before/after.json`、`attribute-before/after-ultimate.json`、`attribute-ultimate-preview/result.png`。进化后第二次完整API及客户端重启也通过，`final-restart-before/after.json`核对六账号、54单位、1976400金币、配置revision26、41关卡记录及24回执；状态摘要SHA256为`9cb77e8533292e55319fb2bedd3f239f084178f073cc5be9f7ec0685a1503f5a`。
