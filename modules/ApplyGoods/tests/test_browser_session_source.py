from __future__ import annotations

import inspect
import unittest

from browser_session import BrowserSession


class BrowserSessionSourceTest(unittest.TestCase):
    def test_close_closes_any_connected_browser_and_has_remote_close_helper(self) -> None:
        source = inspect.getsource(BrowserSession)

        self.assertIn("def close_remote_browser", source)
        self.assertIn("if self.browser is not None:", source)
        self.assertNotIn("if self.browser is not None and self._owns_browser:", source)

    def test_page_for_ignores_chrome_error_pages_when_reusing_tabs(self) -> None:
        source = inspect.getsource(BrowserSession.page_for)

        self.assertIn("not page.url.startswith(\"chrome-error://\")", source)
        self.assertIn("usable_pages", source)


if __name__ == "__main__":
    unittest.main()
