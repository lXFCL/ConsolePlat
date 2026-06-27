from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative: str) -> Path:
    """Path for bundled read-only resources such as the Excel template."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


def runtime_root() -> Path:
    """Writable directory beside the exe when frozen, otherwise project root."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent
