from __future__ import annotations

import unittest
from pathlib import Path

from temu_goods import compliance_modal_container_selector, page_size_option_labels


class PageSizeHelperTest(unittest.TestCase):
    def test_page_size_option_labels_include_spaced_compact_and_numeric_forms(self) -> None:
        self.assertEqual(page_size_option_labels(100), ["100 条/页", "100条/页", "100"])

    def test_compliance_modal_container_selector_supports_dialog_and_drawer_layouts(self) -> None:
        selector = compliance_modal_container_selector()

        self.assertIn(".rocket-drawer-content-wrapper", selector)
        self.assertIn(".rocket-drawer-content", selector)
        self.assertIn(".rocket-drawer-body", selector)
        self.assertIn('[role="dialog"]', selector)
        self.assertIn('[aria-modal="true"]', selector)
        self.assertNotIn(",div", selector)
        self.assertNotIn(",section", selector)
        self.assertNotIn(",aside", selector)

    def test_compliance_javascript_uses_shared_container_selector(self) -> None:
        source = Path("temu_goods.py").read_text(encoding="utf-8")

        self.assertNotIn("document.querySelectorAll('.rocket-drawer-content-wrapper')", source)


if __name__ == "__main__":
    unittest.main()
