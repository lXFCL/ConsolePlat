from PyQt5.QtWidgets import QApplication

from consoleplat.config import AppSettings
from consoleplat.ui.ai_selection_page import AISelectionPage


def test_ai_selection_page_blocks_run_without_program_data_dir():
    app = QApplication.instance() or QApplication([])
    page = AISelectionPage(settings=AppSettings(program_data_dir=""))

    page.start_selection()

    assert "程序数据目录" in page.status_label.text()
    assert page.process is None
    page.close()


def test_ai_selection_page_exports_success_payload_and_loads_latest_batch(tmp_path):
    app = QApplication.instance() or QApplication([])
    page = AISelectionPage(settings=AppSettings(program_data_dir=str(tmp_path)))

    page.handle_fetch_payload(
        {
            "ok": True,
            "candidates": [
                {
                    "title": "商品 A",
                    "sales_text": "已售 99",
                    "sales_count": 99,
                    "price": "$9",
                    "product_url": "https://www.temu.com/goods-a.html",
                    "image_url": "",
                    "keyword": "黑白T恤",
                }
            ],
            "failures": [],
        }
    )

    assert page.results_table.rowCount() == 1
    assert "AI选品" in page.output_label.text()
    assert page.batch_combo.count() == 1
    page.close()


def test_ai_selection_page_pauses_on_login_payload(tmp_path):
    app = QApplication.instance() or QApplication([])
    page = AISelectionPage(settings=AppSettings(program_data_dir=str(tmp_path)))

    page.handle_fetch_payload({"ok": False, "kind": "login", "message": "请完成登录"})

    assert "请完成登录" in page.status_label.text()
    assert page.start_button.isEnabled()
    page.close()
