from consoleplat.config import AppSettings, SettingsStore
from consoleplat.ui.settings_page import SettingsPage
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QWidget,
)


def test_settings_page_exposes_monitor_export_dir(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings(purchase_export_dir="E:/exports/purchase"))
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    edits = page.findChildren(QLineEdit)
    assert any(edit.objectName() == "purchaseExportDirEdit" and edit.text() == "E:/exports/purchase" for edit in edits)

    page.close()


def test_settings_page_exposes_monitor_print_gallery_controls(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(
        AppSettings(
            print_gallery_source="github",
            print_gallery_local_dir="E:/prints/cache",
            print_gallery_github_raw_base_url="https://raw.githubusercontent.com/demo/gallery/main",
        )
    )
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    monitor_panel = page.stack.widget(0)
    edits = {edit.objectName(): edit.text() for edit in monitor_panel.findChildren(QLineEdit)}
    combos = {combo.objectName(): combo.currentText() for combo in monitor_panel.findChildren(QComboBox)}
    labels = [label.text() for label in monitor_panel.findChildren(QLabel)]

    assert "印花来源" in labels
    assert combos["printGallerySourceCombo"] == "来自 GitHub"
    assert edits["printGalleryLocalDirEdit"] == "E:/prints/cache"
    assert edits["printGalleryGithubRawBaseEdit"] == "https://raw.githubusercontent.com/demo/gallery/main"
    assert page.findChild(QPushButton, "testPrintGalleryGithubButton") is not None
    assert page.findChild(QLabel, "printGalleryGithubTestStatusLabel") is not None

    page.close()


def test_settings_page_save_persists_print_gallery_controls(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings())
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    page.findChild(QComboBox, "printGallerySourceCombo").setCurrentText("来自 GitHub")
    page.findChild(QLineEdit, "printGalleryLocalDirEdit").setText("E:/prints/cache")
    page.findChild(QLineEdit, "printGalleryGithubRawBaseEdit").setText(
        "https://raw.githubusercontent.com/demo/gallery/main"
    )
    page.save_settings()
    saved = SettingsStore(path).load()

    assert saved.print_gallery_source == "github"
    assert saved.print_gallery_local_dir == "E:/prints/cache"
    assert saved.print_gallery_github_raw_base_url == "https://raw.githubusercontent.com/demo/gallery/main"

    page.close()


def test_settings_page_test_print_gallery_uses_current_form_values(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings(print_gallery_local_dir="E:/old/cache"))
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])
    started = {}

    class FakeThread:
        def __init__(self, parent=None):
            started["thread_parent"] = parent
            self.started = FakeSignal()
            self.finished = FakeSignal()

        def start(self):
            started["thread_started"] = True

        def quit(self):
            pass

        def deleteLater(self):
            pass

    class FakeSignal:
        def __init__(self):
            self.callbacks = []

        def connect(self, callback):
            self.callbacks.append(callback)

    class FakeWorker:
        def __init__(self, github_url, local_gallery_dir, proxy=None):
            started["github_url"] = github_url
            started["local_gallery_dir"] = local_gallery_dir
            started["proxy_enabled"] = proxy.enabled
            started["proxy_url"] = proxy.url
            self.finished = FakeSignal()

        def moveToThread(self, thread):
            started["moved_to_thread"] = thread

        def run(self):
            pass

        def deleteLater(self):
            pass

    monkeypatch.setattr("consoleplat.ui.settings_page.QThread", FakeThread)
    monkeypatch.setattr("consoleplat.ui.settings_page._PrintGalleryGithubTestWorker", FakeWorker)

    page = SettingsPage()
    page.findChild(QLineEdit, "printGalleryLocalDirEdit").setText(str(tmp_path / "current-gallery"))
    page.findChild(QLineEdit, "printGalleryGithubRawBaseEdit").setText("https://github.com/demo/gallery")
    page.findChild(QCheckBox, "updateProxyEnabledCheck").setChecked(False)
    page.findChild(QLineEdit, "updateProxyHostEdit").setText("127.0.0.9")
    page.findChild(QSpinBox, "updateProxyPortSpin").setValue(10809)
    page.test_print_gallery_github()

    assert started["thread_parent"] is page
    assert started["thread_started"] is True
    assert started["github_url"] == "https://github.com/demo/gallery"
    assert started["local_gallery_dir"] == str(tmp_path / "current-gallery")
    assert started["proxy_enabled"] is False
    assert started["proxy_url"] == "http://127.0.0.9:10809"
    assert page.findChild(QPushButton, "testPrintGalleryGithubButton").isEnabled() is False

    page.close()


