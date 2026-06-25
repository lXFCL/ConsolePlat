import sys
import importlib.util
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QLabel
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from consoleplat.config import AppSettings, SettingsStore
from consoleplat.ui.main_window import MainWindow
from consoleplat.ui.settings_page import SettingsPage


def test_appsettings_exposes_applygoods_project_dir():
    settings = AppSettings()

    assert hasattr(settings, "applygoods_project_dir")
    assert settings.applygoods_project_dir == ""


def test_settings_page_has_apply_module_tab_and_path_field(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings())
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    tab_texts = [
        button.text()
        for button in page.findChildren(type(page.save_button))
        if button.objectName() == "settingsTabButton"
    ]
    edits = {edit.objectName(): edit.text() for edit in page.findChildren(type(page.putaway_project_dir_edit))}
    labels = [label.text() for label in page.findChildren(QLabel)]

    assert tab_texts == ["监控", "账号", "生图 / 改图", "发布", "上架", "合规", "程序", "外观", "更新"]
    assert edits["applyGoodsProjectDirEdit"] == ""
    assert any("ApplyGoods" in text for text in labels)

    page.close()


def test_main_window_apply_page_uses_real_page(monkeypatch):
    class FakeSettingsStore:
        def load(self):
            return AppSettings(startup_width=1280, startup_height=820)

    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    window.activate_page("apply")

    current_page = window.stack.currentWidget()

    assert type(current_page).__name__ == "ApplyGoodsPage"

    window.close()


def test_applygoods_adapter_module_exists_and_missing_entry_raises():
    from consoleplat.adapters.applygoods_adapter import ApplyGoodsAdapter

    adapter = ApplyGoodsAdapter(project_dir=Path("/nonexistent/path/ApplyGoods"))

    try:
        adapter.build_embedded_widget()
    except FileNotFoundError as exc:
        assert "未找到 ApplyGoods 入口文件" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")


def test_applygoods_adapter_loads_dataclass_module_from_file(tmp_path):
    from consoleplat.adapters.applygoods_adapter import ApplyGoodsAdapter

    project_dir = tmp_path / "ApplyGoods"
    project_dir.mkdir()
    (project_dir / "main.py").write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "from dataclasses import dataclass",
                "from typing import Callable",
                "",
                "@dataclass(frozen=True)",
                "class Payload:",
                "    value: str",
                "    callback: Callable[[str], None] | None = None",
                "",
                "def create_apply_goods_widget(parent=None):",
                "    return Payload('ok')",
                "",
            ]
        ),
        encoding="utf-8",
    )

    adapter = ApplyGoodsAdapter(project_dir=project_dir)

    widget = adapter.build_embedded_widget()

    assert widget.value == "ok"


def test_applygoods_embedded_widget_hides_workflow_overview():
    applygoods_root = Path(r"E:\1PythonProject\ApplyGoods")
    entry = applygoods_root / "main.py"
    if str(applygoods_root) not in sys.path:
        sys.path.insert(0, str(applygoods_root))
    spec = importlib.util.spec_from_file_location("applygoods_real_main_for_test", entry)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    app = QApplication.instance() or QApplication([])
    widget = module.ApplyGoodsEmbeddedWidget()
    texts = [label.text() for label in widget.findChildren(type(widget.summary_label))]

    assert "流程总览" not in texts
    assert "按顺序向下执行，每一步都单独成卡，减少内嵌场景下的横向拥挤。" not in texts

    widget.close()
