from __future__ import annotations

import unittest
from pathlib import Path
from inspect import getsource

from temu_goods import TemuGoodsList


class FakePage:
    def __init__(self) -> None:
        self.waits: list[int] = []

    def wait_for_timeout(self, timeout: int) -> None:
        self.waits.append(timeout)


class ComplianceSubmitTest(unittest.TestCase):
    def test_submit_clicks_i_know_with_visible_text_fallback(self) -> None:
        logs: list[str] = []
        worker = TemuGoodsList(user_data_dir=Path(".browser-profile"), logger=logs.append)
        page = FakePage()
        calls: list[str] = []

        worker._click_compliance_modal_button = lambda _page, text: calls.append(f"confirm:{text}")
        worker._wait_for_page_ready = lambda _page, timeout=0: calls.append(f"ready:{timeout}")
        worker._click_global_button_if_visible = lambda _page, text, timeout=0: False
        worker._click_visible_text_as_button = lambda _page, text: calls.append(f"fallback:{text}") or True

        worker._submit_compliance_upload(page)

        self.assertEqual(
            calls,
            [
                "confirm:确认上传",
                "ready:10000",
                "fallback:我知道了",
            ],
        )
        self.assertIn("已点击“我知道了”。", logs)

    def test_submit_raises_when_success_modal_cannot_be_closed(self) -> None:
        worker = TemuGoodsList(user_data_dir=Path(".browser-profile"))
        page = FakePage()

        worker._click_compliance_modal_button = lambda _page, text: None
        worker._wait_for_page_ready = lambda _page, timeout=0: None
        worker._click_global_button_if_visible = lambda _page, text, timeout=0: False
        worker._click_visible_text_as_button = lambda _page, text: False
        worker._close_compliance_success_modal = lambda _page: False

        with self.assertRaisesRegex(RuntimeError, "没有关闭上传成功提示"):
            worker._submit_compliance_upload(page)

    def test_success_modal_detection_does_not_scan_all_divs(self) -> None:
        close_source = getsource(TemuGoodsList._close_compliance_success_modal)
        has_source = getsource(TemuGoodsList._has_compliance_success_modal)

        self.assertNotIn(".rocket-modal-content,div", close_source)
        self.assertNotIn(".rocket-modal-content,div", has_source)
        self.assertIn("findSuccessModal", close_source)
        self.assertIn("findSuccessModal", has_source)

    def test_compliance_upload_entry_closes_stale_drawer_first(self) -> None:
        source = getsource(TemuGoodsList._click_batch_upload_compliance)

        self.assertIn("_close_existing_compliance_upload_modal", source)
        self.assertNotIn("继续操作", source)


if __name__ == "__main__":
    unittest.main()
