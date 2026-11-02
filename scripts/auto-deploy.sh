#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
TARGET=/home/RTD_SERVER
[[ $EUID -eq 0 ]] || { echo '请使用 sudo 执行部署脚本。' >&2; exit 1; }
for command in git python3 rsync systemctl flock; do
    command -v "$command" >/dev/null || { echo "缺少命令：$command" >&2; exit 1; }
done
exec 9>/run/lock/rtd-deploy.lock
flock -n 9 || { echo '已有部署正在执行。' >&2; exit 1; }
[[ $(realpath -m "$TARGET") != "$ROOT" ]] || { echo '代码仓库与部署目录必须分开。' >&2; exit 1; }
bash "$ROOT/scripts/auto-update.sh"
STAGE=$(mktemp -d)
trap 'rm -rf -- "$STAGE"' EXIT
git -C "$ROOT" archive HEAD | tar -x -C "$STAGE"
# 备份失败立即退出，部署目录尚未修改。SQLite backup API 包含 WAL 数据。
python3 - "$TARGET" "$STAGE/.database-excludes" <<'PY'
import datetime
import json
import pathlib
import sqlite3
import sys
root = pathlib.Path(sys.argv[1])
excludes = pathlib.Path(sys.argv[2])
excludes.write_text('')
config = root / 'rtd.config.json'
if not config.exists():
    if root.exists() and any(root.iterdir()):
        raise SystemExit('部署目录非空且缺少配置，无法确定数据库位置。')
    print('首次部署：没有现有数据库需要备份。')
else:
    settings = json.loads(config.read_text(encoding='utf-8'))
    db = pathlib.Path(settings['paths']['database'])
    if not db.is_absolute():
        db = root / db
    try:
        relative = db.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        pass
    else:
        excludes.write_text(''.join('/' + relative + suffix + '\n' for suffix in ('', '-wal', '-shm', '-journal')))
    if not db.is_file():
        raise SystemExit('配置中的数据库不存在，停止部署。')
    backups = root / 'backups' / 'deployment'
    backups.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = backups / (stamp + '.sqlite3')
    with sqlite3.connect(db.resolve().as_uri() + '?mode=ro', uri=True) as source:
        with sqlite3.connect(output) as dest:
            source.backup(dest)
            if dest.execute('PRAGMA integrity_check').fetchone() != ('ok',):
                raise SystemExit('数据库备份完整性检查失败。')
    output.chmod(0o600)
    print('数据库备份完成：', output)
PY
mkdir -p "$TARGET"
# 保留线上配置、数据库、资源、日志和虚拟环境，不删除目标端文件。
rsync -a --exclude-from="$STAGE/.database-excludes" --exclude='/.database-excludes' --exclude='/rtd.config.json' --exclude='/data/' --exclude='/backups/' --exclude='/resources/' --exclude='/logs/' --exclude='/.venv/' "$STAGE/" "$TARGET/"
if [[ ! -f "$TARGET/rtd.config.json" ]]; then
    cp "$STAGE/rtd.config.json" "$TARGET/rtd.config.json"
fi
systemctl restart rtd-api.service rtd-resources.service
systemctl is-active --quiet rtd-api.service
systemctl is-active --quiet rtd-resources.service
echo '部署完成，rtd-api 和 rtd-resources 已重启。'
