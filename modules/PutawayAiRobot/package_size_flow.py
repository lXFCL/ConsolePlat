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


def _wait_size_inputs(page, timeout_ms: int = 1200):
    deadline = time.time() + max(0.3, timeout_ms / 1000.0)
    while time.time() < deadline:
        for root in [page, _pick_visible_dialog(page, ["批量", "长(cm)", "宽(cm)", "高(cm)"])]:
            if root is None:
                continue
            try:
                loc = root.locator('input[name="packageLength"], input[placeholder="长(cm)"]').first
                loc.wait_for(state="visible", timeout=120)
                return root
            except Exception:
                continue
        try:
            page.wait_for_timeout(70)
        except Exception:
            time.sleep(0.07)
    return None


def _fill_input(locators, value: str):
    inp = None
    for loc in locators:
        try:
            loc.wait_for(state="visible", timeout=450)
            inp = loc
            break
        except Exception:
            continue
    if inp is None:
        return False
    try:
        inp.scroll_into_view_if_needed(timeout=500)
    except Exception:
        pass
    try:
        inp.click(timeout=500)
    except Exception:
        pass
    inp.fill(value, timeout=900)
    return True


def fill_package_size_batch(page, length: str = "30", width: str = "25", height: str = "1", progress=None):
    length = (length or "").strip() or "30"
    width = (width or "").strip() or "25"
    height = (height or "").strip() or "1"

    if progress:
        progress("打开尺寸批量填写…")

    opened = False
    fixed_candidates = [
        page.locator('span[data-v-65e1d2fb][class="link"]:has-text("(批量)")').first,
        page.locator('span.link:not(.flex-y-center):not(.inline-flex):has-text("(批量)")').first,
        page.locator('span.link:has-text("批量")').first,
        page.locator('a:has-text("批量"), button:has-text("批量")').first,
        page.locator('xpath=//*[contains(normalize-space(.),"尺寸")]/following::span[@class="link" and contains(normalize-space(.),"批量")][1]').first,
        page.locator('xpath=//*[contains(normalize-space(.),"包裹")]/following::span[@class="link" and contains(normalize-space(.),"批量")][1]').first,
        page.locator('xpath=//*[contains(normalize-space(.),"长(cm)") or contains(normalize-space(.),"宽(cm)") or contains(normalize-space(.),"高(cm)")]/preceding::span[contains(normalize-space(.),"批量")][1]').first,
    ]
    for loc in fixed_candidates:
        try:
            _click_first([loc], timeout_ms=900)
            if _wait_size_inputs(page, timeout_ms=1200) is not None:
                opened = True
                break
        except Exception:
            continue

    if not opened:
        all_batch = page.locator('span.link:not(.flex-y-center):not(.inline-flex):has-text("(批量)")')
        cnt = 0
        try:
            cnt = int(all_batch.count())
        except Exception:
            cnt = 0
        for i in range(min(max(cnt, 0), 10)):
            try:
                loc = all_batch.nth(i)
                loc.wait_for(state="visible", timeout=900)
                try:
                    loc.scroll_into_view_if_needed(timeout=800)
                except Exception:
                    pass
                try:
                    loc.click(timeout=900)
                except Exception:
                    loc.click(timeout=900, force=True)
                if _wait_size_inputs(page, timeout_ms=1200) is not None:
                    opened = True
                    break
            except Exception:
                continue

    if not opened:
        raise RuntimeError("未找到尺寸“批量”入口")

    dlg = _wait_size_inputs(page, timeout_ms=800)
    if dlg is None:
        dlg = page

    if progress:
        progress("填写长宽高…")

    ok_length = _fill_input(
        [
            dlg.locator('input[name="packageLength"]').first,
            dlg.locator('input[placeholder="长(cm)"]').first,
            page.locator('input[name="packageLength"]').first,
            page.locator('input[placeholder="长(cm)"]').first,
        ],
        length,
    )
    if not ok_length:
        raise RuntimeError("未找到长(cm)输入框")

    ok_width = _fill_input(
        [
            dlg.locator('input[name="packageWidth"]').first,
            dlg.locator('input[placeholder="宽(cm)"]').first,
            page.locator('input[name="packageWidth"]').first,
            page.locator('input[placeholder="宽(cm)"]').first,
        ],
        width,
    )
    if not ok_width:
        base = dlg.locator('input[name="packageLength"], input[placeholder="长(cm)"]').first
        try:
            row_inputs = base.locator('xpath=ancestor::*[self::div or self::span][1]//following::input').all()
        except Exception:
            row_inputs = []
        if len(row_inputs) >= 1:
            try:
                row_inputs[0].fill(width, timeout=1200)
                ok_width = True
            except Exception:
                ok_width = False
    if not ok_width:
        raise RuntimeError("未找到宽(cm)输入框")

    ok_height = _fill_input(
        [
            dlg.locator('input[name="packageHeight"]').first,
            dlg.locator('input[placeholder="高(cm)"]').first,
            page.locator('input[name="packageHeight"]').first,
            page.locator('input[placeholder="高(cm)"]').first,
        ],
        height,
    )
    if not ok_height:
        raise RuntimeError("未找到高(cm)输入框")

    if progress:
        progress("确认尺寸…")

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
