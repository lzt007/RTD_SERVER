# 历史活动积分解锁：修复方法与回放手册

本手册对应 2026-11-07 已完成的生产修复与安卓验收，原因及证据见 [完整分析结果](history-event-unlock-analysis-20261107.md)。实际部署地址、登录凭据、签名密码、账号和数据库由本地配置或环境注入，不进入 Git。

## 1. 先判定故障属于哪一层

|检查|正确结果|异常时处理|
|---|---|---|
|原关卡配置|20710／20711／20712 的活动 ID 为 100001，门槛 0／5／50，教程前置 10000|沿用原始主表，不人为降门槛或增加逐关前置|
|实际部署文件|存在积分补全模块，生成器接收 event_id，单层／多层入口都传原活动 ID|比较实际文件，不能只看开发仓库提交号|
|新 `order_quest` 响应|出现的 41028 每只 1 分，非目标为 0|检查生成器优先级、运营覆盖、原掉落字段和部署版本|
|客户端实际击杀|单局积分按目标逐只增加，普通龙不增加|核对实际新战斗响应及敌人定位，不先改客户端逻辑|
|`clear_quest2`|原客户端上报实际获得积分，服务端返回 4096|检查冻结上限、请求字段和原子回滚，不能自动补发全部可获得积分|
|持久化及重登|服务端余额保存，新进程登录返回相同余额|检查结算保存、回执和登录协议；不能只看本地结算界面|
|解锁|余额≥5 时 20711 可解锁，余额≥50 时 20712 可解锁|保留原教程与日程条件，检查客户端实际取得的主表和登录数据|

旧战斗会重用入场冻结快照。部署后恢复旧局继续为 0，不足以否定新实现；应正常退出旧局并新开一局。不能通过改写旧快照或回填历史余额使测试“通过”。

## 2. 源码修复

本次修复已经包含在服务端 `2fd7d0b`，并已合并至本次调查基线 `346d856`。本次工作补齐的是生产部署、真实关卡回归、只读诊断和完整实机验收，不是另行修改客户端战斗算法。

### 2.1 独立记录缺失补全

[event_point_recovery.py](../../rtd/policies/event_point_recovery.py) 按原活动 ID 和原敌人 ID 筛选目标：

```python
TARGETS = {
    100000: frozenset(range(40103, 40115)) | frozenset(range(40119, 40123)),
    100001: frozenset({41028}),
    100003: frozenset({41040, 41045, 41049, 41053, 41058, 41064, 41069}),
}


def missing_point(event_id, enemy_id):
    return int(enemy_id in TARGETS.get(event_id, ()))
```

上面的目标范围和每只 1 分是已有本地缺失补全规则，不冒充官方恢复数量。已有原始记录、显式 0 和其他活动不得被覆盖；后续找到真实数据时，应撤销对应推测并记录出处。

### 2.2 保留明确的字段优先级

[battle_generation.py](../../rtd/services/battle_generation.py) 的关键逻辑：

```python
original = drops.get(drop_id, {})
point_source = (
    override
    if override is not None and 'sp_event_point' in override
    else original
)
point_default = missing_point(event_id, table[prefix + '_set_id'])
point = point_source.get('sp_event_point', point_default)
# 仅 present 且非地形对象时输出 point，否则输出 0。
```

不要用 `value or fallback`，那会错误覆盖真实 0；不要给全部战斗敌人统一 1 分；不要把“未知字段”补成一个冒充原值的 0。

### 2.3 单层与多层都传入原活动 ID

两个入口调用生成器时必须包含：

```python
generate_enemies(..., event_id=quest.get('sp_event_id', 0), ...)
```

对应文件为 [battle_entry.py](../../rtd/services/battle_entry.py) 和 [battle_layers.py](../../rtd/services/battle_layers.py)。不能只修单层，也不能按关卡 ID 猜活动身份。

### 2.4 保留冻结、结算和重放语义

沿用 [event_points.py](../../rtd/policies/event_points.py) 的本局上限冻结与累计检查：单局最多 999、累计最多 99999；上报必须是整数且不超过冻结上限，显式拒绝布尔值、字符串、负数和超额值。

