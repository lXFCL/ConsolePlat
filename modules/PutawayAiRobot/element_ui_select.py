import re
import time


def get_el_form_item_value(page, label_text: str) -> str:
    label_text = (label_text or "").strip()
    if not label_text:
        return ""
    for loc in [
        page.locator(f'.el-form-item:has-text("{label_text}") input').first,
        page.locator(f'xpath=//*[contains(normalize-space(.),"{label_text}")]/following::input[1]').first,
    ]:
        try:
            val = (loc.input_value(timeout=800) or "").strip()
            if val:
                return val
        except Exception:
            continue
    return ""


def open_el_form_item_dropdown(page, label_text: str, placeholder_re=None) -> bool:
    label_text = (label_text or "").strip()
    for loc in [
        page.locator(f'.el-form-item:has-text("{label_text}") .el-select').first,
        page.locator(f'.el-form-item:has-text("{label_text}") input').first,
        page.locator(f'xpath=//*[contains(normalize-space(.),"{label_text}")]/following::div[contains(@class,"el-select")][1]').first,
        page.locator(f'xpath=//*[contains(normalize-space(.),"{label_text}")]/following::input[1]').first,
    ]:
        try:
            loc.click(timeout=2000)
            return True
        except Exception:
            continue
    if placeholder_re is not None:
        for loc in [
            page.get_by_placeholder(placeholder_re).first,
            page.get_by_text(placeholder_re).first,
        ]:
            try:
                loc.click(timeout=2000)
                return True
            except Exception:
                continue
    return False


def select_el_option_by_text(page, option_text: str):
    option_text = (option_text or "").strip()
    if not option_text:
        raise RuntimeError("选项文字为空")

    def _wait_dropdown_hidden():
        try:
            page.locator("div.el-select-dropdown:visible").first.wait_for(state="hidden", timeout=1200)
        except Exception:
            pass

    def _try_item_click():
        try:
            item = page.locator(
                "div.el-select-dropdown:visible li.el-select-dropdown__item:not(.is-disabled)",
                has_text=option_text,
            ).first
        except TypeError:
            item = (
                page.locator("div.el-select-dropdown:visible li.el-select-dropdown__item:not(.is-disabled)")
                .filter(has_text=option_text)
                .first
            )
        item.wait_for(state="visible", timeout=1500)
        item.click(timeout=1500)
        _wait_dropdown_hidden()

    def _try_type_filter():
        try:
            inp = page.locator("div.el-select-dropdown:visible input").first
            inp.wait_for(state="visible", timeout=600)
            inp.fill(option_text, timeout=600)
            return True
        except Exception:
            pass
        try:
            inp = page.locator("input:focus").first
            inp.fill(option_text, timeout=600)
            return True
        except Exception:
            return False

    try:
        _try_item_click()
        return
    except Exception:
        pass

    try:
        typed = _try_type_filter()
        if not typed:
            page.keyboard.type(option_text, delay=5)
        time.sleep(0.15)
    except Exception:
        pass

    try:
        _try_item_click()
        return
    except Exception:
        pass

    try:
        page.keyboard.press("Enter")
        time.sleep(0.15)
        try:
            dropdown_visible = page.locator("div.el-select-dropdown:visible").count()
        except Exception:
            dropdown_visible = 1
        if dropdown_visible == 0:
            return
    except Exception:
        pass

    try:
        _try_item_click()
        return
    except Exception:
        pass

    text_re = re.compile(re.escape(option_text))
    for loc in [
        page.get_by_role("option", name=option_text, exact=True).first,
        page.get_by_role("menuitem", name=option_text, exact=True).first,
        page.get_by_text(option_text, exact=True).first,
        page.get_by_role("option", name=text_re).first,
        page.get_by_role("menuitem", name=text_re).first,
        page.get_by_text(text_re).first,
    ]:
        try:
            loc.click(timeout=2500)
            return
        except Exception:
            continue
    raise RuntimeError(f"未找到选项：{option_text}")
