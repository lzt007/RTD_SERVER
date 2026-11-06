# 狼模型 v2 离线候选与验证

2026-11-04。此候选继续构造真实狼外形，不以回退作为修复完成；最初在独立目录构造；随后按用户授权部署正式环境，尚无 Android 实机验证。

## 构造内容

`scripts/prepare_wolf_strip_candidate.py` 读取恢复清单中的八种狼，保留新备份的狼网格、真实属性贴图、双骨架及动作路径，转换为旧客户端资源格式。与 v1 相比，主要实验变量是将三角列表改成带退化连接的原生条带；所有非退化有向面片必须与源逐项相同。内部 CAB 身份独立于 v1，以免旧包残留或同载冲突。

输出目录为 `resources/reconstructed/wolf-strip-v2-candidate/`，包含八种狼所需资源名和对应属性贴图、SHA-256 与验证清单。2026-11-04 已按用户授权启用这八个候选；部署证据见 ../../deployment-20261104-monster-recovery.md。

## 已验证

- 两种基础几何：330 保留全部 52 面、80 顶点；550 保留全部 124 面、192 顶点。条带绕序、索引范围和序列化回读通过。
- 检查骨骼权重、骨索引、bindpose 数量、引用闭包、原版待机/攻击动作的骨路径、贴图回读和导出名称。
- `validate_wolf_cpu_skin.py` 使用原 APK 的待机/攻击 Hermite 曲线，各采样五帧，另外输出静止姿态。对两个 renderer 分别进行层级矩阵与四权重 CPU 蒙皮，并以真实 UV 和 alpha 生成接触表。所有采样坐标有限，没有检测到数值飞散；这不等于原生渲染验证。
- CompressedMesh 各通道均为空，不存在另一份旧压缩几何与新顶点流竞争。
- `compare_wolf_rest_bindings.py` 对照原始 Unity 5 狼和旧版原生熊。狼 renderer 113 的局部偏移在原始源中同样存在，renderer 114 的静止误差小于 8e-8；原生熊也有同类层级偏移。因此不将其误判为转换造成的骨骼破坏，也不贸然删除第二 renderer。

## 反证与未解决项

`survey_native_mesh_layouts.py` 调查原始预载/本地包中的旧格式网格，记录 2,154 个 topology=2 子网格，同时也发现 18 个 topology=0 子网格；956 个网格使用 9/20 顶点布局。统计包含不同来源包中的重复素材，不是去重后的物种数量；未覆盖 APK data 中全部独立网格。

因此，不能断言旧客户端不支持 topology=0，也不能将条带候选说成已经找到根因。离线贴图、面片和蒙皮连续，仍不能证明 Android 上头部、后肢、透明排序和移动贴图片段正常。候选用于隔离拓扑变量；当前没有足够证据确认这些实机症状已修复。

## 复现

使用资源工具解释器运行：

```sh
/tmp/rtd-event-assets-venv/bin/python scripts/prepare_wolf_strip_candidate.py --output resources/reconstructed/wolf-strip-v2-candidate
/tmp/rtd-event-assets-venv/bin/python scripts/validate_wolf_cpu_skin.py
/tmp/rtd-event-assets-venv/bin/python scripts/compare_wolf_rest_bindings.py
```

测试关卡仍为 11012「暴赫龙吼」，需同时覆盖火狼 Lv1/Lv2、银色史莱姆、敌人死亡淡出及结算。结算链和独立阶段诊断工具见 [结算闪退分析](结算闪退分析.md)。正式撤下故障狼包只是隔离措施；银色史莱姆保持。
