from __future__ import annotations

from datetime import datetime
from pathlib import Path


def log_exception(context: str, exc: BaseException) -> None:
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} [{context}] {type(exc).__name__}: {exc}\n"
    path.write_text(path.read_text(encoding="utf-8") + line if path.exists() else line, encoding="utf-8")


def _log_path() -> Path:
    from consoleplat.config import default_settings_path

    return default_settings_path().with_name("app.log")
