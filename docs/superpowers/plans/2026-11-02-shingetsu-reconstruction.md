# 神月のケモノ缺失数据重建 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 为 20844–20846 生成独立、可核对的缺失地图及 12 个掉落表补全候选，严格保留全部真实数据。

**Architecture:** 使用生成器读取原始 catalog，独立导出候选包，并通过默认关闭的 RTD_SHINGETSU_RECONSTRUCTION=1 将缺失地图／掉落叠加到内存目录。已有记录优先，不修改源资源文件，不自动重开历史副本。仅确实缺失的资源允许保留证据的临时替代。

**Tech Stack:** Python 3 标准库、现有 unittest 与 battle_generation。

**Spec:** docs/superpowers/specs/2026-11-02-shingetsu-reconstruction-design.md；用户新增原始数据不可修改要求优先。

## Global Constraints

- 原始记录、字段与资源引用一律不修改；史莱姆保持无属性。
- 仅缺失的地图、掉落表可补；零值和空掉落不视为缺失。
- 路线、掉落权重、掉落等级标为估算；不写入原始 resources/master-data 和 resources/level-data。
- 本地候选包与显式启用的内存叠加；过期日期、原始前置不绕过。

## Review Focus

- 将来找到真实地图／掉落时，应采用真实记录，停止生成对应估算。
- 原始 death_id=0 为实际 Boss；boss_id=99 为惩罚死神，禁止互换。
- 地图尺寸要与客户端初始距离一致，终点应可达。
- 挑战击杀数与魂值需要可达路线支持，不以响应中的怪物总数替代路径分析。
- 缺少原始模型应如实报告，不能因离线协议测试通过就宣称可实机游玩。

### Task 1: 原值保护与候选生成

**Files:** Create scripts/reconstruct_shingetsu.py; Test tests/test_shingetsu_reconstruction.py。

**Interfaces:** build_candidate(masters, levels) -> dict，输入不变；返回 levels、drops、provenance、original_records_sha256。apply_missing(masters, levels, candidate) -> (masters, levels)，深拷贝，按 ID 只添加缺失记录。

- [x] 写失败测试：所有原始表／地图不变；史莱姆与 Boss／狼保持原属性模型；三张地图初始距离 18／23／30；12 表候选引用合法角色，权重≤100；已有真实地图／掉落优先；原始空掉落0保留。
- [x] 运行 unittest 确认因生成器未实现而失败。
- [x] 实现离线生成器及 CLI，显式标明估算：普通狼掉落仅火素材候选、单次20%／30%；Boss 角色1%／3%／5%，其余素材79%／77%／75%，剩余空；初中稀有素材100%；上级金史莱姆炎火80%、悪い20%；上级Boss炎火65%、超悪い10%、百獣王5%、空20%。所有单位Lv1。以上均为可调整推测。
- [x] 地图使用9列、起点(4,4)、height=distance+14；关底行 height-10 全行A0、出口行height-5全行C0；中路放8／14／22只原表狼，支路放一只原表史莱姆。没有原图证据，全部位置明确为估算。
- [x] 跑测试通过，核对最少击杀与魂条件存在路线；生成包不得覆盖已有目录。

### Task 2: 离线协议与开放条件验证

**Files:** 同上测试文件；产出 resources/reconstructed/shingetsu/。

- [x] 写失败测试：中路可达、怪物坐标不碰起点／关底／出口；入场抽样真实 Boss ID、火狼与无属性史莱姆正确；掉落可按现有协议生成；日期过期时拒绝入场，单独本地排期仍要求10000前置。
- [x] 使用原始客户端 CIL 确认地图解码、距离、Boss等级成长；记录中上Boss攻击分别5572和13930，维基5906/15000不覆盖原值。
- [x] 生成 JSON 候选包、逐字段来源、ASCII 地图预览、原始记录哈希及资源阻塞报告。
- [x] 完成专项回归和原始资源目录哈希比对；更新结果文档，不提交／推送／部署。

## Execution ledger

- 用户已指示“其他的继续”，在当前会话顺序执行，不再次要求许可。
- Ruling: 已撤销“兽王模型缺失”的判断：角色包含真实模型。原始引用保留；用户允许仅对确实缺失的资源临时替代。误判成本为错误外观，因此先查角色包。
- Ruling: 根据原客户端证据支持挑战22，按原始 UNIT_MASTER.style 检查入场队伍及援军，不修改挑战主表。误判成本为错误授予挑战，专项覆盖援军不符和缺失快照。
- Ruling: 用户要求继续修复，增加默认关闭的内存叠加开关，原始文件不变、历史日期仍有效。误判成本为本地试用行为变化，默认关闭并单测保护。
- 2026-11-02：已实现地图／掉落生成、原值优先、类型22和API开关；CLI覆盖已有导出时拒绝。继续协议验证与最终审查。

- Task 1: complete — 原值保护、真实数据优先、三地图与12掉落、CLI拒绝覆盖；专项10/10。
- Task 2: complete（本地协议范围）— 三难度入场、结算、重试、上级首通、过期与前置；439源JSON导出前后不变。实机验收与发布不在完成声明中。
- Final review: fresh reviewer review_shingetsu，未发现Critical／Important；独立运行专项10/10。Minor为计划旧接口status未实现，已将计划接口修正为实际不含status，运行时无消费者。
- 回归：相关旧测试17项中1项既有失败（20101可用性预期），与先前全量日志同名，不修改无关逻辑。全量不宣称通过。
- 下一阶段：实机验收、其他角色Boss资源再审计；未部署、未重排期。详见2026-11-02-shingetsu-reconstruction-result.md。

- 后续授权：2026-11-03用户要求部署并开放，已执行；缺失书本依赖补充后用户确认进入成功。随后授权整理提交和推送。上述“未部署／不提交”仅为早期阶段边界，最新状态见结果文档。
