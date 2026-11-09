# 书本悬浮 v8：隔离原角色待机的位置绑定

## 问题与实机根因

2026-11-09，用户确认“召唤”（quest 20710）地图书本仍静止。该关卡角色敌人 41028 的 symbol=12，对应地图书本 ms00_book_el_03。主表、地图、敌人属性、数值、角色模型、掉落和开放条件均不修改。

在同一台 Android 14 设备、原 Unity 运行时中载入生产 v7 色03包，运行原角色待机 pc_wait_stk_01 的最小对照：

| 条件 | 实测 move 局部 Y 范围差 | 动画状态 |
| --- | --- | --- |
| 只有根 el_wait 悬浮 | 0.09957282 | 根播放，子不播放 |
| 子 move CrossFade 原 Wait | 0 | 根、子都播放，但 move 恒为 -0.54 |
| 停止子 Wait，保留根播放 | 0.09958533 | 悬浮恢复 |

因此不是缺少曲线。根 Animation 与运行时子 Animation 同时写 move.localPosition，原角色 Wait 覆盖了悬浮。原角色待机的空绑定还负责基础位置，不能简单忽略整个 move 节点。

## 最终修复范围

只升级六色推测替代书本资源。新增中性子骨骼 `move/book_hover`，保持 move 原休止位置、旋转、缩放，以及运行时 AnimationController。根 el_wait 改为驱动这个子骨骼，蒙皮也绑定子骨骼。原动作继续负责基础位置，新增局部位移负责悬浮。

保留原材质、贴图、Shader、Mesh、顶点、UV、索引、尺寸、锚点、包围盒、原曲线关键帧／时间／切线的字节或数据；只改曲线绑定路径。原根 Animation 保留，满足 Enemy.UnLoad 的 clip 访问和清理契约；move Animation 也保留。每包15对象，无外部依赖，旧 Unity GameObject 激活编码仍为0。没有修改原游戏程序集逻辑。

审查曾发现并列骨骼候选会丢失 move 的基础位移而抬高书本，已弃用；未发布该候选。回归检查要求子骨骼继承 move，旧并列候选在六色检查中均失败。

## 可复现构建与验证

`scripts/reconstruct_gacha_book.py` 是历史 v4 构建器，不用于发布当前书本。新脚本 `scripts/prepare_book_hover_isolation.py` 从严格 SHA256 白名单的六色 v7 包升级，拒绝其他输入及覆盖输出。v7 输入保留在本地 `resources/reconstructed/book-hover-v7-inputs/`；也可从生产历史不可变 blob 按脚本列出的哈希取回，不覆盖历史包。

```sh
python scripts/prepare_book_hover_isolation.py \
  --input resources/reconstructed/book-hover-v7-inputs \
  --output /tmp/rtd-book-hover-v8-final
python -m unittest tests.test_book_hover_isolation \
  tests.test_resource_publish tests.test_resource_versions tests.test_resource_dependencies
```

上述测试需要离线 UnityPy 与本地原始输入，实际执行22项通过。新增检查首先在生产 v7 六色均失败，再验证新包通过，覆盖位置绑定隔离、继承原定位、原资源字节、原动画契约及闭包。独立审查未发现其他重要问题。

客户端 `diagnostics/book-hover/` 仅供单独候选 APK 使用，不进入正式构建。它记录根／move 动画状态、书本骨骼位置，并以“原 Wait 同时播放时骨骼仍运动”为判据。诊断包不改变真实关卡实例，只采样；对照实验使用临时离屏克隆。正式中文 APK 保持原件，验证结束须覆盖恢复。

## 实机与生产验收状态

最终子骨骼方案在同一 Android 14 设备完成最小对照：单独悬浮范围差0.09939377；同时播放原 Wait 时 book_hover 范围差0.09973534，move 保持-0.54；停止 Wait 后范围差0.1000815。嵌套绑定确实在原 Unity 运行时生效，不丢失基础定位。

生产已备份至 `backups/deployment/book-hover-v8-20261109T130528Z`，包含 SQLite backup API 一致性副本、完整配置、被替换文件、旧 active.json 与版本分配记录。只更改六个书本资源条目，375总数不变；其余369条目录数据逐项保持原样。六色缓存版本为1000000380至1000000385（色03为1000000382）。发布快照为 `2208f6543d2c9052b34c3b479f487da4fbd3fd4b2dc67bbab39a8b06fe0ad841`。两服务健康，六个不可变下载地址和六个旧下载路径均核对SHA256通过，有效主表、地图、关卡开放与运营配置不变，其他已有资源文件哈希不变。

发布过程中校验触发过自动回退：当前发布器会补空requiredPrefabs字段，因此改为私有暂存发布，保留无关资源条目的原表示；随后修正校验请求缺少protocol字段的问题。最终校验全部通过。回退仅恢复发布可见性及替换文件，保留不可变历史及单调缓存版本分配，不回滚玩家数据库。完整关卡实机记录继续补充。

结构通过不等于画面通过，悬浮通过也不代表旧有完整通关／结算问题已修复。全程未重启测试手机。
