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


def test_publish_controls_show_configured_declare_price(monkeypatch):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    monkeypatch.setattr(PutawayEmbeddedWidget, "_load_accounts_ui", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "_load_product_rows_ui", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "_reload_browser_options", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "refresh_pages", lambda self: None)
    monkeypatch.setattr(
        "browser_dom_automation.load_runtime_settings",
        lambda: {"declare_price": "14"},
    )

    widget = create_putaway_widget()

    assert widget.select_shop_category_btn.text() == "开始批量上架"
    assert isinstance(widget.declare_price_input, QtWidgets.QDoubleSpinBox)
    assert widget.declare_price_input.decimals() == 2
    assert widget.declare_price_input.minimum() > 0
    assert widget.declare_price_input.value() == 14

    widget.deleteLater()


def test_publish_controls_show_configured_custom_weights(monkeypatch):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    monkeypatch.setattr(PutawayEmbeddedWidget, "_load_accounts_ui", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "_load_product_rows_ui", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "_reload_browser_options", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "refresh_pages", lambda self: None)
    monkeypatch.setattr(
        "browser_dom_automation.load_runtime_settings",
        lambda: {"declare_price": "14", "weights": [140, 145, 150, 155, 160]},
    )

    widget = create_putaway_widget()

    assert len(widget.weight_inputs) == 5
    assert all(isinstance(weight_input, QtWidgets.QSpinBox) for weight_input in widget.weight_inputs)
    assert [weight_input.value() for weight_input in widget.weight_inputs] == [140, 145, 150, 155, 160]

    widget.deleteLater()


def test_publish_confirmation_saves_and_snapshots_declare_price(monkeypatch):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    events = []
    captured = {}

    monkeypatch.setattr(PutawayEmbeddedWidget, "_load_accounts_ui", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "_load_product_rows_ui", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "_load_runtime_settings_ui", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "_reload_browser_options", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "refresh_pages", lambda self: None)
    monkeypatch.setattr(
        PutawayEmbeddedWidget,
        "_collect_product_rows_ui",
        lambda self: [
            {"shop_name": "店铺A", "category": "T恤", "sku": "SKU-1"},
            {"shop_name": "店铺A", "category": "T恤", "sku": "SKU-2"},
        ],
    )
    monkeypatch.setattr(
        "browser_dom_automation.validate_sku_images",
        lambda skus: {"exists": True, "image_count": 2, "missing": []},
    )
    monkeypatch.setattr(
        PutawayEmbeddedWidget,
        "_selected_credentials",
        lambda self: {"username": "user", "password": "secret"},
    )
    monkeypatch.setattr(
        PutawayEmbeddedWidget,
        "_save_runtime_settings_from_ui",
        lambda self: events.append("saved"),
    )
    monkeypatch.setattr(PutawayEmbeddedWidget, "_selected_tab_url", lambda self: "https://example.test")
    monkeypatch.setattr(PutawayEmbeddedWidget, "_selected_tab_ws", lambda self: "ws://example.test")
    monkeypatch.setattr(PutawayEmbeddedWidget, "_app_screen_geometry", lambda self: {})

    def confirm(_parent, _title, text, *_args, **_kwargs):
        events.append("confirmed")
        captured["confirmation_text"] = text
        return QtWidgets.QMessageBox.Yes

    class FakeWorker:
        pass

    def build_worker(*args, **kwargs):
        events.append("worker_created")
        captured["worker_args"] = args
        captured["worker_kwargs"] = kwargs
        return FakeWorker()

    monkeypatch.setattr(QtWidgets.QMessageBox, "question", confirm)
    monkeypatch.setattr("browser_dom_automation.BatchPublishWorker", build_worker)
    monkeypatch.setattr(
        PutawayEmbeddedWidget,
        "_run_action",
        lambda self, worker, message: captured.update(worker=worker, status=message),
    )

    widget = create_putaway_widget()
    widget.declare_price_input.setValue(14.5)
    widget.parallel_publish_input.setValue(2)
    widget.select_shop_category_selected()

    assert events == ["saved", "confirmed", "worker_created"]
    assert "真实批量上架" in captured["confirmation_text"]
    assert "有效商品：2 条" in captured["confirmation_text"]
    assert "申报价格：14.5" in captured["confirmation_text"]
    assert captured["worker_kwargs"]["declare_price"] == "14.5"
    assert "申报价格14.5" in captured["status"]

    widget.deleteLater()


