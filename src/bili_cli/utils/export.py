"""Export helpers."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def export_data(data: Any, output: str) -> None:
    path = Path(output).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix == ".json":
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return
    if suffix in {".yaml", ".yml"}:
        import yaml

        path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return
    if suffix == ".csv":
        rows = data if isinstance(data, list) else [data]
        keys: list[str] = []
        for row in rows:
            if isinstance(row, dict):
                keys.extend([key for key in row.keys() if key not in keys])
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=keys)
            writer.writeheader()
            for row in rows:
                writer.writerow({key: _flatten(row.get(key)) for key in keys})
        return
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _flatten(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return "" if value is None else str(value)
