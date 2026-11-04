# RTD_SERVER：本地游戏模拟服务与管理后台

这是可单独迁移的 Python 服务端，提供 RTD 2.4.0 协议模拟、SQLite 账号存档、中文 Web 管理后台、资源下载及本地启动公告。后台与游戏 API 同一进程、同一数据库；默认 API 为 `127.0.0.1:18766`，下载为 `127.0.0.1:18765`。

服务端目录不含 APK、客户端补丁或模拟器安装操作。当前资源为已恢复的原版资源和本地派生资源，不代表原服全量恢复；具体玩法边界保留在 `docs/archive/`。迁移时无需旧项目目录。

## 目录

```text
rtd.config.json          唯一运行配置入口，修改后重启服务
rtd/                    HTTP/协议/业务/存储及后台静态页面
  resources.py          下载 HTTP 服务
  startup_content.py    本地公告与 common-text 响应
config/                 本地规则定义、可跟踪的资源 SHA-256 清单
resources/              本地资源（全部被 Git 忽略，另行备份）
  master-data/          25 个恢复主表文件
  level-data/           414 个关卡定义文件
  bundles/              91 个可下载的 .unity3d 传输包
  cache/Shared/         90 份原始 Unity 缓存，共 180 文件
  startup/              公告 HTML、common-text 原文及出处清单
  icon-sources/         从原资产独立提取的 17 份图集源文件
  unit-icons/           746 张后台图标 PNG 与生成清单
scripts/                启动、资源校验、图标生成和独立进程验证
tests/                 Python 与 Node 回归测试
data/                  运行时 SQLite（不进 Git）
backups/               数据库快照（不进 Git）
logs/                  请求与验证日志（不进 Git）
build/                 隔离验证目录（不进 Git）
docs/archive/          原接口、规则、验收资料与历史 README
```

## 准备依赖

要求 Python 3.10+。服务本身只用 Python 标准库（HTTP、SQLite、JSON、GZIP），无需安装 Flask 等框架；完整测试需要 Pillow，后台逻辑测试需要 Node.js（本次使用 Node 24）。建议用虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

只有需要从项目内图集源重新生成 PNG 时才安装 `requirements-dev.txt` 中的 UnityPy。项目不依赖旧目录的 `tools/python-libs`、全局专用环境变量、Android SDK 或 ADB。

## 启动与停止

在两个终端分别运行：

```powershell
.\scripts\start.ps1 -Service api -Python .\.venv\Scripts\python.exe
.\scripts\start.ps1 -Service resources -Python .\.venv\Scripts\python.exe
```

脚本会切到项目根目录；也可从根目录直接运行 `python -m rtd` 与 `python -m rtd.resources`。保留 `python rtd_server.py` 兼容入口。分别按 Ctrl+C 停止。脚本不杀占用端口的进程、不重启已有服务；若端口冲突，请更改配置或使用显式 CLI 临时端口。

