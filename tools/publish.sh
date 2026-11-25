#!/bin/bash
# Сборка и публикация только в dd77yy77-wq/shchitok-2.
# Запуск из любой папки: bash tools/publish.sh <code> <name> "<заметки>"
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE="$(git -C "$ROOT" remote get-url origin)"
case "$REMOTE" in
  "https://github.com/dd77yy77-wq/shchitok-2.git"|"git@github.com:dd77yy77-wq/shchitok-2.git") ;;
  *) echo "Отказ: origin должен указывать только на dd77yy77-wq/shchitok-2" >&2; exit 1 ;;
esac
python "$ROOT/build.py" "$1" "$2" "$ROOT/Shchitok2.apk"
python - "$ROOT/version.json" "$1" "$2" "$3" <<'PY'
import json, sys
path, code, name, notes = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
with open(path, 'w', encoding='utf-8') as f:
    json.dump({'code': code, 'name': name, 'notes': notes}, f, ensure_ascii=False)
    f.write('\n')
PY
git -C "$ROOT" add -A
git -C "$ROOT" commit -m "Щиток 2 $2: $3"
git -C "$ROOT" push origin main
