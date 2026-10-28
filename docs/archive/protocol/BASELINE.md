# T01 基线与恢复

2026-10-26：以下为历史冻结记录；当前工具解析已改用 enter-env.ps1，本地 Git 已建立，不能照抄旧 Python313 路径。正式旧档已额外只读备份到 server/backups/original-preserved-20261026.sqlite3；在线备份和新路径恢复使用 backup-rtd.ps1，见 [当前交付说明](../LOCAL_PLAYABLE_RELEASE.md)。历史账号3原始数据仍保留。

2026-10-24 18:05 冻结记录：`analysis/baselines/20261024-180522/manifest.json`；5项测试完整输出在同目录 `tests.txt`。账号3原始状态、在线备份恢复状态和操作后状态SHA256完全一致。恢复副本 integrity_check=ok、foreign_key_check为空；3玩家、23会话。备份为 `server/backups/rtd-baseline-20261024-180522.sqlite3`，含凭据，仅本机保存。

该清单保存原APK、热更新包、原始程序集、实验APK、服务端/启动/输入源码及两个已通过客户端run的逐文件哈希。Python 3.13.11、SQLite 3.50.4、Windows 10 19045。既有成功run为171719和172111；本次没有重做客户端验收。

重复冻结：`& 'C:\Program Files\Python313\python.exe' server/freeze_baseline.py`。在线备份使用SQLite backup API，禁止在运行时仅复制主DB而遗漏WAL。脚本使用只读生产连接，恢复与测试均在临时目录，测试监听随机端口。

恢复演练：将快照复制到一个新的实验目录，使用 `server/rtd_server.py --database <实验目录>/restored.sqlite3 --port 18767`。确认 `/health`，执行只读账号摘要与完整性检查。不要把实验API反向转发给当前账号3客户端。正式回退时先停止API，另做当前在线备份，确认没有连接后，将旧DB及其WAL/SHM移入新建隔离目录，再从已校验快照恢复；不得覆盖原快照。正式回退尚未执行，临时恢复已执行。

生产18766 PID18524、资源18765 PID9088、模拟器emulator-5554已存在，无重复启动。不存在Git仓库；不以Git提交作为恢复依据。原APK自动恢复机制未改动。

首次脚本演练暴露Windows上sqlite连接上下文不关闭句柄的问题，已改用contextlib.closing；失败只影响临时副本清理，没有修改生产状态。18:05:22重跑通过。
