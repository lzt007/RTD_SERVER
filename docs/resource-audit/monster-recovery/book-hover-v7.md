# 书本悬浮 v7

用户要求保持大小，略微上移并轻微浮动。原APK AnimationData/DirectionAnimation/el_wait（assets/bin/Data/26595f22f2533e947a90160e552b4934）为1.5秒循环、Y=0..0.100869的书本待机，原始路径为空。Enemy.SetEnemyParameter在找到BOOK_SYMBOL渲染器时给move的Animation添加该clip；同时会按属性改材质颜色。现有替代不依赖新增BOOK_SYMBOL标签，以免对原抽卡图重新染色。

复用原曲线不改关键帧和切线，仅把绑定路径从空改为move；作为本包独立AnimationClip1301，根Animation1300默认自动循环播放，作用于move骨骼，而不是地图定位的根Transform。move保留Animation与控制器契约，根Animation也继续满足Enemy.UnLoad访问clip及清理的契约。根Animation可以承载这种播放，但之前补空组件的直接原因是释放路径，不是已经存在悬浮效果。

底部Y=.49→.59（额外上移.10），宽.505、高.68不变。浮动范围0..0.100869，包围盒覆盖完整浮动范围；所有六色统一处理，独立CAB身份。首次回归在旧包失败：缺少1301及底部仍为.49。实机浮动效果及与运行时动画混合仍待确认，不能以UnityPy结构验证当作实机通过。

验证：4项通过（89.078s），六色动画曲线逐项等于原APK（仅path重定向），贴图/骨架/move Animation原始字节不变。发布七处生产文件，六路径HTTP哈希匹配，API及服务健康，有效配置与其他资源保持不变。已备份，未完成v7实机验收。

## 用户实机反馈：未观察到悬浮（待解决）

2026-11-05，用户反馈：“仍未观测到书本上下移动。”因此v7悬浮效果未获实机确认，记录为未生效／待排查，不得以曲线存在、自动播放字段、结构测试或生产HTTP哈希通过宣称悬浮已实现。

反馈未明确说明本次缓存刷新与实际命中包，不能据此断定缓存或某个动画组件是根因。后续先确认设备实际加载v7包，再检查根Animation是否启用、clip播放状态与时间推进、move局部Y是否变化，以及运行时子Animation／控制器是否覆盖同一Transform。上述仅为排查方向，尚未验证。书本大小、锚点、无崩溃状态与悬浮效果分别验收。

本轮仅记录反馈，未改资源、客户端或生产服务。

## 2026-11-09：召唤关卡定向排查

用户再次确认“召唤”关卡书本静止。原始主表对应 quest 20710、enemy_table 14420，其中角色敌人 41028 的 chara_symbol=12，经原客户端 UnitEnemySymbolToBookColor 映射到颜色 3，地图加载 ms00_book_el_03，而不是其战斗角色模型。未修改关卡、角色或战斗配置。

生产不可变资源目录中该包版本为 1000000146，大小 9037 字节，SHA256 为 `4dbddc1b53e09bb379be14fa7b82c1946cb7c05d37714a7b058f94e3bf50e183`。服务端仍发布 v7。此证据不能证明离线设备实际命中了该包。

对原始 Assembly-CSharp.dll 做静态分析：EnemyManager.SetupEnemyComponent 在名为 move 的子节点添加 AnimationController；Enemy.SetEnemyParameter 对没有 BOOK_SYMBOL 渲染器的角色书本走角色动作分支，最终 CharacterAnimation(0) 播放待机动作。chara_kind=301 映射动作类别 6，MotionAssign.ActionAssign 第 6 行第 0 项为 10，对应 MotionData.motionFilename 中的 pc_wait_stk_01。

从原 APK 成员 `assets/bin/Data/41544a50e5150db42afdc7bcbbf25c0a` 提取该 AnimationClip：空路径位置曲线在 0 与 1.2000000477 秒都为 `(0.0999999940, -0.5399999619, 0)`，因此子 Animation 的待机动作持续写入其自身 move 的局部位置。v7 根 Animation 的 el_wait 曲线也以 move 为目标。已确认两个动画具有重叠的位置绑定；究竟由哪一个覆盖、是否存在嵌套 Animation 绑定边界问题，仍须实机采样，不能将静态冲突直接当成已证实的唯一根因。

另发现当前受版本控制的 reconstruct_gacha_book.py 仍生成 v4 结构，不能直接重跑它来修复 v7，否则会退回大小、锚点和动画的旧版本。后续修复须同步维护可复现构建与回归测试。

本轮 ADB 设备列表为空，旧连接重连失败；已请求新的远程连接信息。下一步在实际书本实例上同时记录根／move Animation 的 enabled、播放状态、时间及 move.localPosition，再做单变量覆盖实验。验证后才能确定隔离悬浮绑定的修复方式，并检查外观、角色转换及释放。当前未发布候选修复，也未宣称悬浮恢复。


2026-11-09 后续：已在 Android 14 原运行时通过单变量对照确认原 Wait 覆盖 move 位置，并完成独立子骨骼修复与生产发布。根因、回归和实机验收边界见 [书本悬浮 v8](book-hover-v8.md)。
