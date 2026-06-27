from __future__ import annotations

import inspect
import unittest

import temu_goods
from temu_goods import TemuGoodsList


class JitAndInventorySourceTest(unittest.TestCase):
    def test_jit_open_confirms_pending_product_info_before_opening_jit(self) -> None:
        source = inspect.getsource(TemuGoodsList.batch_open_jit_management)

        self.assertIn("_confirm_pending_jit_product_info_if_needed(page)", source)
        self.assertLess(
            source.index("_confirm_pending_jit_product_info_if_needed(page)"),
            source.index("_set_jit_product_page_size(page, target_page_size)"),
        )

    def test_pending_product_info_confirmation_uses_100_page_size_then_refreshes(self) -> None:
        source = inspect.getsource(TemuGoodsList)
        method_source = inspect.getsource(TemuGoodsList._confirm_pending_jit_product_info_if_needed)

        self.assertIn("JIT_PRODUCT_INFO_CONFIRM_PAGE_SIZE = 100", inspect.getsource(temu_goods))
        self.assertIn("def _confirm_pending_jit_product_info_if_needed", source)
        self.assertIn("_activate_jit_pending_product_info_filter(page)", source)
        self.assertIn("_set_jit_product_page_size(page, JIT_PRODUCT_INFO_CONFIRM_PAGE_SIZE)", source)
        self.assertIn("_select_all_jit_products(page)", source)
        self.assertIn("_click_batch_confirm_product_info(page)", source)
        self.assertIn("page.reload(wait_until=\"domcontentloaded\")", source)
        self.assertLess(
            method_source.index("_activate_jit_pending_product_info_filter(page)"),
            method_source.index("_set_jit_product_page_size(page, JIT_PRODUCT_INFO_CONFIRM_PAGE_SIZE)"),
        )
        self.assertLess(
            method_source.index("_set_jit_product_page_size(page, JIT_PRODUCT_INFO_CONFIRM_PAGE_SIZE)"),
            method_source.index("_select_all_jit_products(page)"),
        )
        self.assertGreaterEqual(method_source.count("_activate_jit_pending_product_info_filter(page)"), 2)
        self.assertIn("_ensure_jit_pending_product_info_list_active(page)", method_source)
        self.assertLess(
            method_source.index("_ensure_jit_pending_product_info_list_active(page)"),
            method_source.index("_select_all_jit_products(page)"),
        )

    def test_pending_product_info_helpers_target_real_page_text(self) -> None:
        source = inspect.getsource(TemuGoodsList)

        self.assertIn("TEXT_PENDING_PRODUCT_INFO_CONFIRM", inspect.getsource(temu_goods))
        self.assertIn("TEXT_BATCH_CONFIRM_PRODUCT_INFO", inspect.getsource(temu_goods))
        self.assertIn("def _read_jit_pending_product_info_count", source)
        self.assertIn("def _click_batch_confirm_product_info", source)
        self.assertIn("def _confirm_pending_product_info_modal_if_visible", source)
        self.assertIn("def _ensure_jit_pending_product_info_list_active", source)

    def test_pending_product_info_filter_must_be_clicked_before_continuing(self) -> None:
        source = inspect.getsource(TemuGoodsList._activate_jit_pending_product_info_filter)

        self.assertIn("raise RuntimeError", source)
        self.assertIn("没有成功点击“商品信息待确认”", source)
        self.assertNotIn("继续使用当前列表状态", source)

    def test_pending_product_info_list_requires_selected_quick_filter(self) -> None:
        source = inspect.getsource(TemuGoodsList)
        method_source = inspect.getsource(TemuGoodsList._jit_pending_product_info_list_active)

        self.assertIn("def _jit_pending_product_info_filter_selected", source)
        self.assertIn("_jit_pending_product_info_filter_selected(page)", method_source)

    def test_pending_product_info_reselects_filter_when_confirm_button_stays_disabled(self) -> None:
        source = inspect.getsource(TemuGoodsList)
        method_source = inspect.getsource(TemuGoodsList._confirm_pending_jit_product_info_if_needed)

        self.assertIn("def _jit_batch_confirm_product_info_enabled", source)
        self.assertIn("_jit_batch_confirm_product_info_enabled(page)", method_source)
        self.assertLess(
            method_source.index("_jit_batch_confirm_product_info_enabled(page)"),
            method_source.index("_click_batch_confirm_product_info(page)"),
        )

    def test_jit_confirmation_is_scoped_and_repeated_until_no_modal_remains(self) -> None:
        source = inspect.getsource(TemuGoodsList)
        method_source = inspect.getsource(TemuGoodsList._confirm_all_jit_open_modals)

        self.assertIn("def _confirm_all_jit_open_modals", source)
        self.assertIn("def _click_jit_confirm_button", source)
        self.assertIn("_confirm_all_jit_open_modals(page)", source)
        self.assertIn("for attempt in range(1, 5):", source)
        self.assertIn("return Boolean(findJitConfirmModal())", source)
        self.assertIn("_scroll_jit_confirm_modal_to_bottom(page)", method_source)

    def test_jit_confirm_button_accepts_confirm_or_ok_text_and_nested_label(self) -> None:
        source = inspect.getsource(TemuGoodsList)

        self.assertIn("TEXT_JIT_CONFIRM_OPTIONS", source)
        self.assertIn("confirmTexts.includes(norm(el.innerText || el.textContent))", source)
        self.assertIn("closest('button,[role=\"button\"],a')", source)
        self.assertIn("modalRoot", source)

    def test_jit_confirm_button_scrolls_long_modal_to_bottom_before_clicking(self) -> None:
        source = inspect.getsource(TemuGoodsList)
        method_source = inspect.getsource(TemuGoodsList._click_jit_confirm_button)
        scroll_source = inspect.getsource(TemuGoodsList._scroll_jit_confirm_modal_to_bottom)

        self.assertIn("def _scroll_jit_confirm_modal_to_bottom", source)
        self.assertIn("_scroll_jit_confirm_modal_to_bottom(page)", method_source)
        self.assertLess(
            method_source.index("_scroll_jit_confirm_modal_to_bottom(page)"),
            method_source.index("page.evaluate("),
        )
        self.assertIn("scrollTop = node.scrollHeight", source)
        self.assertIn("findJitConfirmModals()", scroll_source)
        self.assertIn("for (const modal of findJitConfirmModals())", scroll_source)

    def test_jit_confirm_modal_matches_real_mdl_dialog_classes(self) -> None:
        source = inspect.getsource(temu_goods)

        self.assertIn("jit_confirm_modal_selector()", source)
        self.assertIn(".MDL_outerWrapper", source)
        self.assertIn(".MDL_innerWrapper", source)
        self.assertIn(".MDL_body", source)

    def test_jit_batch_open_menu_uses_real_select_dropdown_structure(self) -> None:
        source = inspect.getsource(TemuGoodsList)

        self.assertIn("def _click_batch_adjust_jit_control", source)
        self.assertIn("def _wait_for_jit_popup_item", source)
        self.assertIn("def _activate_jit_popup_item", source)
        self.assertIn(".ST_outerWrapper_5-120-1", source)
        self.assertIn(".cIL_item_5-120-1", source)

    def test_inventory_save_waits_for_completion_and_closes_leftover_dialog(self) -> None:
        source = inspect.getsource(TemuGoodsList)

        self.assertIn("def _wait_for_inventory_setting_save_finished", source)
        self.assertIn("def _has_inventory_setting_edit_modal", source)
        self.assertIn("_wait_for_inventory_setting_save_finished(page)", source)
        self.assertIn("_close_identifier_upload_dialog(page)", source)
        self.assertIn("timeout: int = 30000", source)


if __name__ == "__main__":
    unittest.main()
