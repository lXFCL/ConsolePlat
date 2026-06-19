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
