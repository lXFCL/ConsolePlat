from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
import importlib.util
import inspect

from consoleplat.runtime import script_command


@dataclass(frozen=True)
class PutawayAdapter:
    project_dir: Path
    data_dir_path: Path
    log_dir_path: Path

    def launch_command(self) -> tuple[str, list[str], Path]:
        entry = self.project_dir / "browser_dom_automation.py"
        program, args = script_command(entry)
        return program, args, self.project_dir

    def build_embedded_widget(self, parent=None, home_url: str = "", album_url: str = ""):
        entry = self.project_dir / "browser_dom_automation.py"
        if not entry.exists():
            raise FileNotFoundError(f"未找到 PutawayAiRobot 入口文件：{entry}")
        if str(self.project_dir) not in sys.path:
            sys.path.insert(0, str(self.project_dir))
        spec = importlib.util.spec_from_file_location("putaway_browser_dom_automation", entry)
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载 PutawayAiRobot 模块：{entry}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        factory = getattr(module, "create_putaway_widget", None)
        if factory is None:
            raise AttributeError("PutawayAiRobot 未提供 create_putaway_widget() 入口")
        parameters = inspect.signature(factory).parameters
        accepts_var_keywords = any(
            parameter.kind is inspect.Parameter.VAR_KEYWORD
            for parameter in parameters.values()
        )
        kwargs = {"parent": parent}
        if accepts_var_keywords or "home_url" in parameters:
            kwargs["home_url"] = home_url
        if accepts_var_keywords or "album_url" in parameters:
            kwargs["album_url"] = album_url
        return factory(**kwargs)
