# 新手助战账号

先在开发环境验证。用户随后明确授权将九名助战加入生产数据库。

原先仅有一个助战源于固定NPC策略，不是缺少角色。原 UNIT_MASTER 有751项。新增账号沿用原角色与技能，不合成不存在的角色，不改技能数值。配置位于 config/newcomer-helpers.json。

|ID|角色|等级|用途|
|---|---|---|---|
|15550|機神王 ASmk-2β|99|王系|
|15559|海龍王 リヴァイア|99|王系|
|15562|覇壊王 宝条まゆ|99|王系|
|15565|刻帝王 クロノ|99|王系|
|15577|禁書王 ユーリカ|99|王系|
|16003|聖王 ジャンヌ|80|全转剑，追击时获得1魂|
|14209|砂賊王 マチルダ|80|全转弓，攻击时30%概率获得1魂|
|15033|火焔将 ナタル|80|全转枪，受击时45%概率反击|
|14203|超老 マクスウェル|80|全转杖，全属性板块加成提升|

技能按 UNIT_MASTER 的 a_skill_id/p_skill_id 查对应 RANK_MASTER 的 skill_80_89，再解析技能主表；不能直接把成长组ID当技能ID。等级按 lv_max，经验由既有 level_exp 计算。保留原图形、属性与技能，尚未设备实战验收。

从开发项目根目录执行：

```bash
python3 scripts/seed_helpers.py --database data/rtd.sqlite3
```

必须明确给数据库路径。初始化在一个事务内创建九名账号，随机内部身份、独立账号ID，npc_helper_key标识；再次执行按key识别，不覆盖既有关系、余额或角色进度。配置修改已有key不重置账号；如需替换角色应另做明确迁移。初始化不会自动在生产执行，生产目录默认拒绝，只有显式 --allow-production 才允许。生产执行前必须备份。

账号禁止认证登录，但可搜索、借用，收到申请自动建立双向好友关系；满额、删除、助战订单快照及友情点沿用现有实现。系统账号不受正常100人上限约束（max_friend=1000000），真人好友容量仍正常检查。没有自动接受真人之间的申请。

助战显示仍采用既有排序与20名陌生人上限；本地账号较多时，可搜索初始化输出的ID添加后借用。默认user_id=0的教程助战保留。

## 验证与生产初始化

2026-11-01开发定向回归：NPC4项、好友12项、助战奖励20项、账号11项，共47项通过。独立审查发现NPC第101名好友会被旧队列上限拒绝，已用失败用例复现并修正，只豁免NPC接收侧，真人容量限制保留。

全量回归运行结果如下（含子用例失败），仍未全绿。主要是既有后台测试未认证、Pillow未安装、关卡开放及路径/视觉恢复断言问题；不将定向通过写成全量通过。

Ran 256 tests in 238.475s
FAILED (failures=58, errors=1)

失败测试名称（合并同名子用例）：

- `ERROR: test_admin_unit_icons (unittest.loader._FailedTest)`
- `FAIL: test_json_errors_invalid_atomic_replacement_and_methods (test_admin_http.AdminHttpTest)`
- `FAIL: test_real_http_read_write_catalog_and_conflict (test_admin_http.AdminHttpTest)`
- `FAIL: test_rejected_method_consumes_bounded_body_before_closing_connection (test_admin_http.AdminHttpTest)`
- `FAIL: test_conflict_and_player_scoped_request_id (test_admin_present_delivery.AdminDeliveryTest)`
- `FAIL: test_http_claim_restart_and_replay_never_resurrects (test_admin_present_delivery.AdminDeliveryTest)`
- `FAIL: test_invalid_requests_do_not_write (test_admin_present_delivery.AdminDeliveryTest)`
- `FAIL: test_safe_read_views_and_http_errors (test_admin_present_delivery.AdminDeliveryTest)`
- `FAIL: test_unit_claim_uses_original_level_experience (test_admin_present_delivery.AdminDeliveryTest)`
- `FAIL: test_catalog_exposes_actual_openability_stair_dependencies_and_point_identity (test_admin_web.AdminWebTest)`
- `FAIL: test_no_directory_listing_path_traversal_or_game_route_interference (test_admin_web.AdminWebTest)`
- `FAIL: test_page_and_exact_assets_are_served_without_changing_configuration (test_admin_web.AdminWebTest)`
- `FAIL: test_unit_icons_follow_master_g_id_with_png_headers_and_safe_paths (test_admin_web.AdminWebTest)`
- `FAIL: test_formal_verified_paths_require_explicit_event_and_keep_other_children_gated (test_battle_layers.BattleLayersTest)`
- `FAIL: test_path_identity_is_canonical_case_insensitive_and_does_not_create_database (test_health_identity.HealthIdentityTest)`
- `FAIL: test_defaults_catalog_schema_and_existing_v1_migration (test_live_configuration.LiveConfigurationTest)`
- `FAIL: test_unverified_content_requires_explicit_experimental_opt_in (test_quest_content.QuestContentTest)`
- `FAIL: test_config_validation_wrong_original_event_and_formal_gate (test_sp_event_integration.EventIntegrationTests)`
- `FAIL: test_main_story_available_without_experimental_mode (test_story_160_200.Story160200Test)`
- `FAIL: test_formal_area150_orders_events_and_unverified_floor_gate (test_story_area150.StoryArea150Test)`
- `FAIL: test_formal_story_orders_and_events_work_while_unverified_content_stays_blocked (test_story_batch.StoryBatchTest)`
- `FAIL: test_story_catalog_formal_events_and_visual_audit_names_quests (test_story_batch.StoryBatchTest)`
- `FAIL: test_approved_overlay_is_stable_narrow_and_disableable (test_visual_recovery.VisualRecoveryTest)`

生产已创建账号13–21，按上表顺序对应九名角色。初始化前在生产 backups/newcomer-helpers-20261101-162625 保存数据库和替换模块备份；原12个账号全部字段及会话逐字节保持，新增恰好9名，SQLite integrity_check=ok。同步此前的陌生助战支持与本次NPC模块，重启API后健康检查200，资源服务保持运行；直接读取生产助战处理器确认九名角色和等级均可列出。未做设备端实战验收。

开发库相同账号13–21已初始化，再次执行全账号state逐字节保持。未改动既有 scripts/auto-deploy.sh 工作区修改。
