from consoleplat.config import AppSettings, SettingsStore
from consoleplat.ui.settings_page import SettingsPage
from PyQt5.QtWidgets import QApplication, QLineEdit, QPushButton, QSpinBox


def test_settings_page_exposes_monitor_export_dir(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings(purchase_export_dir="E:/exports/purchase"))
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    edits = page.findChildren(QLineEdit)
    assert any(edit.objectName() == "purchaseExportDirEdit" and edit.text() == "E:/exports/purchase" for edit in edits)

    page.close()


def test_settings_page_has_module_tabs(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings())
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    tab_texts = [
        button.text()
        for button in page.findChildren(QPushButton)
        if button.objectName() == "settingsTabButton"
    ]
    assert tab_texts == ["监控", "账号", "程序"]

    page.close()


def test_settings_page_loads_startup_window_size(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings(startup_width=1280, startup_height=820))
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    spins = {spin.objectName(): spin.value() for spin in page.findChildren(QSpinBox)}
    assert spins["startupWidthSpin"] == 1280
    assert spins["startupHeightSpin"] == 820

    page.close()
