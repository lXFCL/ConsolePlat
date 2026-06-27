from __future__ import annotations

import inspect
import unittest

from temu_goods import TemuGoodsList


class LoginSourceTest(unittest.TestCase):
    def test_worker_has_login_credentials_and_auto_login_hooks(self) -> None:
        source = inspect.getsource(TemuGoodsList)

        self.assertIn("def set_login_credentials", source)
        self.assertIn("def _ensure_authenticated_after_navigation", source)
        self.assertIn("def _is_login_page", source)
        self.assertIn("def _login_with_saved_credentials", source)
        self.assertIn("def _enter_seller_center_if_needed", source)
        self.assertIn("seller.kuajingmaihuo.com", source)
        self.assertNotIn("seller.kuaijingmaihuo.com", source)
        self.assertIn("授权登录", source)
        self.assertIn('"登录"', source)
        self.assertIn("for button_text in", source)
        self.assertIn("#usernameId", source)
        self.assertIn("#passwordId", source)
        self.assertIn("end_time = page.evaluate(\"Date.now()\") + 8000", source)
        self.assertIn("def _is_login_authorization_page", source)
        self.assertIn("def _recover_blank_login_app_if_needed", source)
        self.assertIn("You need to enable JavaScript to run this app.", source)
        self.assertIn("确认授权并前往", source)
        self.assertIn("CBX_squareInputWrapper", source)
        self.assertIn("data-checked", source)
        self.assertIn("for _attempt in range(5)", source)
        self.assertIn("商家中心", source)
        self.assertIn("中国地区", source)

    def test_all_open_page_entries_run_authentication_guard(self) -> None:
        for method_name in [
            "open_goods_list",
            "open_template_group",
            "open_compliance_info",
            "open_compliant_live_photos",
            "open_jit_product_select",
            "open_stock_sale_manage",
        ]:
            source = inspect.getsource(getattr(TemuGoodsList, method_name))
            self.assertIn("_ensure_authenticated_after_navigation(page", source, method_name)


if __name__ == "__main__":
    unittest.main()
