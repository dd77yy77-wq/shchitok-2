#!/usr/bin/env python3
"""Добавить операции из экспортированного JSON в следующий выпуск Щитка 2."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ALLOWED = {"category_add", "category_rename", "category_delete", "device_add", "device_update", "device_delete", "breaker_update"}

def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def main(source):
    data = read_json(Path(source).resolve())
    if data.get("format") != "shchitok2-changes" or data.get("formatVersion") != 1:
        raise SystemExit("Неподдерживаемый формат файла изменений")
    incoming = data.get("operations")
    if not isinstance(incoming, list):
        raise SystemExit("В файле отсутствует список operations")
    canonical = ASSETS / "release-ops.json"
    current = read_json(canonical) if canonical.exists() else []
    merged = {op["id"]: op for op in current if isinstance(op, dict) and op.get("id")}
    added = 0
    for op in incoming:
        if not isinstance(op, dict) or not op.get("id") or not isinstance(op.get("at"), (int, float)) or op.get("type") not in ALLOWED:
            raise SystemExit("Некорректная операция в файле изменений")
        if op["id"] not in merged:
            merged[op["id"]] = op
            added += 1
    operations = sorted(merged.values(), key=lambda op: (op["at"], op["id"]))
    canonical.write_text(json.dumps(operations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ASSETS / "release-ops.js").write_text(
        "/* Сформировано tools/apply_changes.py. Не редактировать вручную. */\n"
        "window.SHCHITOK2_RELEASE_OPS=" + json.dumps(operations, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    print("Добавлено новых операций:", added)
    print("Всего операций в выпуске:", len(operations))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Использование: python tools/apply_changes.py <shchitok2-changes.json>")
    main(sys.argv[1])
