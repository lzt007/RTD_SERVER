# 2026-11-02 生产部署与简体包

生产服务端已部署开发提交 cfb5926（含奖励批发、模拟购买、原商品SKU与备份兼容修复）。保留生产配置、数据库、资源；部署前SQLite在线备份位于生产目录 backups/deploy-20261102-003316/before.sqlite3。迁移后schema 3、integrity_check为ok，部署前后账号均21。API健康和公告资源HTTP均200，两个systemd服务active。未向真实玩家发测试奖励。

客户端提交869e398完整构建简体APK，含9693条翻译（现有繁体译文经OpenCC t2s转换），文泉驿正黑字库2553字形。生产连接配置仅留在忽略目录；debuggable关闭、日志warning，沿用本地开发签名。产物位于相邻RTD_CLIENT/dist/rtd-client-zh-CN.apk，SHA256 a39d7a4b03ebdfc28c6360519c68eeb21bce59896f632d57dfcc84de98e709db。

购买契约、LocalStoreTests、Loader、Localization、zipalign、apksigner和资源一致性检查通过，产物摘要与报告一致。没有设备连接，未声称真机界面或购买流程验收通过。配置、字体、APK、密钥及构建日志均未纳入Git。
