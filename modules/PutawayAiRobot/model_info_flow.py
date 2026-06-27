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


def _select_dropdown_option(page, option_text: str):
    option_text = (option_text or "").strip()
    if not option_text:
        raise RuntimeError("选项文本为空")

    tokens = [t for t in re.split(r"\s+", option_text) if t]

    def _match_all(txt: str):
        txt = (txt or "").strip()
        return all(t in txt for t in tokens) or option_text in txt

    def _safe_count(locator):
        try:
            return int(locator.count())
        except Exception:
            return -1

    def _click_from_list(list_locator):
        n = _safe_count(list_locator)
        if n <= 0:
            return False
        for i in range(min(n, 80)):
            opt = list_locator.nth(i)
            try:
                txt = opt.inner_text(timeout=600)
            except Exception:
                continue
            if not _match_all(txt):
                continue
            try:
                opt.scroll_into_view_if_needed(timeout=900)
            except Exception:
                pass
            try:
                opt.click(timeout=1200)
                return True
            except Exception:
                try:
                    opt.click(timeout=1200, force=True)
                    return True
                except Exception:
                    continue
        return False

    for list_loc in [
        page.locator(".ant-select-dropdown:visible .ant-select-item-option"),
        page.locator(".ant-select-item-option:visible"),
        page.locator(".ant-dropdown:visible li.ant-dropdown-menu-item"),
        page.locator("ul.ant-dropdown-menu:visible li.ant-dropdown-menu-item"),
        page.locator(".el-select-dropdown:visible .el-select-dropdown__item"),
        page.locator(".el-select-dropdown__item:visible"),
        page.locator("li:visible"),
    ]:
        try:
            if _click_from_list(list_loc):
                return
        except Exception:
            continue
    raise RuntimeError(f"未找到选项：{option_text}")


def select_model_tryon_size(page, size_text: str = "M", progress=None):
    if progress:
        progress("打开模特信息弹窗…")

    clicked = False
    for btn in [
        page.locator('xpath=//*[contains(normalize-space(.),"模特信息")]/following::span[contains(normalize-space(.),"添加模特")][1]').first,
        page.locator('xpath=//*[contains(normalize-space(.),"模特信息")]/following::button[contains(normalize-space(.),"添加模特")][1]').first,
        page.locator('xpath=//*[contains(normalize-space(.),"模特信息")]/following::span[contains(normalize-space(.),"+")][1]').first,
        page.get_by_text(re.compile(r"添加模特\\+?", re.I)).first,
        page.locator('span.link:has-text("添加模特")').first,
        page.locator('xpath=//*[contains(normalize-space(.),"模特信息")]/following::button[contains(normalize-space(.),"选择模特")][1]').first,
        page.locator('xpath=//*[contains(normalize-space(.),"模特信息")]/following::span[contains(normalize-space(.),"选择模特")][1]').first,
        page.get_by_role("button", name=re.compile(r"选择模特", re.I)).first,
        page.get_by_text("选择模特").first,
        page.locator('button:has-text("选择模特"), span:has-text("选择模特")').first,
    ]:
        try:
            btn.wait_for(state="visible", timeout=2500)
            try:
                btn.scroll_into_view_if_needed(timeout=1200)
            except Exception:
                pass
            btn.click(timeout=1800)
            clicked = True
            break
        except Exception:
            continue
    if not clicked:
        raise RuntimeError("未找到“模特信息”右侧“添加模特/选择模特”入口")

    dlg = _pick_visible_dialog(page, ["添加模特信息", "模特信息"])
    if dlg is None:
        raise RuntimeError("未检测到“添加模特信息”弹窗")

    if progress:
        progress("选择试穿尺码…")

    want = (size_text or "").strip() or "M"

    radio = None
    for loc in [
        dlg.locator(f'input.ant-radio-input[value="{want}"]').first,
        dlg.locator(f'input[type="radio"][value="{want}"]').first,
    ]:
        try:
            loc.wait_for(state="attached", timeout=650)
            radio = loc
            break
        except Exception:
            continue

    if radio is not None:
        clicked_radio = False
        for btn in [
            radio.locator('xpath=ancestor::label[contains(@class,"ant-radio-wrapper")][1]').first,
            radio.locator('xpath=ancestor::*[contains(@class,"ant-radio-wrapper")][1]').first,
            radio.locator('xpath=ancestor::*[contains(@class,"ant-radio")][1]').first,
            radio,
        ]:
            try:
                btn.wait_for(state="visible", timeout=1200)
                try:
                    btn.scroll_into_view_if_needed(timeout=900)
                except Exception:
                    pass
                try:
                    btn.click(timeout=1200)
                except Exception:
                    btn.click(timeout=1200, force=True)
                clicked_radio = True
                break
            except Exception:
                continue
        if not clicked_radio:
            raise RuntimeError(f"未能选择试穿尺码：{want}")
        try:
            if radio.is_checked(timeout=800):
                pass
        except Exception:
            pass
    else:
        opened = False
        for field in [
            dlg.locator('xpath=//*[contains(normalize-space(.),"试穿尺码")]/following::*[@role="combobox"][1]').first,
            dlg.locator('xpath=//*[contains(normalize-space(.),"试穿尺码")]/following::input[1]').first,
            dlg.locator('xpath=//*[contains(normalize-space(.),"试穿尺码")]/following::div[contains(@class,"ant-select")][1]').first,
        ]:
            try:
                field.wait_for(state="visible", timeout=1500)
                try:
                    field.scroll_into_view_if_needed(timeout=900)
                except Exception:
                    pass
                field.click(timeout=1200)
                opened = True
                break
            except Exception:
                continue
        if not opened:
            raise RuntimeError("未找到“试穿尺码”选择控件（radio/select）")

        try:
            page.wait_for_timeout(120)
        except Exception:
            time.sleep(0.12)

        candidates = [want]
        if not want.endswith("码"):
            candidates.append(f"{want}码")
        ok = False
        for opt in candidates:
            try:
                _select_dropdown_option(page, opt)
                ok = True
                break
            except Exception:
                continue
        if not ok:
            raise RuntimeError(f"未找到试穿尺码选项：{want}")

    if progress:
        progress("确认模特信息…")

    _click_first(
        [
            dlg.locator('span.link:has-text("选择")').first,
            dlg.locator('div:has(span.link:has-text("选择"))').first,
            dlg.get_by_text("选择", exact=True).first,
            dlg.get_by_text("选择").first,
        ],
        timeout_ms=2500,
    )

    try:
        dlg.wait_for(state="hidden", timeout=3500)
    except Exception:
        pass
