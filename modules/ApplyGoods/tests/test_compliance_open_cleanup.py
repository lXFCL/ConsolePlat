from __future__ import annotations

import unittest
from pathlib import Path

from temu_goods import TemuGoodsList


class FakeSession:
    def __init__(self, page) -> None:
        self.page = page

    def connect_or_launch(self) -> None:
        return None

    def page_for(self, _url_contains: str):
        return self.page


class FakePage:
    url = "https://agentseller.temu.com/govern/information-supplementation"

    def wait_for_load_state(self, _state: str, timeout: int) -> None:
        return None


class ComplianceOpenCleanupTest(unittest.TestCase):
    def test_open_compliance_info_cleans_existing_success_modal(self) -> None:
        worker = TemuGoodsList(user_data_dir=Path(".browser-profile"))
        page = FakePage()
        calls: list[str] = []
        worker.session = FakeSession(page)
        worker._wait_for_page_ready = lambda _page: calls.append("ready")
        worker._dismiss_existing_compliance_success_modal = lambda _page: calls.append("cleanup")

        result = worker.open_compliance_info()

        self.assertIs(result, page)
        self.assertEqual(calls, ["ready", "cleanup"])


if __name__ == "__main__":
    unittest.main()
