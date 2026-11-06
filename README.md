# RTD_SERVER：本地游戏模拟服务与管理后台

这是可单独迁移的 Python 服务端，提供 RTD 2.4.0 协议模拟、SQLite 账号存档、中文 Web 管理后台、资源下载及本地启动公告。后台与游戏 API 同一进程、同一数据库；默认 API 为 `127.0.0.1:18766`，下载为 `127.0.0.1:18765`。

服务端目录不含 APK、客户端补丁或模拟器安装操作。当前资源为已恢复的原版资源和本地派生资源，不代表原服全量恢复；具体玩法边界保留在 `docs/archive/`。迁移时无需旧项目目录。

## 目录

```text
rtd.config.json          基础运行配置，修改后重启服务
rtd/                    HTTP/协议/业务/存储及后台静态页面
  resources.py          下载 HTTP 服务
  startup_content.py    本地公告与 common-text 响应
config/                 本地规则定义、可跟踪的资源 SHA-256 清单
resources/              本地资源（全部被 Git 忽略，另行备份）
  master-data/          25 个恢复主表文件
  level-data/           414 个关卡定义文件
  bundles/              原优先下载包（历史基础交付为 91 包）
  reconstructed/        活动/书本与怪物兼容包，按独立清单管理
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

重新生成图标、准备书本替代或运行离线 Unity 资源检查时，需要安装 `requirements-dev.txt` 中的 UnityPy；模型转换另外使用 `requirements-model-recovery.txt`。项目不依赖旧目录的 `tools/python-libs`、全局专用环境变量、Android SDK 或 ADB。

## 启动与停止

在两个终端分别运行：

```powershell
.\scripts\start.ps1 -Service api -Python .\.venv\Scripts\python.exe
.\scripts\start.ps1 -Service resources -Python .\.venv\Scripts\python.exe
```

脚本会切到项目根目录；也可从根目录直接运行 `python -m rtd` 与 `python -m rtd.resources`。保留 `python rtd_server.py` 兼容入口。分别按 Ctrl+C 停止。脚本不杀占用端口的进程、不重启已有服务；若端口冲突，请更改配置或使用显式 CLI 临时端口。

后台入口：[http://127.0.0.1:18766/admin/](http://127.0.0.1:18766/admin/)。健康检查为 `/health`；后台配置接口为 `/admin/v1/config`。后台操作直接影响所选数据库，应先核对健康接口中的 `database_path_id` 与启动日志。后台页面、静态资源及 `/admin/v1/` 接口统一要求 HTTP Basic 认证，用户名为 `admin`。密码优先取 `RTD_ADMIN_PASSWORD`；未设置时读取根配置 `paths.database` 同目录的 `admin-password.txt`，文件缺失则生成随机密码。默认路径为被 Git 忽略的 `data/admin-password.txt`，不要提交或在日志中输出密码。未认证请求返回 401，`/health` 与游戏协议不使用后台凭据。远程访问应通过受控隧道或 HTTPS 代理，避免明文传输 Basic 凭据。

API 服务终端会在每个游戏接口请求到达时打印 `API IN`，处理结束后打印 `API OUT`、接口返回码和耗时。若只看到 `API IN` 而没有对应 `API OUT`，说明请求已到达但尚未完成处理；完整的脱敏请求记录写入 `logs/requests.jsonl`。修改 Python 代码后需重启 `-Service api` 窗口才会生效。

## 配置契约

基础配置文件只读取项目根目录 `rtd.config.json`；活动排期与运营卡池保存在所选数据库的 `runtime_config`，后台更新后用于新请求，不由开发目录的静态文件自动覆盖。所有 `paths` 中的相对路径均以该文件所在项目根目录解析，与终端当前目录无关；支持迁移后保持原相对布局，也支持用户明确配置绝对外部资源路径。

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
| `features.experimental_content` | 默认 false，保留历史模式标记；不再作为关卡可玩白名单 |
| `features.blocked_quests` | 显式禁止入场的关卡 ID；仍需检查原前置、排期与积分条件 |

API CLI 兼容 `--host`、`--port`、`--database`、`--run-id`，下载 CLI 兼容 `--host`、`--port`；仅用于当前进程临时覆盖，不写回配置。CLI `--database` 相对项目根解析。历史测试兼容环境变量 `RTD_VISUAL_RECOVERY=0/1` 和 `RTD_CONTENT_EXPERIMENTAL=0/1`，显式设置时覆盖对应 feature；资源重建另有 `RTD_EVENT_RECONSTRUCTION=1`、`RTD_SHINGETSU_RECONSTRUCTION=1`、`RTD_MONSTER_RECOVERY=1`，分别启用活动重建、神月补缺及怪物兼容层；默认关闭，API 与资源服务需按部署方案设置。后台凭据使用 `RTD_ADMIN_PASSWORD`。这些环境变量及基础配置都需在对应服务启动时生效。端口要求 1–65535，配置在启动时读取，修改后重启。

设备侧的 API 和下载地址由独立客户端项目设置。此项目不会修改设备端网络路由或自动安装客户端。默认环回地址适合已有转发；真实网络访问应同时调整监听、public URL 与客户端配置。

## 下载路由

- `/Android/V1/<name>.unity3d`：兼容原 basename 查找；也支持历史其他前缀中的同名 `.unity3d`。优先读取 `paths.bundles`；缺失时按已启用的活动重建、怪物兼容层顺序查找清单允许的包。
- `/cache/Shared/<40位小写十六进制目录>/CustomAssetBundle-<标识>` 或同目录 `/__info`：下载原始缓存文件，字节原样保留，禁止路径穿越。
- `/rtd/local-notice`：独立、UTF-8 的本地公告。
- GET 或表单 POST `/rtd/local/common-text4.json`：保留原文结构，仅把 `info` 指向配置的本地公告 URL。POST 长度、重复头与超时校验有回归覆盖。

传输包与原始缓存用途不同：前者是客户端可下载 UnityWeb 封装，后者是恢复留存的 Unity 缓存文件。两者均保留，不能把原始 CustomAssetBundle 改名当成下载传输包。运行服务本身无需原 APK；离线重建部分书本/模型时需要独立客户端项目的原 APK、模板包及对应工具输入。

## 资源交付、校验与迁移

Git 保存代码、文档、本地规则与资源清单，`resources/` 的原始、解包、派生、缓存和图像文件均不跟踪。`config/resource-inventory.json` 是基础交付清单，不能用其中的历史文件总数代表后续全部重建资源。活动/书本及怪物兼容包另由对应清单管理，资源审计入口见 [docs/resource-audit/README.md](docs/resource-audit/README.md)。从 Git 克隆后需另行恢复资源目录；迁移时应从实际部署整体复制资源及配套清单，再执行基础清单检查：

```powershell
python scripts/check_resources.py
```

校验脚本依据当前路径配置检查基础清单中的文件大小和 SHA-256；它不自动穷尽后续兼容层，后者还需核对各自清单、HTTP 下载路径和依赖。新资源版本应重新审计、更新清单后交付，不能为通过校验直接改 hash。图标可选重新生成命令为 `python scripts/export_admin_unit_icons.py`，只从 `paths.icon_sources` 读取原始图集，不依赖 APK 或旧目录。默认交付的 PNG 可直接使用，无需重生成。

完整迁移应复制源码/配置/资源，并通过一致性备份迁移数据库；不要在服务运行中直接复制 SQLite 主文件而丢失 WAL。停服后也可复制完整数据目录。不要把真实数据库加入 Git。

## 数据库管理

开发目录中的 `data/rtd.sqlite3` 与生产数据库是独立副本，不会自动同步。判断已开放活动必须读取目标部署的实际运营配置及日程，记录配置 revision；不能用开发副本推断生产开放范围。Git 不包含玩家存档；仅克隆代码且未恢复数据库时，首次启动会新建空库。

```powershell
python manage.py list
python manage.py backup --output backups/manual.sqlite3
```

默认数据库取根配置，亦可显式 `--database data/other.sqlite3`。读取以 SQLite 只读模式打开，在线备份使用 SQLite backup API；目标文件已存在则拒绝覆盖。备份/输出的相对路径同样以项目根解析。恢复时先停止目标实例、保留现有库，验证快照后再配置新路径启动；不要覆盖运行中的主库。

## 开发与验证

```powershell
python -m unittest discover -s tests -v
node --test tests/test_admin_web.mjs tests/test_reward_model.mjs
python scripts/check_resources.py
```

也可运行 `scripts/start.ps1 -Service test`。测试使用临时 SQLite；后台 HTTP 用例使用临时凭据，不依赖生产密码。完整离线资源测试还需要本地原资源和生成索引，不能把缺少输入时跳过的检查当成已验证。

2026-11-06 提交前回归：完整发现 72 组 Python 测试，修正旧认证、白名单、卡池与平台断言后复测，最终 **374 项 Python、13 项 Node 测试通过，零跳过**。该记录不代表 Android 全流程或所有关卡实机验收。

`scripts/smoke_test.py` 是历史隔离启动脚本，当前后台请求尚未适配 Basic 认证，不能直接沿用旧版“8 项通过”结论。基础资源清单检查与该历史进程验证的结果也不能替代后续兼容层审计。

## 接口与历史资料

新项目当前运行入口和配置以本文为准。原后台接口文档为 [ADMIN_OPERATIONS.md](docs/archive/api/ADMIN_OPERATIONS.md)，原后台使用验收为 [ADMIN_WEB_ACCEPTANCE.md](docs/archive/protocol/ADMIN_WEB_ACCEPTANCE.md)，业务策略见 `docs/archive/rules/`。这些文档按原样归档，可能出现历史目录、实验端口、旧 APK 和阶段性状态；它们不是本项目启动脚本，也不表示当前实例已完成那些客户端验收。归档 README 位于 `docs/archive/ORIGINAL_SERVER_README.md`。

变更业务时请优先在 `rtd/services/`、`policies/`、`operations/` 添加测试；严格 DTO、请求原子事务、回执重放与已验收资源映射是兼容重点。后台读写与 API 共库，操作会影响本地模拟经济。本项目仍为原服协议的本地重建，不实现支付，不承诺历史原服所有行为一致。

## 活动关卡重建与当前审计（更新至 2026-11-06）

批量重建只补缺失地图、掉落和资源，已有真实记录及原本正常关卡的有效配置保持不变。`RTD_EVENT_RECONSTRUCTION` 默认关闭；启用后仍需明确排期才开放。推测数据和原始记录分开保存，角色Boss优先复用原角色模型，缺失书本标记使用独立内部资源名的临时包。

- [逐关修复与受阻清单](docs/superpowers/specs/2026-11-03-event-reconstruction-batch-result.md)：全量882条活动记录，当时84条新增准备完成，82条原本可用保持不变，716条当时受阻；含攻略来源和具体方案。
- [生产测试开放记录](docs/deployment-20261103-event-batch.md)：后续按用户要求将84关分29组开放测试，保留原有4组；已有前置通关与积分条件不变，仍待客户端验证。
- 离线资源准备：使用UnityPy==1.25.4运行`python scripts/prepare_event_reconstruction_resources.py --output resources/reconstructed/events/bundles`，输出目录必须不存在，已有原资源不覆盖。派生二进制及生产排期数据库不进入Git。

- [提交前回归说明](docs/verification-20261103-event-batch.md)：记录完整测试结果、远端基线已有失败与测试隔离修正，避免把相关测试通过表述为全量通过。

后续更新与验收边界：

- [地图、书本、育成与六人结算部署](docs/deployment-20261103-map-book-training-party.md)：增加四属性育成12关，修正推测地图布局及六人队伍结算；该记录保留当时的配置版本。
- [卡池差集清理](docs/deployment-20261103-gacha-cleanup.md)：仅移除副本可得或进化目标，保留剩余条目的权重、等级和顺序；迁移需审阅差集提案并核对运行配置 revision。
- [活动积分审计](docs/protocol/event-point-open-audit-20261106.md)：生产配置快照为 revision 40、36组开放活动；补全100000/100001/100003缺失积分规则，保留显式值与原门槛。规则为推测补全，已入库代码不等于已部署到生产，不追补无击杀记录的历史战斗。
- [生产育成12关补充审计](docs/resource-audit/production-training-20261106/README.md)：22个下载包的HTTP、哈希、模型导出、贴图及敌人递归依赖核查通过；地图8个LevelBackground组件的自定义字段仍有解析限制，未做实机通关验收。
- [最新资源审计入口](docs/resource-audit/README.md)：生产兼容清单、原图稿缺口、角色型加载链与旧报告范围分开说明。狼与银色史莱姆的模型显示已获确认；通关闪退未由资源审计证明修复。

活动运营中的“已开放”、数据层的“可支持”和客户端的“已验收”是不同状态。生产revision 40仅是2026-11-06核查快照，后续以实际部署的运行配置为准。