def test_publish_confirmation_snapshots_custom_weights(monkeypatch):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    captured = {}

    monkeypatch.setattr(PutawayEmbeddedWidget, "_load_accounts_ui", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "_load_product_rows_ui", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "_load_runtime_settings_ui", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "_reload_browser_options", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "refresh_pages", lambda self: None)
    monkeypatch.setattr(
        PutawayEmbeddedWidget,
        "_collect_product_rows_ui",
        lambda self: [{"shop_name": "店铺A", "category": "T恤", "sku": "SKU-1"}],
    )
    monkeypatch.setattr(
        "browser_dom_automation.validate_sku_images",
        lambda skus: {"exists": True, "image_count": 1, "missing": []},
    )
    monkeypatch.setattr(
        PutawayEmbeddedWidget,
        "_selected_credentials",
        lambda self: {"username": "user", "password": "secret"},
    )
    monkeypatch.setattr(PutawayEmbeddedWidget, "_save_runtime_settings_from_ui", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "_selected_tab_url", lambda self: "https://example.test")
    monkeypatch.setattr(PutawayEmbeddedWidget, "_selected_tab_ws", lambda self: "ws://example.test")
    monkeypatch.setattr(PutawayEmbeddedWidget, "_app_screen_geometry", lambda self: {})
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "question",
        lambda _parent, _title, text, *_args, **_kwargs: captured.update(confirmation_text=text) or QtWidgets.QMessageBox.Yes,
    )

    class FakeWorker:
        pass

    monkeypatch.setattr(
        "browser_dom_automation.BatchPublishWorker",
        lambda *args, **kwargs: captured.update(worker_kwargs=kwargs) or FakeWorker(),
    )
    monkeypatch.setattr(
        PutawayEmbeddedWidget,
        "_run_action",
        lambda self, worker, message: captured.update(status=message),
    )

    widget = create_putaway_widget()
    custom_weights = [140, 145, 150, 155, 160]
    for input_box, value in zip(widget.weight_inputs, custom_weights):
        input_box.setValue(value)
    widget.select_shop_category_selected()

    assert "克重：140/145/150/155/160g" in captured["confirmation_text"]
    assert captured["worker_kwargs"]["weights"] == tuple(custom_weights)
    assert "克重140/145/150/155/160g" in captured["status"]

    widget.deleteLater()


def test_cancel_publish_confirmation_does_not_create_worker(monkeypatch):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    worker_created = []

    monkeypatch.setattr(PutawayEmbeddedWidget, "_load_accounts_ui", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "_load_product_rows_ui", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "_load_runtime_settings_ui", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "_reload_browser_options", lambda self: None)
    monkeypatch.setattr(PutawayEmbeddedWidget, "refresh_pages", lambda self: None)
    monkeypatch.setattr(
        PutawayEmbeddedWidget,
        "_collect_product_rows_ui",
        lambda self: [{"shop_name": "店铺A", "category": "T恤", "sku": "SKU-1"}],
    )
    monkeypatch.setattr(
        "browser_dom_automation.validate_sku_images",
        lambda skus: {"exists": True, "image_count": 1, "missing": []},
    )
    monkeypatch.setattr(
        PutawayEmbeddedWidget,
        "_selected_credentials",
        lambda self: {"username": "user", "password": "secret"},
    )
    monkeypatch.setattr(PutawayEmbeddedWidget, "_save_runtime_settings_from_ui", lambda self: None)
    monkeypatch.setattr(QtWidgets.QMessageBox, "question", lambda *_args, **_kwargs: QtWidgets.QMessageBox.No)
    monkeypatch.setattr(
        "browser_dom_automation.BatchPublishWorker",
        lambda *args, **kwargs: worker_created.append((args, kwargs)),
    )

    widget = create_putaway_widget()
    widget.select_shop_category_selected()

    assert worker_created == []

    widget.deleteLater()
