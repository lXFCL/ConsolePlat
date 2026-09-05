from pathlib import Path

from PyQt5.QtWidgets import QApplication, QLabel, QLineEdit, QTabWidget, QWidget

from consoleplat.adapters.putaway_adapter import PutawayAdapter
from consoleplat.config import AppSettings, SettingsStore
from consoleplat.ui.putaway_page import PutawayPage


def test_putaway_adapter_loads_legacy_factory_without_custom_url_parameters(tmp_path):
    project_dir = tmp_path / "PutawayAiRobot"
    project_dir.mkdir()
    (project_dir / "browser_dom_automation.py").write_text(
        "\n".join(
            [
                "def create_putaway_widget(parent=None):",
                "    return {'parent': parent, 'factory': 'legacy'}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    parent = object()
    adapter = PutawayAdapter(
        project_dir=project_dir,
        data_dir_path=project_dir / "data",
        log_dir_path=project_dir / "log",
    )

    widget = adapter.build_embedded_widget(
        parent=parent,
        home_url="https://www.dianxiaomi.com/home.htm",
        album_url="https://www.dianxiaomi.com/web/service/album",
    )

    assert widget == {"parent": parent, "factory": "legacy"}


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

    def fake_build(self, parent=None, **_kwargs):
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

    def fake_build(self, parent=None, **_kwargs):
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


def test_putaway_page_passes_custom_urls_to_embedded_widget(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    captured = {}

    class FakeEmbeddedWidget(QWidget):
        pass

    def fake_build(self, parent=None, home_url="", album_url=""):
        captured["parent"] = parent
        captured["home_url"] = home_url
        captured["album_url"] = album_url
        return FakeEmbeddedWidget(parent)

    monkeypatch.setattr("consoleplat.ui.putaway_page.PutawayAdapter.build_embedded_widget", fake_build, raising=False)
    path = tmp_path / "settings.json"
    SettingsStore(path).save(
        AppSettings(
            putaway_project_dir="E:/1PythonProject/PutawayAiRobot",
            putaway_home_url="https://www.dianxiaomi.com/web/home",
            putaway_album_url="https://www.dianxiaomi.com/web/service/album",
        )
    )
    monkeypatch.setattr("consoleplat.ui.putaway_page.SettingsStore", lambda: SettingsStore(path))
    page = PutawayPage()

    page._load_embedded()

    assert captured["parent"] is page.container_panel
    assert captured["home_url"] == "https://www.dianxiaomi.com/web/home"
    assert captured["album_url"] == "https://www.dianxiaomi.com/web/service/album"
    page.close()


def test_putaway_page_shows_import_error_when_embed_load_fails(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    calls = []

    def fake_build(self, parent=None, **_kwargs):
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


def test_putaway_page_prepare_product_import_switches_tab_and_imports_latest_excel(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    calls = []

    class FakeEmbeddedWidget(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.tabs = QTabWidget(self)
            self.tabs.addTab(QWidget(), "自动化")
            self.tabs.addTab(QWidget(), "产品数据")
            self.latest_excel_dir_input = QLineEdit(self)

        def clear_product_rows(self):
            calls.append("clear")

        def import_from_latest_excel(self):
            calls.append("import")

    def fake_build(self, parent=None, **_kwargs):
        return FakeEmbeddedWidget(parent)

    monkeypatch.setattr("consoleplat.ui.putaway_page.PutawayAdapter.build_embedded_widget", fake_build, raising=False)
    page = _page_with_temp_store(tmp_path, monkeypatch)

    page.prepare_product_import_from_publish(object())

    assert page.embedded_widget.tabs.tabText(page.embedded_widget.tabs.currentIndex()) == "产品数据"
    assert page.embedded_widget.latest_excel_dir_input.text() == "E:/1PythonProject/PutawayAiRobot/data"
    assert calls == ["clear", "import"]
    assert "已从发布任务进入产品数据导入" in page.status_label.text()

    page.close()
