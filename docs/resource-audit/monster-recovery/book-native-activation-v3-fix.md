# 书本原生活动标记修复

依据 origin/main 的 b40b3bb 调查修复当前实际使用的 reconstruct_gacha_book.py：两个 GameObject 的 m_IsActive 从1改为0，保留原图像、几何、动作绑定与游戏配置。策略和内部CAB身份升级为 inferred-gacha-book-billboard-native-activation-v3。validate_book 拒绝活动标记非0的包；六色构建测试回读实际序列化标记。旧生成器的远端修正亦同步，保留其历史用途提示。

新增断言在旧实现上实测失败，实际值[1,1]，预期[0,0]。隔离候选输出：/tmp/rtd-book-native-v3-candidate，逐色来源和输出SHA见其中resource-provenance.json。

未覆盖生产资源、未变更有效游戏配置、未发布客户端。远端调查只证明03书本入场改善，战斗角色转换仍退出；这里的静态检查不代表实机整关修复。当前环境无adb，不能执行冷缓存下载、角色转换、战斗、结算、重入及Android16验收。不得直接发布候选或以此关闭整关闪退问题。

验证结果：test_gacha_book_resources 三项通过（60.893s），test_prepare_gacha_resources 一项通过（60.796s）；六色候选构建及结构校验通过。Python编译检查通过。全仓 unittest discover 运行约六分钟，管理端多项401失败后人工中止，停在 test_attribute_exp 初始化；未完成全仓测试，不宣称全仓通过。完整本地日志 /tmp/rtd-book-fix-full-tests.log。现有 battle_entry.py 工作区改动有尾随空白，本次未修改该文件。

## 生产发布

用户追加授权后已发布六色书本及对应哈希清单。六个Android/V1011 HTTP响应SHA匹配；API健康、两服务active；部署前后全部有效主表、地图、活动、运营配置一致，其他资源字节一致。已备份文件和SQLite一致性副本，未回滚玩家数据。备份与结果见上级book-native-v3-deployment-20261105.json。此前“未发布”描述为发布前阶段。客户端需执行“取得最新数据”并重启、新入关卡，尚未完成实机战斗转换和通关验收。
