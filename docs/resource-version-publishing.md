# 资源版本发布（开发阶段）

版本接口和不可变发布已实现；客户端事务及真机验收尚未完成，不代表整项功能可用。

发布清单格式：`{"resources":{"a.unity3d":{"source":"bundles/a.unity3d","dependencies":[]}}}`。source 相对清单文件，dependencies 必须显式填写；空列表表示经审核确认的叶子，不表示尚未调查。调用 `python3 scripts/publish_resources.py manifest.json --output <版本目录>`。默认服务端版本目录为配置 bundles 目录的同级 resource-versions。当前 CLI 要求完整清单，不自动猜测游戏动态依赖。

发布自动计算 SHA256 并为内容分配持久整数缓存版本，先写不可变 blobs 与历史快照，再原子切换 active.json。旧版本保留；禁止手工清除 blobs、versions.json 或篡改已发布文件。恢复历史 active.json 可回滚服务端发布指针；不能删除当前下载中的历史文件。请求阶段仅加载变更后的索引，禁止全目录哈希。

POST /resources/v1/resolve 输入 protocol=1、roots 资源标识数组，可附 operationId、knownSnapshot、本地版本映射；返回 snapshotId、closureDigest 和完整 resources 依赖闭包。GET 返回的 downloadPath 下载固定字节；旧下载路由仍保留兼容。内容哈希校验不能代替客户端可加载性与对象依赖校验。

同步生产前必须备份数据库（SQLite backup API，含 WAL）、程序与配置、资源及版本目录，检查备份可读和 SQLite integrity_check，保存恢复步骤。用户已授权本次开发的生产同步，但没有授权推送 Git 远端；部署不得调用自动 git pull/push 脚本。
