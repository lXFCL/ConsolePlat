from PyQt5.QtWidgets import QApplication, QLabel, QWidget

from consoleplat.config import AppSettings, SettingsStore
from consoleplat.ui.apply_goods_page import ApplyGoodsPage


def _page_with_temp_store(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(
        AppSettings(
            applygoods_project_dir="E:/1PythonProject/ApplyGoods",
            program_data_dir=str(tmp_path / "ConsolePlatData"),
        )
    )
    monkeypatch.setattr("consoleplat.ui.apply_goods_page.SettingsStore", lambda: SettingsStore(path))
    return ApplyGoodsPage()


def test_apply_goods_page_mounts_embedded_widget_when_adapter_succeeds(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    class FakeEmbeddedWidget(QWidget):
        pass

    def fake_build(self, parent=None):
        widget = FakeEmbeddedWidget(parent)
        widget.setObjectName("fakeApplyGoodsEmbeddedWidget")
        return widget

    monkeypatch.setattr("consoleplat.ui.apply_goods_page.ApplyGoodsAdapter.build_embedded_widget", fake_build, raising=False)

    page = _page_with_temp_store(tmp_path, monkeypatch)

    assert isinstance(page.embedded_widget, FakeEmbeddedWidget)
    assert page.error_label.isHidden()
    assert page.embedded_widget.parent() is not None
    assert "合规项目目录" not in page.container_panel.findChildren(QLabel)[0].text()

    page.close()


def test_apply_goods_page_shows_import_error_when_embed_load_fails(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    def fake_build(self, parent=None):
        raise ModuleNotFoundError("missing applygoods dependency")

    monkeypatch.setattr("consoleplat.ui.apply_goods_page.ApplyGoodsAdapter.build_embedded_widget", fake_build, raising=False)

    page = _page_with_temp_store(tmp_path, monkeypatch)

    assert page.embedded_widget is None
    assert not page.error_label.isHidden()
    assert "missing applygoods dependency" in page.error_label.text()

    page.close()
