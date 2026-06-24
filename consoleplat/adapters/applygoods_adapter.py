from __future__ import annotations

import sys
from dataclasses import dataclass
import importlib.util
from pathlib import Path


@dataclass(frozen=True)
class ApplyGoodsAdapter:
    project_dir: Path

    def launch_command(self) -> tuple[str, list[str], Path]:
        entry = self.project_dir / "main.py"
        if entry.exists():
            return sys.executable, [str(entry)], self.project_dir
        return sys.executable, ["-c", "print('ApplyGoods placeholder launch')"], self.project_dir

    def build_embedded_widget(self, parent=None):
        entry = self.project_dir / "main.py"
        if not entry.exists():
            raise FileNotFoundError(f"未找到 ApplyGoods 入口文件：{entry}")
        if str(self.project_dir) not in sys.path:
            sys.path.insert(0, str(self.project_dir))
        spec = importlib.util.spec_from_file_location("applygoods_main", entry)
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载 ApplyGoods 模块：{entry}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        factory = getattr(module, "create_apply_goods_widget", None)
        if factory is None:
            raise AttributeError("ApplyGoods 未提供 create_apply_goods_widget() 入口")
        return factory(parent=parent)
