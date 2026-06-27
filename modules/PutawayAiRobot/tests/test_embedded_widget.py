from pathlib import Path
import sys

from PyQt5 import QtWidgets

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_version import APP_TITLE
from browser_dom_automation import MainWindow, PutawayEmbeddedWidget, create_putaway_widget


def test_create_putaway_widget_builds_embeddable_widget(monkeypatch):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    monkeypatch.setattr(PutawayEmbeddedWidget, "_load_accounts_ui", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "_load_product_rows_ui", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "_load_runtime_settings_ui", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "_reload_browser_options", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "refresh_pages", lambda self: None)

    widget = create_putaway_widget()

    assert isinstance(widget, PutawayEmbeddedWidget)
    assert widget.parent() is None
    assert widget.tabs.count() == 4
    assert widget.windowTitle() == ""

    widget.deleteLater()


def test_main_window_wraps_embedded_widget(monkeypatch):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    monkeypatch.setattr(PutawayEmbeddedWidget, "_load_accounts_ui", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "_load_product_rows_ui", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "_load_runtime_settings_ui", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "_reload_browser_options", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "refresh_pages", lambda self: None)

    window = MainWindow()

    assert isinstance(window.centralWidget(), PutawayEmbeddedWidget)
    assert window.windowTitle() == APP_TITLE

    window.close()