def test_settings_page_test_print_gallery_requires_github_url(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings())
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()
    page.findChild(QLineEdit, "printGalleryGithubRawBaseEdit").setText("")
    page.test_print_gallery_github()

    assert page.findChild(QLabel, "printGalleryGithubTestStatusLabel").text() == "请先填写 GitHub 图集地址"
    assert page._print_gallery_test_thread is None

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
    assert tab_texts == ["监控", "账号", "生图 / 改图", "发布", "上架", "合规", "程序", "外观", "更新"]

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

    program_panel = page.stack.widget(6)
    program_labels = [label.text() for label in program_panel.findChildren(QLabel)]

    assert "程序模块" in program_labels
    assert "程序数据目录" in program_labels
    assert "启动宽度" in program_labels
    assert "启动高度" in program_labels
    assert "上架项目目录" not in program_labels
    assert "上架 data 目录" not in program_labels
    assert "上架日志目录" not in program_labels

    page.close()


def test_settings_page_appearance_panel_exposes_theme_and_background_controls(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings(theme_name="dark", bg_image_path="E:/bg.png"))
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    appearance_panel = page.stack.widget(7)
    assert isinstance(appearance_panel, QScrollArea)
    assert page.tab_buttons["appearance"].text() == "外观"
    assert page.findChild(QComboBox, "themeCombo").currentText().startswith("深色")
    assert page.findChild(QLineEdit, "bgImageEdit").text() == "E:/bg.png"

    page.close()


def test_settings_page_update_panel_exposes_update_controls(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings(check_update_on_startup=False, update_proxy_host="127.0.0.2", update_proxy_port=10809))
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    update_panel = page.stack.widget(8)
    update_labels = [label.text() for label in update_panel.findChildren(QLabel)]
    assert isinstance(update_panel, QScrollArea)
    assert page.tab_buttons["update"].text() == "更新"
    assert "软件更新" in update_labels
    assert page.findChild(QCheckBox, "checkUpdateOnStartupCheck").isChecked() is False
    assert page.findChild(QProgressBar, "downloadProgress") is not None
    assert page.findChild(QTextEdit, "releaseNotesEdit").isReadOnly()
    assert page.findChild(QPushButton, "checkUpdateButton").text() == "检查更新"
    assert page.findChild(QPushButton, "downloadUpdateButton").isEnabled() is False
    assert page.findChild(QCheckBox, "updateProxyEnabledCheck").isChecked() is True
    assert page.findChild(QLineEdit, "updateProxyHostEdit").text() == "127.0.0.2"
    assert page.findChild(QSpinBox, "updateProxyPortSpin").value() == 10809

    page.close()


def test_settings_page_update_checks_share_one_option_row(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings())
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    option_row = page.findChild(QWidget, "updateOptionRow")
    startup_check = page.findChild(QCheckBox, "checkUpdateOnStartupCheck")
    proxy_check = page.findChild(QCheckBox, "updateProxyEnabledCheck")

    assert option_row is not None
    assert startup_check.parent() is option_row
    assert proxy_check.parent() is option_row

    page.close()