服务端只累加客户端本次正常上报的积分；相同成功结算重放不能再次加分。旧战斗不重新按新配置计算，既有客户端请求 DTO 不增加字段。

## 3. 部署前验证与制作最小补丁

在开发仓库确认本地修改和目标分支，获取远端最新状态，运行相关测试：

```powershell
git status --short
git fetch origin
git log -5 --oneline
$env:PYTHONUTF8='1'
$env:PYTHONPATH='tests'
.\.venv\Scripts\python.exe -m unittest test_battle_generation test_battle_layers test_history_event_points test_history_event_points_e2e test_sp_event_integration -q
```

本次 30 项通过。新增 [真实历史关卡端到端测试](../../tests/test_history_event_points_e2e.py) 使用临时 SQLite 与真实主表／重建地图／掉落；仅绕过二进制资源就绪审计，不能代替 Android 验收。已有测试还验证显式 0、上报边界、冻结和幂等。

发布包只包含已复核的四个生产源码文件及逐文件 SHA-256 清单。先取实际部署文件副本做差异比较：若有其他部署改动，应在该副本上应用最小差异，不能整份覆盖。四个文件必须作为同一版本发布，避免调用者和生成器签名不一致。

不把 APK、资源包、生产配置、数据库或日志夹带进源码包。本次没有修改资源二进制，因此不重打资源包或替换全量资源清单。

## 4. 备份、替换、重启和健康检查

生产部署不一定是 Git checkout，本次部署目录就没有 `.git`。下面是独立发布目录的通用 Bash 示例；所有环境变量必须由操作者从已核实的运行配置设置。示例不包含任何真实部署地址或凭据。

```bash
set -euo pipefail
: "${RTD_PROJECT_ROOT:?Set the actual project directory}"
: "${RTD_PATCH_ROOT:?Set the reviewed four-file patch directory}"
: "${RTD_BACKUP_ROOT:?Set a private backup parent directory}"
: "${RTD_HEALTH_URL:?Set the verified actual API health URL}"
: "${RTD_EXPECTED_BEFORE_SHA256:?Set the reviewed original-file checksum manifest}"
: "${RTD_EXPECTED_ABSENT_LIST:?Set the reviewed originally-absent paths file; it may be empty}"

paths=(
  rtd/policies/event_point_recovery.py
  rtd/services/battle_generation.py
  rtd/services/battle_entry.py
  rtd/services/battle_layers.py
)
backup="$RTD_BACKUP_ROOT/event-points-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$backup"
cd "$RTD_PROJECT_ROOT"
for rel in "${paths[@]}"; do
  test -f "$RTD_PATCH_ROOT/$rel"
  mkdir -p "$backup/$(dirname "$rel")"
  if test -f "$rel"; then
    cp -p "$rel" "$backup/$rel"
    sha256sum "$rel" >> "$backup/before.sha256"
  else
    printf '%s\n' "$rel" >> "$backup/originally-absent.txt"
  fi
done
python3 -m py_compile "${paths[@]/#/$RTD_PATCH_ROOT/}"
# 清单应由上一步复核的生产副本生成，使用相对项目根目录的文件名。
sha256sum --check "$RTD_EXPECTED_BEFORE_SHA256"
while IFS= read -r rel; do
  test -z "$rel" && continue
  if test -e "$rel"; then
    printf '%s\n' 'Originally absent file appeared; abort and review drift.' >&2
    exit 1
  fi
done < "$RTD_EXPECTED_ABSENT_LIST"
for rel in "${paths[@]}"; do
  cp "$RTD_PATCH_ROOT/$rel" "$rel.next"
  mv "$rel.next" "$rel"
done
systemctl restart rtd-api.service

deadline=$((SECONDS + 180))
healthy=0
while (( SECONDS < deadline )); do
  if curl --noproxy '*' --fail --silent --max-time 3 "$RTD_HEALTH_URL" |
     python3 -c 'import json,sys; h=json.load(sys.stdin); assert h.get("status")=="ok" and h.get("protocol")=="RTD-2.4.0"'; then
    healthy=1
    break
  fi
  if systemctl is-failed --quiet rtd-api.service; then break; fi
  sleep 2
done
if (( healthy != 1 )); then
  printf '%s\n' 'Health failed: restore the recorded backup before continuing.' >&2
  exit 1
fi
systemctl is-active rtd-api.service
```

