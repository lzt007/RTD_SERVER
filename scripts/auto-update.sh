#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
[[ -z $(git status --porcelain) ]] || { echo '工作区存在未提交修改，请先处理。' >&2; exit 1; }
git symbolic-ref -q HEAD >/dev/null || { echo '请先切换到有远端跟踪分支的本地分支。' >&2; exit 1; }
git rev-parse --abbrev-ref '@{upstream}' >/dev/null
git pull --ff-only --no-rebase
echo "更新完成：$(git rev-parse --short HEAD)"
