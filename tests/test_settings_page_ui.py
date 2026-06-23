from consoleplat.config import AppSettings, SettingsStore
from consoleplat.ui.settings_page import SettingsPage
from PyQt5.QtWidgets import QApplication, QComboBox, QFormLayout, QLabel, QLineEdit, QPushButton, QSpinBox


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
    assert tab_texts == ["监控", "账号", "生图 / 改图", "发布", "上架", "程序"]

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


def test_settings_page_program_panel_only_keeps_program_fields(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings())
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    program_panel = page.stack.widget(5)
    program_labels = [label.text() for label in program_panel.findChildren(QLabel)]

    assert "程序模块" in program_labels
    assert "程序数据目录" in program_labels
    assert "启动宽度" in program_labels
    assert "启动高度" in program_labels
    assert "上架项目目录" not in program_labels
    assert "上架 data 目录" not in program_labels
    assert "上架日志目录" not in program_labels

    page.close()


def test_settings_page_putaway_panel_contains_putaway_paths(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings())
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    putaway_panel = page.stack.widget(4)
    putaway_labels = [label.text() for label in putaway_panel.findChildren(QLabel)]

    assert "上架模块" in putaway_labels
    assert "上架项目目录" in putaway_labels
    assert "上架 data 目录" in putaway_labels
    assert "上架日志目录" in putaway_labels

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


def test_settings_page_exposes_ai_provider_controls(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(
        AppSettings(
            default_ai_provider_id="provider-2",
            ai_providers=[
                {
                    "provider_id": "provider-1",
                    "name": "主接口",
                    "api_key": "key-1",
                    "api_base": "https://one.example/v1",
                    "model": "gpt-image-a",
                    "size": "1024x1024",
                },
                {
                    "provider_id": "provider-2",
                    "name": "备用接口",
                    "api_key": "key-2",
                    "api_base": "https://two.example/v1",
                    "model": "gpt-image-b",
                    "size": "1536x1024",
                },
            ],
        )
    )
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    provider_combo = page.findChild(QComboBox, "aiProviderCombo")
    assert provider_combo is not None
    assert provider_combo.count() == 2
    assert provider_combo.currentText() == "备用接口"
    assert page.findChild(QLineEdit, "aiEditApiKeyEdit") is not None

    page.close()


def test_settings_page_save_persists_default_ai_provider(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(
        AppSettings(
            default_ai_provider_id="provider-1",
            ai_providers=[
                {
                    "provider_id": "provider-1",
                    "name": "主接口",
                    "api_key": "key-1",
                    "api_base": "https://one.example/v1",
                    "model": "gpt-image-a",
                    "size": "1024x1024",
                },
                {
                    "provider_id": "provider-2",
                    "name": "备用接口",
                    "api_key": "key-2",
                    "api_base": "https://two.example/v1",
                    "model": "gpt-image-b",
                    "size": "1536x1024",
                },
            ],
        )
    )
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    page.findChild(QComboBox, "aiProviderCombo").setCurrentText("备用接口")
    page.findChild(QLineEdit, "aiEditApiKeyEdit").setText("new-key-2")
    page.findChild(QLineEdit, "aiEditApiBaseEdit").setText("https://two-new.example/v1")
    page.findChild(QLineEdit, "aiEditModelEdit").setText("gpt-image-c")
    page.findChild(QLineEdit, "aiEditSizeEdit").setText("2048x2048")
    page.save_settings()

    saved = SettingsStore(path).load()
    assert saved.default_ai_provider_id == "provider-2"
    assert [provider.name for provider in saved.ai_providers] == ["主接口", "备用接口"]
    assert saved.ai_providers[1].api_key == "new-key-2"
    assert saved.ai_providers[1].api_base == "https://two-new.example/v1"
    assert saved.ai_providers[1].model == "gpt-image-c"
    assert saved.ai_providers[1].size == "2048x2048"

    page.close()


def test_settings_page_image_panel_stays_compact(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings())
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    image_panel = page.stack.widget(2)
    layout = image_panel.layout()
    assert layout.spacing() <= 12
    assert layout.contentsMargins().top() <= 18
    assert page.ai_edit_prompt_edit.maximumHeight() <= 96
    assert isinstance(image_panel.findChildren(QFormLayout)[0], QFormLayout)
    assert page.ai_provider_combo.maximumWidth() <= 260

    page.close()


def test_settings_page_other_panels_stay_compact(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings())
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    for index in (0, 1, 3, 4, 5):
        panel = page.stack.widget(index)
        layout = panel.layout()
        assert layout.spacing() <= 14
        assert layout.contentsMargins().top() <= 22
        forms = panel.findChildren(QFormLayout)
        assert forms
        for form in forms:
            assert form.verticalSpacing() <= 10
            assert form.horizontalSpacing() <= 12

    page.close()


def test_settings_page_non_image_panels_push_extra_space_below_form(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings())
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    for index in (0, 1, 3, 4, 5):
        panel = page.stack.widget(index)
        layout = panel.layout()
        trailing_item = layout.itemAt(layout.count() - 1)
        assert trailing_item is not None
        assert trailing_item.spacerItem() is not None

    page.close()


def test_settings_page_loads_posai_model_root(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings(posai_model_root="E:/1PythonProject/PosAiImg/模特图-干净"))
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    edits = {edit.objectName(): edit.text() for edit in page.findChildren(QLineEdit)}
    assert edits["posaiModelRootEdit"] == "E:/1PythonProject/PosAiImg/模特图-干净"

    page.close()


def test_settings_page_save_persists_posai_model_root(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings())
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    page.findChild(QLineEdit, "posaiModelRootEdit").setText("E:/1PythonProject/PosAiImg/custom-models")
    page.save_settings()

    saved = SettingsStore(path).load()
    assert saved.posai_model_root == "E:/1PythonProject/PosAiImg/custom-models"

    page.close()
