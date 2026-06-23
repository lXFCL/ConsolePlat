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
    assert tab_texts == ["监控", "账号", "生图 / 改图", "发布", "程序"]

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


def test_settings_page_loads_publish_titles_and_program_paths(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(
        AppSettings(
            bo_product_title="BO 固定标题",
            szw_product_title="SZW 固定标题",
            program_data_dir="E:/ConsolePlatData",
            putaway_project_dir="E:/1PythonProject/PutawayAiRobot",
            putaway_data_dir="E:/1PythonProject/PutawayAiRobot/data",
            putaway_log_dir="E:/1PythonProject/PutawayAiRobot/log",
        )
    )
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    edits = {edit.objectName(): edit.text() for edit in page.findChildren(QLineEdit)}
    assert edits["boProductTitleEdit"] == "BO 固定标题"
    assert edits["szwProductTitleEdit"] == "SZW 固定标题"
    assert edits["programDataDirEdit"] == "E:/ConsolePlatData"
    assert edits["putawayProjectDirEdit"] == "E:/1PythonProject/PutawayAiRobot"
    assert edits["putawayDataDirEdit"] == "E:/1PythonProject/PutawayAiRobot/data"
    assert edits["putawayLogDirEdit"] == "E:/1PythonProject/PutawayAiRobot/log"

    page.close()


def test_settings_page_save_persists_publish_and_ai_fields(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings())
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    page.findChild(QLineEdit, "boProductTitleEdit").setText("新的 BO 标题")
    page.findChild(QLineEdit, "szwProductTitleEdit").setText("新的 SZW 标题")
    page.findChild(QLineEdit, "programDataDirEdit").setText("E:/ConsolePlatData")
    page.findChild(QLineEdit, "aiEditApiBaseEdit").setText("https://example.invalid/v1")
    page.findChild(QLineEdit, "aiEditModelEdit").setText("gpt-image-test")
    page.findChild(QLineEdit, "aiEditSizeEdit").setText("1536x1024")
    page.save_settings()

    saved = SettingsStore(path).load()
    assert saved.bo_product_title == "新的 BO 标题"
    assert saved.szw_product_title == "新的 SZW 标题"
    assert saved.program_data_dir == "E:/ConsolePlatData"
    assert saved.ai_edit_api_base == "https://example.invalid/v1"
    assert saved.ai_edit_model == "gpt-image-test"
    assert saved.ai_edit_size == "1536x1024"

    page.close()
