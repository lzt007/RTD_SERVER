# 普通单位进化

`evolve_unit`请求为目标`dst_unit_instance_id`、1–4个唯一素材`src_unit_instance_id`及`add_point`。原客户端传入主表need_pt，不能改成素材总点数。普通目标必须满级且rev_unit_id有效；费用need_pt×100。素材点数为int(Single(Single(level−1)×Single(sqrt(set_pt))+Single(set_pt)))，总和至少达到need_pt。

目标保持实例ID、member、收藏、四项bonus和编队位置，换成rev_unit_id后level1、exp0、attribute_exp0。素材收藏/任一组前三主槽受保护，两副槽引用随消耗清除。特殊material_type或携带bonus/attribute_exp的素材暂拒绝8197。目标换型、金币、素材、图鉴、高水位及回执在同一事务；重排、并发、重启和旧回执不重复扣费或覆盖后续进度。响应result为空字符串数组，原消费分支不读取其内容。

原DLL SHA c83aea19ee65ae973815daf6a04e430d9e87b8426b6180c1fe507e4260763ecc；REA parent ev_95be35708cabf725152679d97d757913096c99d3c3cdea5c80bdbb04e0e476af，五个选定类型全部匹配。

特殊强化`sp_compose_unit`及究极进化`ultimate_evolve`现已增加独立规则、持久化和测试，见[SPECIAL_EVOLUTION.md](SPECIAL_EVOLUTION.md)。原普通进化行为保留；服务端协议通过与原菜单验收分别记录。

当前证据：48项服务端测试、16项Android工具测试通过；独立整体审查无发现。隔离unit-evolve-20261025从T20派生，两次11000及四批正常强化将1003升至15级/10685经验；所有批次先核对原版预览，未直接修改等级或货币。

19:43:26真实evolve_unit4096：1003原10021换11021、level1/exp0，素材1005（20000、level4、40点）消耗，73575→69575金币、4→3单位。原版动画结束展示图鉴39角色模型与纹理，等级1。服务端完整目标元数据、所有编队及另两单位保留；旧10021图鉴最高15与新11021图鉴1并存，一条进化回执。AP19→20为等待期间原自然恢复，不是进化奖励。证据evolve-preview.jsonl、before/after-evolve.sqlite3、evolve-verified.json。双重启核对进行中。

观测限制：原ClientAddEvoUnit替换列表中的UnitData，静态MMUnitEvo.m_BaseUnit仍引用旧对象，成功后不能用该静态字段判断客户端最终类型。最终原版详情画面及重新登录get_units为准。

双重启已通过：新进程EvoBase实际单位行1003/11021，三单位及全部五组编队一致。与进化后即时存档相比，仅unit_collection_flags第4字节22→150（OR128，原客户端发现g_id39）；断言其余完整存档相等。重启后SHA a258c9421fef95c5f6f38c0203b40c01e996d641de2de562b44f7cf1e9f9731c，证据restart-verified.json、evolve-restart-client.jsonl、after-evolve-restart.sqlite3。
