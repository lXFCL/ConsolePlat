from pathlib import Path

from PyQt5.QtWidgets import QApplication, QLabel, QWidget

from consoleplat.config import AppSettings, SettingsStore
from consoleplat.ui.putaway_page import PutawayPage


def _page_with_temp_store(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(
        AppSettings(
            putaway_project_dir="E:/1PythonProject/PutawayAiRobot",
            putaway_data_dir="E:/1PythonProject/PutawayAiRobot/data",
            putaway_log_dir="E:/1PythonProject/PutawayAiRobot/log",
            program_data_dir=str(tmp_path / "ConsolePlatData"),
        )
    )
    monkeypatch.setattr("consoleplat.ui.putaway_page.SettingsStore", lambda: SettingsStore(path))
    return PutawayPage()


def test_putaway_page_does_not_build_embedded_widget_until_requested(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    calls = []

    def fake_build(self, parent=None):
        calls.append(parent)
        return QWidget(parent)

    monkeypatch.setattr("consoleplat.ui.putaway_page.PutawayAdapter.build_embedded_widget", fake_build, raising=False)

    page = _page_with_temp_store(tmp_path, monkeypatch)

    assert calls == []
    assert page.embedded_widget is None
    assert page._embed_loaded is False
    assert page.error_label.isHidden()

    page.close()


def test_putaway_page_mounts_embedded_widget_once_when_loaded(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    calls = []

    class FakeEmbeddedWidget(QWidget):
        pass

    def fake_build(self, parent=None):
        calls.append(parent)
        widget = FakeEmbeddedWidget(parent)
        widget.setObjectName("fakePutawayEmbeddedWidget")
        return widget

    monkeypatch.setattr("consoleplat.ui.putaway_page.PutawayAdapter.build_embedded_widget", fake_build, raising=False)

    page = _page_with_temp_store(tmp_path, monkeypatch)
    page._load_embedded()
    page._load_embedded()

    assert len(calls) == 1
    assert isinstance(page.embedded_widget, FakeEmbeddedWidget)
    assert page._embed_loaded is True
    assert page.error_label.isHidden()
    assert page.embedded_widget.parent() is not None
    assert not hasattr(page, "open_settings_button")
    assert "项目目录：" not in page.container_panel.findChildren(QLabel)[0].text()

    page.close()


def test_putaway_page_shows_import_error_when_embed_load_fails(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    calls = []

    def fake_build(self, parent=None):
        calls.append(parent)
        raise ModuleNotFoundError("missing putaway dependency")

    monkeypatch.setattr("consoleplat.ui.putaway_page.PutawayAdapter.build_embedded_widget", fake_build, raising=False)

    page = _page_with_temp_store(tmp_path, monkeypatch)

    assert calls == []
    assert page.embedded_widget is None
    assert page.error_label.isHidden()

    page._load_embedded()
    page._load_embedded()

    assert len(calls) == 1
    assert page.embedded_widget is None
    assert page._embed_loaded is True
    assert not page.error_label.isHidden()
    assert "missing putaway dependency" in page.error_label.text()

    page.close()
