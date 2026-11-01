# 好友增量验证

2026-11-01：好友12项、助战奖励20项、账号11项定向回归通过；Node后台前端12项通过。独立审查未发现确认的流程阻断。

全量 `python3 -m unittest discover -s tests` 跑完252项，报告60个失败（包括子用例）、1个导入错误，未通过。该轮读取了修正前的账号测试和助战错误码：其中下列两个 AccountsTest 失败随后已通过11项账号复验修复。其他失败涉及后台测试缺认证返回401、Pillow未安装、已有关卡开放断言与当前实现不一致、Linux路径大小写及视觉恢复断言。未在本次好友范围内修改这些子系统，也未声称最终全量通过。

完整失败名称（合并同名子用例）：

- `ERROR: test_admin_unit_icons (unittest.loader._FailedTest)`
- `FAIL: test_local_helper_contract_is_authenticated_read_only_and_restart_safe (test_accounts.AccountsTest)`
- `FAIL: test_second_tutorial_entry_validates_hashes_and_keeps_one_snapshot (test_accounts.AccountsTest)`
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

## 待验证与后续事项

- 尚未设备验收：NPC战后提示是否仅确认、旧客户端0号申请8706提示和回退；真实陌生助战战后点“是”的完整界面流程。
- 陌生列表目前读取账号ID后筛选20人，大规模账号下应改为分页候选查询。
- 可扩展20人上限、单账号及双向待处理排除的专项测试；目前多层陌生用例直接验证根订单快照，后层继承依赖现有通用多层回归。
- 本次只使用临时测试数据库，保留既有部署脚本修改，不推送、不替换运行服务。
