# 2026-11-03 批量重建提交前回归说明

完整Python回归覆盖300个测试：58个失败断言涉及22个测试方法，全部在远端main（c33d845）隔离源码、相同恢复资源和临时数据库中复现。当前分支与基线的失败项集合完全一致，未发现新增失败。不能将本次结果表述为全量通过。

本轮功能及生产开放的27项联合验证通过，Node测试13项通过。失败涉及既有后台认证测试、准入规则、卡池数量和错误码预期；没有为迁就旧断言而修改正常关卡、卡池或错误码。

## 既有失败的基线复现

| 测试 | 失败断言数（含子用例） | 基线失败摘要 |
| --- | --- | --- |
| test_admin_http.AdminHttpTest.test_json_errors_invalid_atomic_replacement_and_methods | 1 | False is not true |
| test_admin_http.AdminHttpTest.test_real_http_read_write_catalog_and_conflict | 1 | False is not true |
| test_admin_http.AdminHttpTest.test_rejected_method_consumes_bounded_body_before_closing_connection | 1 | False is not true |
| test_admin_present_delivery.AdminDeliveryTest.test_conflict_and_player_scoped_request_id | 1 | 'application/json' not found in 'text/plain; charset=utf-8' |
| test_admin_present_delivery.AdminDeliveryTest.test_http_claim_restart_and_replay_never_resurrects | 1 | 'application/json' not found in 'text/plain; charset=utf-8' |
| test_admin_present_delivery.AdminDeliveryTest.test_invalid_requests_do_not_write | 32 | 'application/json' not found in 'text/plain; charset=utf-8' |
| test_admin_present_delivery.AdminDeliveryTest.test_safe_read_views_and_http_errors | 1 | 'application/json' not found in 'text/plain; charset=utf-8' |
| test_admin_present_delivery.AdminDeliveryTest.test_unit_claim_uses_original_level_experience | 1 | 'application/json' not found in 'text/plain; charset=utf-8' |
| test_admin_web.AdminWebTest.test_catalog_exposes_actual_openability_stair_dependencies_and_point_identity | 1 | True is not false |
| test_admin_web.AdminWebTest.test_no_directory_listing_path_traversal_or_game_route_interference | 1 | 401 != 404 : /admin/assets/ |
| test_admin_web.AdminWebTest.test_page_and_exact_assets_are_served_without_changing_configuration | 6 | 401 != 200 |
| test_admin_web.AdminWebTest.test_unit_icons_follow_master_g_id_with_png_headers_and_safe_paths | 1 | 401 != 200 |
| test_battle_layers.BattleLayersTest.test_formal_verified_paths_require_explicit_event_and_keep_other_children_gated | 1 | True is not false |
| test_health_identity.HealthIdentityTest.test_path_identity_is_canonical_case_insensitive_and_does_not_create_database | 1 | 'ea8f9cc1d82f8b430e890621c582d959615d93e077b2614fef6c969767db86c5' != 'a7740459840977f1e5568938c7087873d4dfa3b66996db0e3526af1610e85d67' |
| test_live_configuration.LiveConfigurationTest.test_defaults_catalog_schema_and_existing_v1_migration | 1 | Lists differ: [542, 506, 542] != [550, 510, 550] |
| test_quest_content.QuestContentTest.test_unverified_content_requires_explicit_experimental_opt_in | 1 | True is not false |
| test_sp_event_integration.EventIntegrationTests.test_config_validation_wrong_original_event_and_formal_gate | 1 | ProtocolError not raised |
| test_story_160_200.Story160200Test.test_main_story_available_without_experimental_mode | 1 | True is not false |
| test_story_area150.StoryArea150Test.test_formal_area150_orders_events_and_unverified_floor_gate | 1 | True is not false |
| test_story_batch.StoryBatchTest.test_formal_story_orders_and_events_work_while_unverified_content_stays_blocked | 1 | True is not false |
| test_story_batch.StoryBatchTest.test_story_catalog_formal_events_and_visual_audit_names_quests | 1 | True is not false |
| test_visual_recovery.VisualRecoveryTest.test_approved_overlay_is_stable_narrow_and_disableable | 1 | 9472 != 8197 |

## 本轮测试隔离修正

批量和神月测试会借用QuestContentTest夹具，该夹具注册延迟环境清理。外层重建开关必须同样注册LIFO清理，不能先退出外层patch.dict再执行内层清理，否则会把重建开关重新带入后续用例。已修正测试夹具的清理顺序；不改生产业务逻辑。

最初串行完整运行在最终大型字典差异格式化时被中断，不能作为完整通过记录。修正隔离后使用4组独立进程覆盖全部Python测试，组内分别运行88、60、73、79项，失败断言分别为1、10、6、41。分组并发运行耗时以最慢组222.630秒为准。

复现入口：`PYTHONPATH=.:tests python -m unittest discover -s tests`；书本离线测试需安装UnityPy==1.25.4。JavaScript入口：`node --test tests/*.mjs`。所有测试使用临时数据库，不向生产玩家发奖励。
