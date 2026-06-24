import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QLabel, QScrollArea, QWidget

sys.path.insert(0, str(Path(__file__).parent.parent))

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


def test_apply_goods_page_does_not_build_embedded_widget_until_requested(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    calls = []

    def fake_build(self, parent=None):
        calls.append(parent)
        return QWidget(parent)

    monkeypatch.setattr("consoleplat.ui.apply_goods_page.ApplyGoodsAdapter.build_embedded_widget", fake_build, raising=False)

    page = _page_with_temp_store(tmp_path, monkeypatch)

    assert calls == []
    assert page.embedded_widget is None
    assert page._embed_loaded is False
    assert page.error_label.isHidden()

    page.close()


def test_apply_goods_page_mounts_embedded_widget_once_when_loaded(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    calls = []

    class FakeEmbeddedWidget(QWidget):
        pass

    def fake_build(self, parent=None):
        calls.append(parent)
        widget = FakeEmbeddedWidget(parent)
        widget.setObjectName("fakeApplyGoodsEmbeddedWidget")
        return widget

    monkeypatch.setattr("consoleplat.ui.apply_goods_page.ApplyGoodsAdapter.build_embedded_widget", fake_build, raising=False)

    page = _page_with_temp_store(tmp_path, monkeypatch)
    page._load_embedded()
    page._load_embedded()
    scroll_areas = page.findChildren(QScrollArea)

    assert len(calls) == 1
    assert isinstance(page.embedded_widget, FakeEmbeddedWidget)
    assert page._embed_loaded is True
    assert scroll_areas
    assert scroll_areas[0].objectName() == "applyGoodsScroll"
    assert scroll_areas[0].widgetResizable()
    assert page.error_label.isHidden()
    assert page.embedded_widget.parent() is not None
    assert page.embedded_widget.parent() is page.embed_shell
    assert "合规项目目录" not in page.container_panel.findChildren(QLabel)[0].text()
    assert page.container_panel.minimumHeight() >= 720
    assert page.embed_shell.layout().contentsMargins().top() >= 18

    page.close()


def test_apply_goods_page_shows_import_error_when_embed_load_fails(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    calls = []

    def fake_build(self, parent=None):
        calls.append(parent)
        raise ModuleNotFoundError("missing applygoods dependency")

    monkeypatch.setattr("consoleplat.ui.apply_goods_page.ApplyGoodsAdapter.build_embedded_widget", fake_build, raising=False)

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
    assert "missing applygoods dependency" in page.error_label.text()

    page.close()


def test_apply_goods_page_uses_scroll_container_for_tall_content(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page = _page_with_temp_store(tmp_path, monkeypatch)
    scroll_areas = page.findChildren(QScrollArea)

    assert scroll_areas
    assert scroll_areas[0].widget() is page.scroll_content
    assert page.scroll_content.layout().contentsMargins().top() >= 8
    assert page.scroll_content.layout().spacing() >= 16

    page.close()


def test_apply_goods_page_uses_updated_header_copy(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page = _page_with_temp_store(tmp_path, monkeypatch)
    labels = [label.text() for label in page.findChildren(QLabel)]

    assert "当前页面直接内嵌 ApplyGoods 界面，已与控制台主题统一配色。可在此连接浏览器并执行套版组、合规上传、JIT 与库存等操作。" in labels
    assert "已改为纵向卷轴式承载，便于在较小窗口里继续操作套版组、合规上传、JIT 和库存流程。" not in labels

    page.close()
