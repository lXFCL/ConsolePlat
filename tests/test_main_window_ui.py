from PyQt5.QtWidgets import QApplication, QLabel

from consoleplat.config import AppSettings
from consoleplat.ui.ai_edit_page import AIEditPage
from consoleplat.ui.local_image_page import LocalImagePage
from consoleplat.ui.main_window import MainWindow
from consoleplat.ui.product_publish_page import ProductPublishPage
from consoleplat.ui.putaway_page import PutawayPage


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


def test_main_window_putaway_page_uses_real_page(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    window.activate_page("putaway")

    assert window.findChildren(PutawayPage)

    window.close()