这是人工操作步骤的示例，不是包含自动回滚的正式部署工具。现场使用时应把备份路径记入私有变更记录，并按下节执行失败恢复；本次实际部署脚本另有自动回滚保护，其私有连接与路径留在 ignored 诊断目录，不能直接推送。

健康地址从实际配置、进程 CLI 与 `ss -ltnp` 确认。API 绑定非回环网卡时，`127.0.0.1` 连接失败只是地址不匹配。`systemctl active` 也不保证 Python 完成主表／资源初始化；应等待实际 HTTP 响应，并结合应用日志区分慢启动与导入失败。服务默认名如被部署环境修改，应使用实际名称。

### 4.1 失败恢复

1. 停止进一步发布与测试输入，保存服务日志和失败类型。
2. 用记录的备份恢复原来存在的文件；核对恢复后的 SHA-256。
3. 新增且原先不存在的补全模块在旧调用文件恢复后可暂留为未引用文件，不需为回滚删除其他文件。
4. 重启 API，使用真实监听地址重新健康检查；确认原服务恢复。
5. 保留原备份、补丁清单和失败记录，查明原因后重新审查，不盲目重复发布。

本次没有修改生产数据库，不需要恢复玩家数据库。若其他变更确实涉及数据库，须另行使用 SQLite 一致性备份与对应恢复流程，不在运行时直接覆盖主库或忽略 WAL。

## 5. 主表与资源缓存的刷新边界

本次故障是新入场协议下发的积分，不是模型包字段。因此部署后应正常退出旧战斗并新开一局，先读取新的 `enemy_info_list`，不要求清空应用账号数据。

若排查其他问题确实改动主表或资源：

1. 备份测试 APK、账号关联数据和需要保留的进度，先确定目标缓存的真实路径及资源身份。
2. 只清理已确认的主表文件或对应缓存条目；或直接替换已确认版本的设备本地下载资源。
3. 留意内置缓存释放标记。仅删载荷或同长度覆盖，可能被旧完成标记或 APK 内置资源再次覆盖；须按资源原有刷新机制处理。
4. 重启应用，观察实际下载请求、缓存命中和主表／资源哈希，证明新版本确实被使用。
5. 清缓存不能修复服务端仍下发 0 分；恢复旧战斗也不会自动获得新入场快照。

本手册不提供猜测路径的批量删除命令，不使用 `pm clear` 代替定位。现场确需清理应用全部数据时，应独立确认账号恢复方案。

## 6. 构建只读观察包

