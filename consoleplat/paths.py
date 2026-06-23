from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resource_path(relative_path: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", project_root()))
    return base / relative_path