后台入口：[http://127.0.0.1:18766/admin/](http://127.0.0.1:18766/admin/)。健康检查为 `/health`；后台配置接口为 `/admin/v1/config`。后台操作直接影响所选数据库，应先核对健康接口中的 `database_path_id` 与启动日志。HTTP 管理接口的实现没有公网身份认证，应按本地工具部署，远程访问时自行配置受控隧道或认证代理。

API 服务终端会在每个游戏接口请求到达时打印 `API IN`，处理结束后打印 `API OUT`、接口返回码和耗时。若只看到 `API IN` 而没有对应 `API OUT`，说明请求已到达但尚未完成处理；完整的脱敏请求记录写入 `logs/requests.jsonl`。修改 Python 代码后需重启 `-Service api` 窗口才会生效。

## 配置契约

配置文件只读取项目根目录 `rtd.config.json`。所有 `paths` 中的相对路径均以该文件所在项目根目录解析，与终端当前目录无关；支持迁移后保持原相对布局，也支持用户明确配置绝对外部资源路径。

| 配置 | 作用 |
| --- | --- |
| `api.host` / `api.port` | API 与后台监听地址、端口；默认 127.0.0.1 / 18766 |
| `resources.host` / `resources.port` | 下载服务监听地址、端口；默认 127.0.0.1 / 18765 |
| `resources.public_base_url` | **设备访问资源服务的地址**，用于 common-text 中生成公告 URL；不等同于监听地址。修改下载端口时同步修改此 URL |
| `paths.database` | SQLite 文件，默认 data/rtd.sqlite3；缺失时创建新库 |
| `paths.request_log` / `paths.backups` | API 请求 JSONL 与备份输出目录 |
| `paths.master_data` / `paths.level_data` | 恢复主表与关卡定义目录 |
| `paths.bundles` / `paths.cache` | 下载传输包目录、原始缓存 Shared 目录 |
| `paths.startup` | 本地公告、common-text 原始 JSON |
| `paths.unit_icons` / `paths.icon_sources` | 后台 PNG/manifest 与可选生成图集源 |
| `paths.gacha_pools` / `paths.visual_policy` | 本地卡池规则与已审计视觉替代规则 |
| `features.visual_recovery` | 默认 true，启用明确记录的原资源视觉替代 |
| `features.experimental_content` | 默认 false，不把未验收关卡自动作为正式可玩内容 |

API CLI 兼容 `--host`、`--port`、`--database`、`--run-id`，下载 CLI 兼容 `--host`、`--port`；仅用于当前进程临时覆盖，不写回配置。CLI `--database` 相对项目根解析。历史测试兼容环境变量 `RTD_VISUAL_RECOVERY=0/1` 和 `RTD_CONTENT_EXPERIMENTAL=0/1`，显式设置时覆盖对应 feature；日常部署统一编辑配置即可。端口要求 1–65535，配置在启动时读取，修改后重启。

设备侧的 API 和下载地址由独立客户端项目设置。此项目不会修改设备端网络路由或自动安装客户端。默认环回地址适合已有转发；真实网络访问应同时调整监听、public URL 与客户端配置。

## 下载路由

- `/Android/V1/<name>.unity3d`：兼容原 basename 查找；也支持历史其他前缀中的同名 `.unity3d`。文件仅从 `paths.bundles` 中读取。
- `/cache/Shared/<40位小写十六进制目录>/CustomAssetBundle-<标识>` 或同目录 `/__info`：下载原始缓存文件，字节原样保留，禁止路径穿越。
- `/rtd/local-notice`：独立、UTF-8 的本地公告。
- GET 或表单 POST `/rtd/local/common-text4.json`：保留原文结构，仅把 `info` 指向配置的本地公告 URL。POST 长度、重复头与超时校验有回归覆盖。

传输包与原始缓存用途不同：前者是客户端可下载 UnityWeb 封装，后者是恢复留存的 Unity 缓存文件。两者均保留，不能把原始 CustomAssetBundle 改名当成下载传输包。原 APK 不需要放到此项目。

## 资源交付、校验与迁移

Git 仅保存代码、文档、本地规则与 `config/resource-inventory.json`，`resources/` 的全部原始、解包、派生、缓存、图像文件均不跟踪。当前资源共有 **1,477 文件 / 359,379,347 字节（约 342.73 MiB）**。从 Git 克隆后需另行恢复资源目录，不能仅克隆代码即启动。当前工作目录已完整放置资源；迁移请整体复制此项目的 `resources/`，再执行：

```powershell
python scripts/check_resources.py
```

校验脚本依据当前路径配置读取各资源区域，逐文件检查大小和 SHA-256。新资源版本应重新审计、更新清单后交付，不能为通过校验直接改 hash。图标可选重新生成命令为 `python scripts/export_admin_unit_icons.py`，只从 `paths.icon_sources` 读取原始图集，不依赖 APK 或旧目录。默认交付的 PNG 可直接使用，无需重生成。

完整迁移应复制源码/配置/资源，并通过一致性备份迁移数据库；不要在服务运行中直接复制 SQLite 主文件而丢失 WAL。停服后也可复制完整数据目录。不要把真实数据库加入 Git。

## 数据库管理

本机拆分副本的 `data/rtd.sqlite3` 已放入拆分时正在使用的服务实例的一致性快照，保留现有玩家与后台配置；通过 SQLite 在线备份 API 读取原库，原服务和原库未改变。快照与原库的逻辑 SQL SHA-256 相同，出处和时间记录在被忽略的 `data/split-checkpoint.json`。新目录未启动常驻服务，此后两份数据库不会自动同步。Git 不包含这份存档；仅克隆代码且未恢复数据库时，首次启动会新建空库。

```powershell
python manage.py list
python manage.py backup --output backups/manual.sqlite3
```

默认数据库取根配置，亦可显式 `--database data/other.sqlite3`。读取以 SQLite 只读模式打开，在线备份使用 SQLite backup API；目标文件已存在则拒绝覆盖。备份/输出的相对路径同样以项目根解析。恢复时先停止目标实例、保留现有库，验证快照后再配置新路径启动；不要覆盖运行中的主库。

## 开发与验证

```powershell
python -m unittest discover -s tests -v
node --test tests/test_admin_web.mjs
python scripts/check_resources.py
python scripts/smoke_test.py
```

也可运行 `scripts/start.ps1 -Service test`。Python 测试均创建临时 SQLite；不依赖真实玩家存档。`smoke_test.py` 在 ignored `build/smoke-*` 创建独立最小项目副本、复制必需主表/规则/公告和代表性资源，通过根配置分配随机空闲端口与新 SQLite，再启动两个子进程，验证后台、配置 API、健康检查、图标、common-text 公告 URL、传输包与原缓存逐字节下载，最后只停止自己创建的进程；不会访问默认 18765/18766/18767。

本次验证：**247 项 Python 测试、12 项 Node 测试全部通过**，资源清单逐文件通过，独立目录进程验证 8 项通过。记录在 ignored `logs/` 与 `build/smoke-*/result.json`。这证明服务端隔离启动及 HTTP 契约，不代表重新执行客户端全流程或全关卡验收；本次未安装客户端、未操作原正在运行服务或真实数据库。

## 接口与历史资料

新项目当前运行入口和配置以本文为准。原后台接口文档为 [ADMIN_OPERATIONS.md](docs/archive/api/ADMIN_OPERATIONS.md)，原后台使用验收为 [ADMIN_WEB_ACCEPTANCE.md](docs/archive/protocol/ADMIN_WEB_ACCEPTANCE.md)，业务策略见 `docs/archive/rules/`。这些文档按原样归档，可能出现历史目录、实验端口、旧 APK 和阶段性状态；它们不是本项目启动脚本，也不表示当前实例已完成那些客户端验收。归档 README 位于 `docs/archive/ORIGINAL_SERVER_README.md`。

变更业务时请优先在 `rtd/services/`、`policies/`、`operations/` 添加测试；严格 DTO、请求原子事务、回执重放与已验收资源映射是兼容重点。后台读写与 API 共库，操作会影响本地模拟经济。本项目仍为原服协议的本地重建，不实现支付，不承诺历史原服所有行为一致。

## 活动关卡重建与测试开放（2026-11-03）

批量重建只补缺失地图、掉落和资源，已有真实记录及原本正常关卡的有效配置保持不变。`RTD_EVENT_RECONSTRUCTION` 默认关闭；启用后仍需明确排期才开放。推测数据和原始记录分开保存，角色Boss优先复用原角色模型，缺失书本标记使用独立内部资源名的临时包。

- [逐关修复与受阻清单](docs/superpowers/specs/2026-11-03-event-reconstruction-batch-result.md)：全量882条活动记录，84条新增准备完成，82条原本可用保持不变，716条按当前证据仍受阻；含攻略来源和具体方案。
- [生产测试开放记录](docs/deployment-20261103-event-batch.md)：后续按用户要求将84关分29组开放测试，保留原有4组；已有前置通关与积分条件不变，仍待客户端验证。
- 离线资源准备：使用UnityPy==1.25.4运行`python scripts/prepare_event_reconstruction_resources.py --output resources/reconstructed/events/bundles`，输出目录必须不存在，已有原资源不覆盖。派生二进制及生产排期数据库不进入Git。

- [提交前回归说明](docs/verification-20261103-event-batch.md)：记录完整测试结果、远端基线已有失败与测试隔离修正，避免把相关测试通过表述为全量通过。