通用源码、完整 CLI 和签名环境变量说明见客户端仓库的 [event-points README](https://github.com/lzt007/RTD_CLIENT/tree/fix/history-event-unlock-verification/diagnostics/event-points)。观察包只用于开发模拟器，不作为正式游戏客户端发布。

构建要求：原测试 APK、其自带 mscorlib／UnityEngine、已有 .NET／Cecil、JDK、Android zipalign 与 apksigner，以及本地签名材料。用环境变量传签名密码，不把真实密码写进命令历史、脚本或文档。工具不下载依赖、不安装 APK、不连接设备或生产。

构建报告必须确认：只修改辅助 `RTDFlow.dll` 并新增 `RTDPointProbe.dll`；游戏主程序集及其余原 ZIP 条目一致；原辅助方法、跳转及异常区域回读一致；纯 getter 形状匹配；拒绝重复注入与覆盖既有输出。通过后才能用 `adb install -r` 安装到已备份的测试设备。

## 7. ADB 导航、战斗和结算回放

在服务端项目根目录运行，先明确工具和测试设备；以下为 PowerShell 变量示例：

```powershell
$Adb = '<absolute-path-to-adb.exe>'
$Serial = '<test-emulator-serial>'
& $Adb devices -l
python scripts/android_event_unlock_replay.py --adb $Adb --serial $Serial --action inspect
```

使用 [导航回放](../../scripts/android_event_unlock_replay.py) 从通知页进入历史活动。`helper-index` 是当前屏幕内可见助战索引，不是账号 ID，需先观察并选择足以通关的已有助战：

```powershell
python scripts/android_event_unlock_replay.py --adb $Adb --serial $Serial --action enter-history --quest 20710 --helper-index 1 --output logs/history-replay
```

多点拖动使用 [RTDInput.java](../../scripts/android/RTDInput.java)，只注入系统 MotionEvent。用本机 JDK 与 Android Build Tools 编译，不提交 DEX 二进制：

```powershell
$Work = 'build/history-input'
$D8 = '<android-build-tools-directory>/d8.bat'
New-Item -ItemType Directory -Force "$Work/classes", "$Work/dex" | Out-Null
javac -source 8 -target 8 -d "$Work/classes" scripts/android/RTDInput.java
& $D8 --min-api 26 --output "$Work/dex" "$Work/classes/RTDInput.class"
& $Adb -s $Serial push "$Work/dex/classes.dex" /data/local/tmp/rtd-input.dex
```

在另一个终端持续保存积分遥测，防止高频界面日志覆盖环形缓冲区：

```powershell
& $Adb -s $Serial logcat -v raw |
  Select-String '^RTD_POINT_PROBE ' |
  ForEach-Object { $_.Line } |
  Tee-Object -FilePath logs/history-point-live.jsonl -Append
```

运行 [战斗回放](../../scripts/android_event_unlock_play.py)：

```powershell
python -X utf8 scripts/android_event_unlock_play.py --adb $Adb --serial $Serial --quest 20710 --input-dex /data/local/tmp/rtd-input.dex --output logs/history-play --use-cure --minimum-points 5 --timeout 1200
```

脚本先核对实际地图哈希，再按可见面板方向与真实位置选路；只用真实点击／拖动攻击和治疗。`--use-cure` 明确允许原技能 11000，按原弹窗 OPEN 状态确认、检查扣魂和实际回血。`--minimum-points 5` 在实际遥测达到门槛后优先前往 Boss，不强行走完全部目标。

脚本在 GameClear 停止，由下一步触发正常结算；遇到未知弹窗、死亡、进程变化或停滞即停止，不自动复活、付费或丢书。治疗动画中确认被忽略时，不盲点：先 inspect，核对原技能后可用 `--action cancel-cure` 正常取消，再继续同一战斗。

```powershell
python scripts/android_event_unlock_replay.py --adb $Adb --serial $Serial --action stage-clear --output logs/history-result
```

## 8. 验收必须闭合的证据链

- 新入场：目标 41028 每只 1 分，非目标为 0；记录实际出现数量及冻结上限。
- 击杀：遥测 `run_points` 对应实际目标逐只增加。`offered_points` 只是可获得上限，访问路线不是击杀证明。
- 通关：由原客户端发送 `clear_quest2`，积分为实际取得值，返回 4096。
- 持久化：只读核对余额、通关位、run cleared、无活动战斗；读取时不输出或修改其他玩家资料。
- 重登：确认结算已成功后完全停止并重启应用，重新通过原登录流程取得余额。不能用 `MMResult` 预加缓存代替该步骤。
- 解锁：重新进入关卡列表，核对 20711／20712 的实际解锁标记和原前置条件。

只查看解锁列表，不额外开局消耗体力：

```powershell
python scripts/android_event_unlock_replay.py --adb $Adb --serial $Serial --action enter-history --stop-at-list --output logs/history-relogin
```

本次实机结果为 7 分到账、重登后 20711 解锁；20712 仍锁定。49/50 边界经协议测试，本次未实机刷满 50 分。对应脱敏结果见 [验收摘要](evidence/history-event-unlock-20261107.json)。

## 9. 保存、恢复和交付

保存每步选择条件、实际坐标、截图哈希、点数日志、服务器成功回执与重新登录证据。记录应含脚本版本和 APK／游戏主程序集哈希，原始日志保留本地 ignored 目录。

确认没有待发送结算后，停止日志与输入控制器，用 `adb install -r` 恢复测试前 APK，保留账号及正常取得的进度，关闭模拟器。不要将开发观察包发布给正常客户端用户，不把部署凭据、签名材料、账号、截图或数据库提交 Git。

可推送内容为两份文档、脱敏摘要、回归测试和通用回放／探针源码。提交前审查全部暂存内容；推送前检查本次全部新增提交，并以远端提交 SHA 核实发布成功。