def test_settings_page_save_persists_update_startup_toggle(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(
        AppSettings(
            check_update_on_startup=True,
            last_update_check="2026-06-25T10:00:00",
            skipped_update_version="1.5.0",
            update_download_dir="E:/downloads",
            update_proxy_enabled=True,
            update_proxy_host="127.0.0.1",
            update_proxy_port=7890,
        )
    )
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    page.findChild(QCheckBox, "checkUpdateOnStartupCheck").setChecked(False)
    page.findChild(QCheckBox, "updateProxyEnabledCheck").setChecked(False)
    page.findChild(QLineEdit, "updateProxyHostEdit").setText("127.0.0.2")
    page.findChild(QSpinBox, "updateProxyPortSpin").setValue(10809)
    page.save_settings()
    saved = SettingsStore(path).load()

    assert saved.check_update_on_startup is False
    assert saved.last_update_check == "2026-06-25T10:00:00"
    assert saved.skipped_update_version == "1.5.0"
    assert saved.update_download_dir == "E:/downloads"
    assert saved.update_proxy_enabled is False
    assert saved.update_proxy_host == "127.0.0.2"
    assert saved.update_proxy_port == 10809

    page.close()


def test_settings_page_applies_successful_update_check_result(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings())
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    page._apply_update_check_result(
        {
            "ok": True,
            "has_update": True,
            "release": {
                "version": "1.5.0",
                "tag_name": "v1.5.0",
                "body": "更新日志正文",
                "download_url": "https://example.invalid/app.zip",
                "asset_name": "app.zip",
            },
        }
    )

    assert page.latest_version_label.text().startswith("最新版本：v1.5.0")
    assert page.release_notes_edit.toPlainText() == "更新日志正文"
    assert page.download_update_button.isEnabled() is True
    assert page.skip_version_button.isEnabled() is True

    page.close()


def test_settings_page_shows_missing_release_update_result(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings())
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    page._apply_update_check_result(
        {
            "ok": False,
            "kind": "no_release",
            "message": "GitHub 已连通，但仓库还没有发布 Release",
        }
    )

    assert page.update_status_label.text() == "GitHub 已连通，但仓库还没有发布 Release"
    assert page.download_update_button.isEnabled() is False
    assert page.skip_version_button.isEnabled() is False

    page.close()


def test_settings_page_check_update_uses_thread_worker_instead_of_qprocess(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings(update_proxy_enabled=True, update_proxy_host="127.0.0.1", update_proxy_port=7890))
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])
    started = {}

    class FakeThread:
        def __init__(self, parent=None):
            started["thread_parent"] = parent
            self.started = FakeSignal()
            self.finished = FakeSignal()

        def start(self):
            started["thread_started"] = True

        def quit(self):
            started["thread_quit"] = True

        def deleteLater(self):
            started["thread_deleted"] = True

    class FakeSignal:
        def __init__(self):
            self.callbacks = []

        def connect(self, callback):
            self.callbacks.append(callback)

    class FakeWorker:
        def __init__(self, proxy):
            started["proxy_url"] = proxy.url
            self.finished = FakeSignal()

        def moveToThread(self, thread):
            started["moved_to_thread"] = thread

        def run(self):
            started["worker_run_connected"] = True

        def deleteLater(self):
            started["worker_deleted"] = True

    monkeypatch.setattr("consoleplat.ui.settings_page.QThread", FakeThread)
    monkeypatch.setattr("consoleplat.ui.settings_page._UpdateCheckWorker", FakeWorker)

    page = SettingsPage()
    page.check_for_update()

    assert started["thread_parent"] is page
    assert started["proxy_url"] == "http://127.0.0.1:7890"
    assert started["thread_started"] is True
    assert page._update_thread is not None
    assert page._update_worker is not None

    page.close()


def test_settings_page_check_update_uses_current_proxy_controls_before_save(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings(update_proxy_enabled=True, update_proxy_host="127.0.0.1", update_proxy_port=7890))
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])
    started = {}

    class FakeThread:
        def __init__(self, parent=None):
            self.started = FakeSignal()
            self.finished = FakeSignal()

        def start(self):
            started["thread_started"] = True

        def quit(self):
            pass

        def deleteLater(self):
            pass

    class FakeSignal:
        def __init__(self):
            self.callbacks = []

        def connect(self, callback):
            self.callbacks.append(callback)

    class FakeWorker:
        def __init__(self, proxy):
            started["proxy_enabled"] = proxy.enabled
            started["proxy_url"] = proxy.url
            self.finished = FakeSignal()

        def moveToThread(self, thread):
            pass

        def run(self):
            pass

        def deleteLater(self):
            pass

    monkeypatch.setattr("consoleplat.ui.settings_page.QThread", FakeThread)
    monkeypatch.setattr("consoleplat.ui.settings_page._UpdateCheckWorker", FakeWorker)

    page = SettingsPage()
    page.findChild(QCheckBox, "updateProxyEnabledCheck").setChecked(False)
    page.findChild(QLineEdit, "updateProxyHostEdit").setText("127.0.0.9")
    page.findChild(QSpinBox, "updateProxyPortSpin").setValue(10809)
    page.check_for_update()

    assert started["proxy_enabled"] is False
    assert started["proxy_url"] == "http://127.0.0.9:10809"
    assert started["thread_started"] is True

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


def test_settings_page_apply_panel_contains_applygoods_path(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings(applygoods_project_dir="E:/1PythonProject/ApplyGoods"))
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    apply_panel = page.stack.widget(5)
    apply_labels = [label.text() for label in apply_panel.findChildren(QLabel)]
    edits = {edit.objectName(): edit.text() for edit in apply_panel.findChildren(QLineEdit)}

    assert "合规模块" in apply_labels
    assert "合规项目目录" in apply_labels
    assert edits["applyGoodsProjectDirEdit"] == "E:/1PythonProject/ApplyGoods"

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
    layout = image_panel.widget().layout()
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

    for index in (0, 1, 3, 4, 5, 6):
        panel = page.stack.widget(index)
        layout = panel.widget().layout()
        assert layout.spacing() <= 14
        assert layout.contentsMargins().top() <= 22
        forms = panel.findChildren(QFormLayout)
        assert forms
        for form in forms:
            assert form.verticalSpacing() <= 10
            assert form.horizontalSpacing() <= 12

    page.close()


