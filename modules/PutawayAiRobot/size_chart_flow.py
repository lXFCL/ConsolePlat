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
        raise RuntimeError("引用模板名称为空")

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

    quick_locators = [
        page.locator(".ant-select-dropdown:visible .ant-select-item-option", has_text=option_text).first,
        page.locator(".ant-select-item-option:visible", has_text=option_text).first,
        page.locator(".el-select-dropdown:visible .el-select-dropdown__item", has_text=option_text).first,
        page.locator(".el-select-dropdown__item:visible", has_text=option_text).first,
        page.get_by_text(option_text, exact=True).first,
        page.get_by_text(option_text).first,
    ]
    for loc in quick_locators:
        try:
            loc.wait_for(state="visible", timeout=700)
            try:
                loc.scroll_into_view_if_needed(timeout=900)
            except Exception:
                pass
            loc.click(timeout=1200)
            return
        except Exception:
            continue

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
    raise RuntimeError(f"未找到引用模板选项：{option_text}")


def _wait_ready_to_confirm(page, dlg, template_name: str, timeout_s: float = 8.0):
    template_name = (template_name or "").strip()
    tokens = [t for t in re.split(r"\s+", template_name) if t]
    deadline = time.time() + max(0.5, float(timeout_s))

    def _safe_count(locator):
        try:
            return int(locator.count())
        except Exception:
            return -1

    def _any_loading():
        for loc in [
            dlg.locator(".ant-spin-spinning:visible"),
            dlg.locator(".ant-btn-loading:visible"),
            dlg.locator(".el-loading-mask:visible"),
        ]:
            try:
                if _safe_count(loc) > 0:
                    return True
            except Exception:
                continue
        return False

    def _template_shown():
        if not tokens:
            return True
        try:
            txt = dlg.inner_text(timeout=800)
        except Exception:
            return False
        return all(t in txt for t in tokens)

    def _template_name_field_ready():
        for loc in [
            dlg.locator('label[title="模板名称"]').first,
            dlg.locator('label:has-text("模板名称")').first,
            dlg.get_by_text("模板名称").first,
        ]:
            try:
                loc.wait_for(state="visible", timeout=220)
                return True
            except Exception:
                continue
        return False

    btn_candidates = [
        dlg.get_by_role("button", name="确定").first,
        dlg.locator('button:has-text("确定")').first,
        dlg.get_by_text("确定").first,
    ]

    while time.time() < deadline:
        btn = None
        for b in btn_candidates:
            try:
                b.wait_for(state="visible", timeout=350)
                btn = b
                break
            except Exception:
                continue

        if btn is not None:
            try:
                disabled = btn.get_attribute("disabled")
                aria_disabled = btn.get_attribute("aria-disabled")
                cls = btn.get_attribute("class") or ""
                is_disabled = disabled is not None or (aria_disabled or "").lower() == "true" or "disabled" in cls
                if (not is_disabled) and _template_name_field_ready():
                    try:
                        page.wait_for_timeout(500)
                    except Exception:
                        time.sleep(0.5)
                    return
                if (not is_disabled) and (not _any_loading()) and _template_shown():
                    try:
                        page.wait_for_timeout(500)
                    except Exception:
                        time.sleep(0.5)
                    return
            except Exception:
                pass

        try:
            page.wait_for_timeout(160)
        except Exception:
            time.sleep(0.16)


