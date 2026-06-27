from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_SETTINGS: dict[str, Any] = {
    "page_size_mode": "50",
    "custom_page_size": 50,
    "login_phone": "",
    "login_password": "",
}


def load_settings(path: Path) -> dict[str, Any]:
    if not path.exists():
        return dict(DEFAULT_SETTINGS)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_SETTINGS)
    result = dict(DEFAULT_SETTINGS)
    if isinstance(data, dict):
        result.update(data)
    return result


def save_settings(path: Path, settings: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
