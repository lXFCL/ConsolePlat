import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).parent.parent))

from consoleplat.config import AppSettings, SettingsStore
from consoleplat.ui.main_window import MainWindow
from consoleplat.ui.settings_page import SettingsPage


def test_appsettings_exposes_applygoods_project_dir():
    settings = AppSettings()

    assert hasattr(settings, "applygoods_project_dir")
    assert settings.applygoods_project_dir == "E:/1PythonProject/ApplyGoods"


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

    assert tab_texts == ["监控", "账号", "生图 / 改图", "发布", "上架", "合规", "程序"]
    assert edits["applyGoodsProjectDirEdit"] == "E:/1PythonProject/ApplyGoods"

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
