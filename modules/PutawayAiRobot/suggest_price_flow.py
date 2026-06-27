import time


def _first_visible(locator, timeout_ms: int):
    try:
        locator.wait_for(state="visible", timeout=timeout_ms)
        return locator
    except Exception:
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


def _pick_send_icon(page):
    for loc in [
        page.locator('i.iconfont.icon_send.link.ml-4:visible').first,
        page.locator('i.iconfont.icon_send:visible').first,
        page.locator('i[class*="icon_send"]:visible').first,
    ]:
        if _first_visible(loc, 1000):
            return loc
    return None


def _find_target_input(page):
    for loc in [
        page.locator('input[class*="!w-90"][class*="g-form-component"]:visible').first,
        page.locator('input[maxlength="14"][class*="g-form-component"]:visible').first,
        page.locator('i.iconfont.icon_send:visible').first.locator('xpath=ancestor::*[self::div or self::td or self::tr][1]//input[contains(@class,"g-form-component") and contains(@class,"!w-90")]').first,
        page.locator('i.iconfont.icon_send:visible').first.locator('xpath=ancestor::*[self::div or self::td or self::tr][1]//input[@maxlength="14" and contains(@class,"g-form-component")]').first,
        page.locator('input[name="weight"]:visible').first,
        page.locator('input[placeholder="请输入"][name="weight"]:visible').first,
    ]:
        try:
            loc.wait_for(state="visible", timeout=1200)
            return loc
        except Exception:
            continue
    return None


def _fill_value_and_pick_icon(page, value: str):
    target = _find_target_input(page)
    if target is None:
        return None

    try:
        target.scroll_into_view_if_needed(timeout=900)
    except Exception:
        pass
    try:
        target.click(timeout=900)
    except Exception:
        pass
    target.fill(value, timeout=1500)

    for icon in [
        target.locator('xpath=following::i[contains(@class,"icon_send")][1]').first,
        target.locator('xpath=ancestor::*[self::div or self::td or self::tr][1]//i[contains(@class,"icon_send")]').first,
        _pick_send_icon(page),
    ]:
        if icon is None:
            continue
        if _first_visible(icon, 800):
            return icon
    return None


def fill_suggest_price_apply_all(page, value: str = "7", progress=None):
    value = (value or "").strip() or "7"

    if progress:
        progress("填写建议售价…")

    icon = _fill_value_and_pick_icon(page, value)
    if icon is None:
        raise RuntimeError("未找到建议售价输入框")

    if progress:
        progress("应用建议售价到全部…")

    try:
        icon.scroll_into_view_if_needed(timeout=900)
    except Exception:
        pass
    try:
        icon.hover(timeout=1000)
    except Exception:
        pass
    try:
        icon.click(timeout=1200)
    except Exception:
        try:
            icon.click(timeout=1200, force=True)
        except Exception:
            pass

    menu_clicked = False
    for _ in range(8):
        try:
            _click_first(
                [
                    page.locator('li.ant-dropdown-menu-item[data-menu-id="all"]:visible').first,
                    page.locator('li.ant-dropdown-menu-item[title="应用到全部"]:visible').first,
                    page.locator('li.ant-dropdown-menu-item:has-text("应用到全部"):visible').first,
                    page.locator('.ant-dropdown:visible li[data-menu-id="all"]').first,
                    page.get_by_role("menuitem", name="应用到全部").first,
                ],
                timeout_ms=700,
            )
            menu_clicked = True
            break
        except Exception:
            try:
                page.wait_for_timeout(120)
            except Exception:
                time.sleep(0.12)
            try:
                icon.hover(timeout=700)
            except Exception:
                pass
            try:
                icon.click(timeout=700)
            except Exception:
                try:
                    icon.click(timeout=700, force=True)
                except Exception:
                    pass
    if not menu_clicked:
        raise RuntimeError("未找到“应用到全部”菜单项")
