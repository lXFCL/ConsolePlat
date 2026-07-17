from PyQt5.QtGui import QCloseEvent
from PyQt5.QtWidgets import QApplication, QLabel, QMessageBox

from consoleplat.config import AppSettings
from consoleplat.ui.ai_edit_page import AIEditPage
from consoleplat.ui.local_image_page import LocalImagePage
from consoleplat.ui.main_window import MainWindow
from consoleplat.ui.product_publish_page import ProductPublishPage
from consoleplat.ui.putaway_page import PutawayPage
from consoleplat.ui.theme import get_app_style


class FakeSettingsStore:
    def load(self):
        return AppSettings(startup_width=1280, startup_height=820)


def test_main_window_uses_saved_startup_size(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    app = QApplication.instance() or QApplication([])

    window = MainWindow()

    assert window.width() == 1280
    assert window.height() == 820

    window.close()


def test_main_window_applies_saved_theme_and_background(monkeypatch):
    class FakeThemedSettingsStore:
        def load(self):
            return AppSettings(startup_width=1280, startup_height=820, theme_name="dark", bg_image_path="E:/bg.png")

    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeThemedSettingsStore())
    app = QApplication.instance() or QApplication([])

    window = MainWindow()

    assert window.styleSheet() == get_app_style("dark", "E:/bg.png")

    window.close()


def test_main_window_settings_save_refreshes_loaded_monitor(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.activate_page("monitor")
    monitor_page = window.pages["monitor"]
    settings = AppSettings(active_shop="THIRD_SHOP", monitor_shops=["YUHOOBO", "THIRD_SHOP"])

    window._handle_settings_saved(settings)

    assert monitor_page.shop_combo.currentText() == "THIRD_SHOP"
    assert monitor_page.shop_combo.count() == 2
    window.close()


def test_main_window_startup_update_result_shows_clickable_status_pill(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    window._on_startup_update_result(
        {
            "ok": True,
            "has_update": True,
            "release": {"version": "1.5.0"},
        }
    )

    assert window.status_pill.text() == "● 发现新版本 v1.5.0"
    assert window.status_pill.property("hasUpdate") == "true"

    window.status_pill.mousePressEvent(None)

    assert window.state.active_page == "settings"

    window.close()


def test_main_window_startup_update_check_uses_thread_worker(monkeypatch):
    class FakeAutoUpdateSettingsStore:
        def load(self):
            return AppSettings(
                startup_width=1280,
                startup_height=820,
                check_update_on_startup=True,
                update_proxy_enabled=True,
                update_proxy_host="127.0.0.1",
                update_proxy_port=7890,
            )

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

    class FailingProcess:
        def __init__(self, *args, **kwargs):
            raise AssertionError("Startup update check should not create QProcess")

    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeAutoUpdateSettingsStore())
    monkeypatch.setattr("consoleplat.ui.main_window.QThread", FakeThread)
    monkeypatch.setattr("consoleplat.ui.main_window.UpdateCheckWorker", FakeWorker)
    monkeypatch.setattr("consoleplat.ui.main_window.QProcess", FailingProcess)

    window = MainWindow()
    window._maybe_check_update_on_startup()

    assert started["thread_parent"] is window
    assert started["proxy_url"] == "http://127.0.0.1:7890"
    assert started["thread_started"] is True
    assert window._update_check_thread is not None
    assert window._update_check_worker is not None

    window.close()


def test_main_window_startup_update_result_respects_skipped_version(monkeypatch):
    class FakeSkippedSettingsStore:
        def load(self):
            return AppSettings(
                startup_width=1280,
                startup_height=820,
                skipped_update_version="1.5.0",
            )

    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSkippedSettingsStore())
    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    window._on_startup_update_result(
        {
            "ok": True,
            "has_update": True,
            "release": {"version": "1.5.0"},
        }
    )

    assert window.status_pill.text() == "就绪"
    assert window.status_pill.property("hasUpdate") in (None, False)

    window.close()


