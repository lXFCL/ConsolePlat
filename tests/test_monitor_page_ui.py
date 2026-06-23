from consoleplat.config import AppSettings, SettingsStore
from PyQt5.QtWidgets import QApplication, QComboBox, QPushButton, QScrollArea

from consoleplat.services.monitor_service import MonitorSnapshot

from consoleplat.ui.monitor_page import MonitorPage


def test_monitor_page_uses_scroll_area_for_dense_content():
    app = QApplication.instance() or QApplication([])

    page = MonitorPage()

    scroll_areas = page.findChildren(QScrollArea)
    assert scroll_areas
    assert scroll_areas[0].widgetResizable()
    assert scroll_areas[0].widget() is not None

    page.close()


def test_monitor_page_initial_state_does_not_show_demo_orders():
    app = QApplication.instance() or QApplication([])

    page = MonitorPage()

    assert page.order_table.rowCount() == 0
    assert page.order_table.isHidden()
    assert not page.order_empty_state.isHidden()
    assert page.order_empty_title.objectName() == "monitorEmptyTitle"
    assert page.order_empty_hint.objectName() == "monitorEmptyHint"
    assert all(card.value_label.text() == "0" for card in page.metric_cards.values())
    assert "等待刷新" in page.source_label.text()

    page.close()


def test_monitor_page_has_shop_selector_for_monitor_target():
    app = QApplication.instance() or QApplication([])

    page = MonitorPage()

    combos = page.findChildren(QComboBox)
    assert any(combo.findText("YUHOOBO") >= 0 and combo.findText("YUHAOBO") >= 0 for combo in combos)

    page.close()


def test_monitor_page_loads_saved_refresh_interval(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings(refresh_interval_seconds=17))
    monkeypatch.setattr("consoleplat.ui.monitor_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = MonitorPage()

    assert page.interval_spin.value() == 17

    page.close()


def test_monitor_page_has_export_purchase_sheet_button():
    app = QApplication.instance() or QApplication([])

    page = MonitorPage()

    buttons = page.findChildren(QPushButton)
    assert any(button.text() == "导出备货单" for button in buttons)

    page.close()


def test_monitor_page_order_table_shows_row_numbers():
    app = QApplication.instance() or QApplication([])

    page = MonitorPage()
    page.apply_snapshot(MonitorSnapshot.demo(seed=0), 0)

    assert not page.order_table.isHidden()
    assert page.order_empty_state.isHidden()
    assert page.order_table.horizontalHeaderItem(0).text() == "序号"
    assert page.order_table.item(0, 0).text() == "1"

    page.close()


def test_monitor_page_has_open_export_folder_button():
    app = QApplication.instance() or QApplication([])

    page = MonitorPage()

    buttons = page.findChildren(QPushButton)
    assert any(button.text() == "打开文件夹" for button in buttons)

    page.close()


def test_monitor_page_starts_cleanup_process_on_close(monkeypatch):
    calls = []

    class DummyPopen:
        def __init__(self, args, **kwargs):
            calls.append((args, kwargs))

    monkeypatch.setattr("consoleplat.ui.monitor_page.subprocess.Popen", DummyPopen)
    app = QApplication.instance() or QApplication([])

    page = MonitorPage()
    page.close()

    assert calls
    assert "--close-monitor-pages" in calls[0][0]
