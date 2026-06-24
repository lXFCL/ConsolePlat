from PyQt5.QtWidgets import QApplication, QWidget

from consoleplat.config import AppSettings
from consoleplat.ui.main_window import MainWindow


class FakeSettingsStore:
    def load(self):
        return AppSettings(startup_width=1280, startup_height=820)


def test_main_window_builds_only_default_page_on_startup(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    create_calls = []
    app = QApplication.instance() or QApplication([])

    def fake_create_page(self, key):
        create_calls.append(key)
        page = QWidget()
        page.setObjectName(f"fake_{key}_page")
        return page

    monkeypatch.setattr(MainWindow, "_create_page", fake_create_page)

    window = MainWindow()

    assert create_calls == ["monitor"]
    assert window._built == {"monitor"}

    window.close()


def test_main_window_builds_page_once_when_activated(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    create_calls = []
    app = QApplication.instance() or QApplication([])

    def fake_create_page(self, key):
        create_calls.append(key)
        page = QWidget()
        page.setObjectName(f"fake_{key}_page")
        return page

    monkeypatch.setattr(MainWindow, "_create_page", fake_create_page)

    window = MainWindow()
    window.activate_page("putaway")
    window.activate_page("publish")
    window.activate_page("putaway")

    assert create_calls == ["monitor", "putaway", "publish"]
    assert window._built == {"monitor", "putaway", "publish"}

    window.close()