def test_settings_page_panels_use_expected_fill_policy(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings())
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()
    page.resize(1180, 760)
    page.show()
    app.processEvents()

    page.activate_module(2)
    app.processEvents()
    image_panel = page.stack.widget(2)
    assert image_panel.widget().minimumHeight() >= image_panel.viewport().height()
    assert page.stack.height() >= 500

    for index in (0, 1, 3, 4, 5, 6, 7, 8):
        page.activate_module(index)
        app.processEvents()
        panel = page.stack.widget(index)
        assert panel.widgetResizable() is False
        assert panel.widget().minimumHeight() == 0
        assert page.stack.maximumHeight() <= panel.widget().sizeHint().height() + 4

    page.close()


def test_settings_page_shrink_wraps_non_image_panels_without_gray_tail(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings())
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()
    page.resize(1180, 760)
    page.show()
    app.processEvents()

    for index in (0, 1, 3, 4, 5, 6, 7, 8):
        page.activate_module(index)
        app.processEvents()
        scroll = page.stack.widget(index)
        content = scroll.widget()
        assert content.height() == content.sizeHint().height()
        assert content.width() == scroll.viewport().width()
        assert page.stack.height() <= content.height() + 4

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


def test_settings_page_exposes_posai_resource_download_controls(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(
        AppSettings(
            posai_comfyui_dir="E:/ConsolePlat/modules/PosAiImg/ComfyUI",
            posai_resource_download_dir="E:/ConsolePlat/runtime/downloads/posai",
            posai_comfyui_download_url="https://example.invalid/comfyui.zip",
            posai_models_download_url="https://example.invalid/models.zip",
        )
    )
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    image_panel = page.stack.widget(2)
    edits = {edit.objectName(): edit.text() for edit in image_panel.findChildren(QLineEdit)}

    assert edits["posaiComfyuiDirEdit"] == "E:/ConsolePlat/modules/PosAiImg/ComfyUI"
    assert edits["posaiResourceDownloadDirEdit"] == "E:/ConsolePlat/runtime/downloads/posai"
    assert edits["posaiComfyuiDownloadUrlEdit"] == "https://example.invalid/comfyui.zip"
    assert edits["posaiModelsDownloadUrlEdit"] == "https://example.invalid/models.zip"
    assert page.findChild(QPushButton, "downloadPosaiComfyuiButton") is not None
    assert page.findChild(QPushButton, "downloadPosaiModelsButton") is not None
    assert page.findChild(QPushButton, "detectPosaiResourcesButton") is not None
    assert page.findChild(QPushButton, "clearPosaiResourcesButton") is not None
    assert page.findChild(QProgressBar, "posaiResourceDownloadProgress") is not None
    assert page.findChild(QLabel, "posaiResourceStatusLabel") is not None

    page.close()


def test_settings_page_save_persists_posai_resource_download_controls(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings())
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    page.findChild(QLineEdit, "posaiComfyuiDirEdit").setText("E:/portable/ComfyUI")
    page.findChild(QLineEdit, "posaiResourceDownloadDirEdit").setText("E:/portable/downloads")
    page.findChild(QLineEdit, "posaiComfyuiDownloadUrlEdit").setText("https://example.invalid/comfyui.zip")
    page.findChild(QLineEdit, "posaiModelsDownloadUrlEdit").setText("https://example.invalid/models.zip")
    page.save_settings()
    saved = SettingsStore(path).load()

    assert saved.posai_comfyui_dir == "E:/portable/ComfyUI"
    assert saved.posai_resource_download_dir == "E:/portable/downloads"
    assert saved.posai_comfyui_download_url == "https://example.invalid/comfyui.zip"
    assert saved.posai_models_download_url == "https://example.invalid/models.zip"

    page.close()


def test_settings_page_posai_download_requires_url_before_starting_thread(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings(posai_comfyui_download_url=""))
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()
    page.findChild(QLineEdit, "posaiComfyuiDownloadUrlEdit").setText("")
    page.download_posai_comfyui()

    assert "待配置" in page.findChild(QLabel, "posaiResourceStatusLabel").text()
    assert page._posai_download_thread is None

    page.close()
