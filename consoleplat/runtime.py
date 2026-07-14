from __future__ import annotations

import importlib
import runpy
import sys
from pathlib import Path


CLI_MODULES = {
    "monitor-fetch": "consoleplat.services.monitor_fetch_cli",
    "sendgoods-export": "consoleplat.services.sendgoods_export_cli",
    "ai-image-edit": "consoleplat.services.ai_image_edit_cli",
    "version-check": "consoleplat.services.version_check_cli",
}


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def cli_command(name: str, *args: str, unbuffered: bool = False) -> tuple[str, list[str]]:
    if name not in CLI_MODULES:
        raise ValueError(f"未知 ConsolePlat 子命令：{name}")
    if is_frozen():
        return sys.executable, ["--consoleplat-cli", name, *map(str, args)]
    prefix = ["-u"] if unbuffered else []
    return sys.executable, [*prefix, "-m", CLI_MODULES[name], *map(str, args)]


def script_command(path: str | Path, *args: str) -> tuple[str, list[str]]:
    if is_frozen():
        return sys.executable, ["--consoleplat-script", str(path), *map(str, args)]
    return sys.executable, [str(path), *map(str, args)]


def run_cli(name: str, args: list[str]) -> int:
    module_name = CLI_MODULES.get(name)
    if module_name is None:
        print(f"未知 ConsolePlat 子命令：{name}", file=sys.stderr)
        return 2
    sys.argv = [module_name, *args]
    module = importlib.import_module(module_name)
    main = getattr(module, "main", None)
    if not callable(main):
        print(f"子命令没有 main()：{module_name}", file=sys.stderr)
        return 2
    result = main()
    return int(result or 0)


def run_script(path: str | Path, args: list[str]) -> int:
    script = Path(path).resolve()
    if not script.is_file():
        print(f"脚本不存在：{script}", file=sys.stderr)
        return 2
    sys.path.insert(0, str(script.parent))
    sys.argv = [str(script), *args]
    runpy.run_path(str(script), run_name="__main__")
    return 0
