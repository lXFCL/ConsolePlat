import re
import time


def _first_visible(locator, timeout_ms: int):
    try:
        locator.wait_for(state="visible", timeout=timeout_ms)
        return locator
    except Exception:
        return None


def _pick_visible_dialog(page, title_keywords):
    for kw in title_keywords:
        try:
            dlg = page.locator("div.ant-modal:visible", has_text=re.compile(re.escape(kw), re.I)).last
            if _first_visible(dlg, 450):
                return dlg
        except Exception:
            pass
        try:
            dlg = page.locator('div[role="dialog"]:visible', has_text=re.compile(re.escape(kw), re.I)).last
            if _first_visible(dlg, 450):
                return dlg
        except Exception:
            pass
        try:
            dlg = page.locator("div.el-dialog__wrapper:visible", has_text=re.compile(re.escape(kw), re.I)).last
            if _first_visible(dlg, 450):
                return dlg
        except Exception:
            pass
    for dlg in [
        page.locator("div.ant-modal:visible").last,
        page.locator('div[role="dialog"]:visible').last,
        page.locator("div.el-dialog__wrapper:visible").last,
        page.locator("div.ant-popover:visible").last,
        page.locator("div.ant-dropdown:visible").last,
    ]:
        if _first_visible(dlg, 450):
            return dlg
    return None


def _click_first(locators, timeout_ms: int):
    last = None
    for loc in locators:
        try:
            loc.wait_for(state="visible", timeout=timeout_ms)
            try:
                loc.scroll_into_view_if_needed(timeout=timeout_ms)
            except Exception:
                pass
            loc.click(timeout=timeout_ms)
            return True
        except Exception as e:
            last = e
            continue
    if last is not None:
        raise last
    return False


def fill_declare_price_batch(page, price_text: str = "13", progress=None):
    price_text = (price_text or "").strip() or "13"

    if progress:
        progress("打开申报价格批量填写…")

    _click_first(
        [
            page.locator('xpath=//*[contains(normalize-space(.),"申报价格")]/following::span[contains(normalize-space(.),"批量")][1]').first,
            page.locator('span.link:has-text("(批量)")').first,
            page.get_by_text(re.compile(r"\\(\\s*批量\\s*\\)")).first,
            page.get_by_text("(批量)").first,
        ],
        timeout_ms=2500,
    )

    try:
        page.wait_for_timeout(180)
    except Exception:
        time.sleep(0.18)

    dlg = _pick_visible_dialog(page, ["申报价格", "批量"])
    if dlg is None:
        dlg = page

    if progress:
        progress("填写申报价格…")

    inp = None
    for loc in [
        dlg.locator('input.ant-input.input-number[placeholder="示例：1.00"]').first,
        dlg.locator('input[placeholder="示例：1.00"]').first,
        dlg.locator('input.ant-input.input-number').first,
        page.locator('input.ant-input.input-number[placeholder="示例：1.00"]').first,
        page.locator('input[placeholder="示例：1.00"]').first,
    ]:
        try:
            loc.wait_for(state="visible", timeout=2500)
            inp = loc
            break
        except Exception:
            continue
    if inp is None:
        raise RuntimeError("未找到申报价格批量输入框")

    try:
        inp.scroll_into_view_if_needed(timeout=900)
    except Exception:
        pass
    try:
        inp.click(timeout=900)
    except Exception:
        pass
    inp.fill(price_text, timeout=1500)

    if progress:
        progress("确认申报价格…")

    _click_first(
        [
            dlg.locator('button.ant-btn-primary:has-text("确定")').first,
            dlg.get_by_role("button", name="确定").first,
            dlg.locator('button:has-text("确定")').first,
            page.locator('button.ant-btn-primary:has-text("确定")').first,
            page.get_by_role("button", name="确定").first,
        ],
        timeout_ms=2500,
    )

    try:
        if dlg is not page:
            dlg.wait_for(state="hidden", timeout=3500)
    except Exception:
        pass
