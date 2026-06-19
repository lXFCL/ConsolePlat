from PyQt5.QtWidgets import QApplication

from consoleplat.config import AppSettings
from consoleplat.ui.main_window import MainWindow


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
