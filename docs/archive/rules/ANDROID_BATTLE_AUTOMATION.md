# 安卓原界面战斗自动化

`analysis/android/drive_startup.py`使用Android MCP点击观察到的菜单、楼梯、失败处理及技能按钮。Unity界面大多没有原生无障碍元素，位置来自只读RTDFlow组件观察与截图；连面板沿用连续触摸助手RTDInput，输入不修改生命、Soul、坐标、敌人或战斗结果。只运行一个输入控制器。

## 多层路线

先在原客户端选择活动区「超古代遺跡の秘法」，再启动：

```powershell
. ./enter-env.ps1
python analysis/android/drive_startup.py --goal main-menu --quest-id 20000 --next-floor-id 20131 --battle-skills --battle-failure exit --timeout 1800
```

`--next-floor-id`仅支持原入口20000的六个实际出口：20100、20131、20122、20103、20120、20110。路线依据原地图hash、宽高、实际坐标、观察到的面板方向与横向环绕规则选择面板；其他已知楼梯点原NO，目标点原YES。地图不符、已越过全部目标、错误子关或没有可确认按钮时停止，不传送、不强制入层。子关不能直接开始新运行，只允许指定`--resume-battle`恢复已存在战斗。

根层优先搜索当前已观察手牌的完整路线，每张面板最多使用一次；只输入第一张，随后重新观察。战斗会消耗其他手牌，因此非末张经过原遭遇格后不再预测旧牌；当前移动牌仍按原客户端继续其剩余箭头。没有可证实完整路线时回退保守选择，随机补牌仍可能导致楼梯不可达，此时停下留证。20103另按原地图和整张面板的中间格绕行可选遭遇，保留31行原Boss区与36行原最终Boss；不保证最优打法。六出口均已有实际胜利及最终完整重启证据，详见`docs/protocol/MULTI_FLOOR.md`。

路线优先提前横向对齐楼梯，不能在未命中目标时落到最后一排楼梯行的错误横向位置：随机面板可能全部带向前箭头，无法再横移到楼梯。无可确认路线时保持停止，使用原菜单放弃后重新从入口付费，不越过目标后伪造转层。

## 主动技能

`--battle-skills`为显式启用选项，不影响被动战败夹具。技能取运行中的`CharacterData.m_AsMaster`，不能直接把`UnitMaster.a_skill_id`当技能ID：原`ClientData.GetActiveSkillMaster`先查等级分段表，再取实际技能。

- 原HealLife1/2：生命低于55%时，点击原`CheckSkill`判定可用的图标，再核对实际技能ID、队员位置、类型、原确认按钮与费用；保留至少1 Soul。
- 原Acute、Enhance、ColorEnhance（type12/13/36）：最终Boss，或已观察敌人最大生命达到队伍最大生命2倍的普通格强敌，可使用增攻；观察原`AttackWeaknessUp`、角色`AttackUp`或`m_ColorEnhance`判断是否已经生效，生效后不重复消费。初始5倍阈值遗漏20103生命97412的高防御水蟹12316，已用实测回归修正；阈值仅是输入策略，不修改敌人数值。
- 原DefenceDown（type8）：仅观察到敌人原`Defence>=5000`且`DefenceEnhance==0`时，通过原UI施放一次。初始1000阈值对1222/1988防御的普通敌人耗费过多Soul，已由实测回归收紧。原技能会累乘减少当前防御，因此任何负的防御修正均阻止再次购买，包括恢复同一敌人后。缺失防御观察、已有降防、低防敌人不猜测；原技能仍自行计算减防比例和扣Soul，观察器不写防御字段。优先级为必要回血、降防、增攻、面板。
- 普通格增攻另需至少11 Soul才打开技能弹框，并按原弹框实际费用检查施放后至少剩5 Soul，保留本轮4 Soul回血的可用余量；未知高费用会受控停止，不擅自确认。最终Boss不使用此普通格预算门槛。该启发式不修改技能费用，也不承诺任意队伍最优策略。
- ColorEnhance按原`GetMainAttribute(true)`及`ConvertClientToServer.ConvertAttribute`转换后的当前战斗属性判断适用性。客户端枚举与服务器属性编号不同，不能直接比较整数。
- 弹框动画期间不连面板；未知技能、身份或费用不符、按钮缺失时停止。合法多次回血以生命、Soul、弹框及效果区分进度，不把每次相同的空面板界面累计为同一次重试。

同类连面板不消耗Soul；低生命优先心面板。已观察到个人增攻生效时，提高对应武器面板的选择优先级；这是输入启发式，不替代客户端伤害公式，不保证任意等级队伍能通过所有关卡。胜负来自原客户端，败北不会被当成通关。

## 验证

```powershell
. ./enter-env.ps1
python -m unittest discover -s analysis/android -p 'test_*.py'
dotnet run --project analysis/SkillObservationTests
```

后者直接运行与RTDFlow共同编译的属性转换辅助函数，覆盖火/水交叉和战斗中属性变更。原始APK/DLL不修改；`build-rtd-local-client.ps1`构建独立观察包。兼容启动器退出时恢复设备上的原APK，必须等待日志确认原SHA恢复后再启动下一次，不能直接杀兼容启动器。