def add_size_chart_by_template(page, template_name: str = "T恤 店小秘模板", progress=None):
    if progress:
        progress("打开尺码表弹窗…")

    _click_first(
        [
            page.get_by_role("button", name=re.compile(r"添加尺码表", re.I)).first,
            page.locator('button:has-text("添加尺码表")').first,
            page.get_by_text("添加尺码表").first,
            page.locator('xpath=//*[contains(normalize-space(.),"尺码表")]/following::button[contains(normalize-space(.),"添加尺码表")][1]').first,
            page.locator('xpath=//*[contains(normalize-space(.),"尺码表")]/following::button[contains(normalize-space(.),"添加")][1]').first,
        ],
        timeout_ms=2500,
    )

    dlg = _pick_visible_dialog(page, ["添加尺码表", "尺码表"])
    if dlg is None:
        raise RuntimeError("未检测到“添加尺码表”弹窗")

    if progress:
        progress("点击同步…")

    try:
        _click_first(
            [
                dlg.locator('span.link.ml-15.mr-5:has-text("同步")').first,
                dlg.locator('span.link:has-text("同步")').first,
                dlg.get_by_text("同步", exact=True).first,
                dlg.get_by_text("同步").first,
                dlg.locator('button:has-text("同步"), a:has-text("同步"), span:has-text("同步")').first,
            ],
            timeout_ms=2000,
        )
    except Exception:
        rows = None
        for loc in [
            dlg.locator(".ant-table-tbody tr"),
            dlg.locator("tbody tr"),
            dlg.locator("tr"),
        ]:
            try:
                if int(loc.count()) >= 3:
                    rows = loc
                    break
            except Exception:
                continue
        if rows is None:
            raise RuntimeError("未找到尺码表弹窗中的“同步”按钮")
        row3 = rows.nth(2)
        _click_first(
            [
                row3.get_by_text("同步", exact=True).first,
                row3.get_by_text("同步").first,
                row3.locator('button:has-text("同步"), a:has-text("同步"), span:has-text("同步")').first,
            ],
            timeout_ms=1800,
        )

    if progress:
        progress("选择引用模板…")

    end_wait = time.time() + 2.6
    while time.time() < end_wait:
        ready = False
        for probe in [
            dlg.locator('.ant-form-item:has-text("引用模板") .ant-select-selector').first,
            dlg.locator('.ant-form-item:has-text("引用模板") [role="combobox"]').first,
            dlg.locator('.el-form-item:has-text("引用模板") .el-select').first,
            dlg.locator('xpath=//*[contains(normalize-space(.),"引用模板")]/following::input[1]').first,
        ]:
            if _first_visible(probe, 120):
                ready = True
                break
        if ready:
            break
        try:
            page.wait_for_timeout(120)
        except Exception:
            time.sleep(0.12)

    opened = False
    for loc in [
        dlg.locator('.ant-form-item:has-text("引用模板") .ant-select-selector').first,
        dlg.locator('.ant-form-item:has-text("引用模板") [role="combobox"]').first,
        dlg.locator('.ant-form-item:has-text("引用模板") input').first,
        dlg.locator('.el-form-item:has-text("引用模板") .el-select').first,
        dlg.locator('.el-form-item:has-text("引用模板") input').first,
        dlg.locator('xpath=//*[contains(normalize-space(.),"店小秘模板")]/ancestor::*[contains(@class,"ant-form-item") or contains(@class,"el-form-item")][1]//*[contains(@class,"select") or self::input][1]').first,
        dlg.locator('xpath=//*[contains(normalize-space(.),"引用模板")]/following::input[1]').first,
    ]:
        try:
            loc.wait_for(state="visible", timeout=2200)
            try:
                loc.scroll_into_view_if_needed(timeout=900)
            except Exception:
                pass
            try:
                loc.click(timeout=1200)
            except Exception:
                loc.click(timeout=1200, force=True)
            opened = True
            break
        except Exception:
            continue
    if not opened:
        raise RuntimeError("未找到“引用模板”下拉框")

    try:
        page.wait_for_timeout(120)
    except Exception:
        time.sleep(0.12)

    _select_dropdown_option(page, template_name)

    if progress:
        progress("等待尺码表加载…")

    _wait_ready_to_confirm(page, dlg, template_name, timeout_s=10.0)

    if progress:
        progress("确认尺码表…")

    _click_first(
        [
            dlg.get_by_role("button", name="确定").first,
            dlg.locator('button:has-text("确定")').first,
            dlg.get_by_text("确定").first,
        ],
        timeout_ms=2500,
    )

    try:
        dlg.wait_for(state="hidden", timeout=3500)
    except Exception:
        pass
