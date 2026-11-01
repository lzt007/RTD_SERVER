# 数据库递进更新

服务启动时执行 rtd/storage/migrations 中的版本化 SQL。V001 初始化玩家、会话、关卡和操作回执表；V002 创建运行配置表。空库按顺序初始化，旧库依据原有 PRAGMA user_version（0/1/2）接续更新，保留已有业务数据。

新增结构变更请添加 V003__说明.sql 等连续编号文件，不修改已发布文件。schema_history 保存版本、文件名、SHA256 和执行时间；历史脚本改变或数据库版本高于服务端时拒绝启动。迁移通过 BEGIN IMMEDIATE 串行执行，SQL 与版本记录在同一事务中提交，失败整体回滚。SQL 文件不要包含 BEGIN、COMMIT 或 VACUUM 等事务管理语句。

部署脚本使用 SQLite backup API 备份并验证完整性，失败停止部署；同步保护配置指定的数据库及 WAL/SHM/journal 文件，不覆盖生产数据库。部署前审查新增 SQL，备份不等于自动回滚；迁移失败应修复新增版本后重试，不要自动覆盖线上库。旧版本首次接入时以 user_version 为基线，因此应先确认旧库版本与实际结构相符。

已核对现有生产库结构为 v2。scripts/baseline-v2.sql 可在备份后为尚无 schema_history 的 v2 库补齐历史记录；不要对其他版本或已有历史记录的库执行。该脚本不修改业务表和 user_version。
