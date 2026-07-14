from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def modules_root() -> Path:
    return project_root() / "modules"


def resources_root() -> Path:
    return project_root() / "resources"


def runtime_root() -> Path:
    return project_root() / "runtime"


def default_runtime_dir(name: str) -> Path:
    clean = str(name or "").strip().strip("/\\")
    return runtime_root() / clean if clean else runtime_root()


def default_prints_dir() -> Path:
    return resources_root() / "prints"


def default_download_dir(name: str = "") -> Path:
    base = default_runtime_dir("downloads")
    clean = str(name or "").strip().strip("/\\")
    return base / clean if clean else base


def resource_path(relative_path: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", project_root()))
    return base / relative_path
