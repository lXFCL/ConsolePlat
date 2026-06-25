from PyQt5.QtWidgets import QApplication, QLabel

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

    assert window.status_pill.text() == "框架预览"
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

    publish_page.process = None
    window.refresh_task_badges()
    assert badge.isHidden()

    window.close()