def test_main_window_closes_monitor_browser_pages(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    calls = []

    def fake_close_pages(self):
        calls.append(self)

    monkeypatch.setattr("consoleplat.ui.monitor_page.MonitorPage._close_monitor_browser_pages", fake_close_pages)
    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    window.close()

    assert len(calls) == 1


def test_main_window_sidebar_uses_larger_nav_icons_except_settings(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    app = QApplication.instance() or QApplication([])

    window = MainWindow()

    for key, button in window.nav_buttons.items():
        icon_labels = [label for label in button.findChildren(QLabel) if label.objectName() == "navIcon"]
        assert icon_labels
        assert icon_labels[0].font().pointSize() == (14 if key == "settings" else 36)

    window.close()


def test_main_window_uses_readable_nav_labels(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    app = QApplication.instance() or QApplication([])

    window = MainWindow()

    assert window.nav_buttons["publish"].accessibleName() == "发布"
    assert window.nav_buttons["putaway"].accessibleName() == "上架"
    assert window.nav_buttons["apply"].accessibleName() == "合规"
    assert window.nav_buttons["monitor"].toolTip() == "店铺实时状态与待处理提醒"

    window.close()


def test_main_window_header_tracks_active_page(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    window.activate_page("ai_edit")

    assert window.page_title_label.text() == "AI 改图"
    assert window.page_description_label.text() == "AI 图片改造与参考图任务"
    assert window.status_pill.text() == "就绪"

    window.close()


def test_main_window_local_image_page_uses_real_page(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    window.activate_page("local_image")

    assert window.findChildren(LocalImagePage)

    window.close()


def test_main_window_ai_edit_page_uses_real_page(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    window.activate_page("ai_edit")

    assert window.findChildren(AIEditPage)

    window.close()


def test_main_window_publish_page_is_before_local_image(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    app = QApplication.instance() or QApplication([])

    window = MainWindow()

    nav_keys = list(window.nav_buttons)
    assert nav_keys[:3] == ["monitor", "publish", "local_image"]
    assert window.nav_buttons["publish"].accessibleName() == "发布"

    window.activate_page("publish")

    assert window.findChildren(ProductPublishPage)

    window.close()


def test_main_window_opens_publish_page_from_monitor_handoff(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    monitor_page = window.pages["monitor"]
    monitor_page.request_open_publish.emit(
        {
            "shop_name": "YUHOOBO",
            "output_path": "E:/exports/purchase.xlsx",
            "total_records": 5,
        }
    )
    publish_page = window.pages["publish"]

    assert window.state.active_page == "publish"
    assert publish_page.task_name_edit.text() == "YUHOOBO 备货单发布"
    assert publish_page.count_spin.value() == 5

    window.close()


def test_main_window_putaway_page_uses_real_page(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    window.activate_page("putaway")

    assert window.findChildren(PutawayPage)

    window.close()


def test_main_window_putaway_page_contains_embedded_widget(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    app = QApplication.instance() or QApplication([])

    class FakeEmbeddedWidget(QLabel):
        def __init__(self, parent=None):
            super().__init__("embedded", parent)
            self.setObjectName("fakePutawayEmbeddedWidget")

    def fake_build(self, parent=None):
        return FakeEmbeddedWidget(parent)

    monkeypatch.setattr("consoleplat.ui.putaway_page.PutawayAdapter.build_embedded_widget", fake_build, raising=False)

    window = MainWindow()
    window.activate_page("putaway")
    page = window.findChildren(PutawayPage)[0]

    assert page.embedded_widget is not None
    assert page.embedded_widget.objectName() == "fakePutawayEmbeddedWidget"
    assert page.error_label.isHidden()

    window.close()


def test_main_window_routes_publish_import_request_to_putaway_page(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    app = QApplication.instance() or QApplication([])
    calls = []

    def fake_prepare(self, record):
        calls.append((self, record))

    monkeypatch.setattr(PutawayPage, "prepare_product_import_from_publish", fake_prepare, raising=False)

    window = MainWindow()
    window.activate_page("publish")
    publish_page = window.pages["publish"]
    record = object()

    publish_page.request_prepare_putaway_import.emit(record)

    assert window.state.active_page == "putaway"
    assert len(calls) == 1
    assert calls[0][0] is window.pages["putaway"]
    assert calls[0][1] is record

    window.close()


def test_main_window_nav_badge_reflects_running_page(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    window.activate_page("publish")
    publish_page = window.pages["publish"]
    publish_page.process = object()
    window.refresh_task_badges()

    badge = window.nav_buttons["publish"].badge_label
    assert not badge.isHidden()
    assert badge.text() == "运行"
    assert window.status_pill.text() == "1 项运行中"

    publish_page.process = None
    window.refresh_task_badges()
    assert badge.isHidden()
    assert window.status_pill.text() == "就绪"

    window.close()


def test_main_window_cancel_close_keeps_running_monitor_open(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.No)
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    monitor_page = window.pages["monitor"]
    monitor_page.timer.start(5000)
    event = QCloseEvent()

    window.closeEvent(event)

    assert not event.isAccepted()
    assert monitor_page.timer.isActive()
    monitor_page.timer.stop()
    window.close()


def test_main_window_confirm_close_cleans_up_running_monitor(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)
    calls = []
    monkeypatch.setattr(
        "consoleplat.ui.monitor_page.MonitorPage._close_monitor_browser_pages",
        lambda self: calls.append(self),
    )
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    monitor_page = window.pages["monitor"]
    monitor_page.timer.start(5000)
    event = QCloseEvent()

    window.closeEvent(event)

    assert event.isAccepted()
    assert calls == [monitor_page]
    monitor_page.timer.stop()


def test_main_window_has_tutorial_button(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    app = QApplication.instance() or QApplication([])

    window = MainWindow()

    assert window.tutorial_button.objectName() == "tutorialButton"
    assert window.tutorial_button.text() == "?"

    window.close()


def test_main_window_tutorial_button_opens_overlay(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    window.show()
    window.activate_page("monitor")
    window.tutorial_button.click()

    assert window.tutorial_overlay is not None
    assert window.tutorial_overlay.isVisible()
    assert window.tutorial_overlay.title_label.text().startswith("1/")

    window.close()
