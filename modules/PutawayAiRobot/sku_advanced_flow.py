import re
import time


def split_sku_prefix_suffix(sku: str):
    s = (sku or "").strip()
    if not s:
        return "", ""

    for sep in ["-", "_", "—", "–", " ", "/", "\\", "."]:
        if sep in s:
            left, right = s.split(sep, 1)
            left = left.strip()
            right = right.strip()
            if left and right:
                return left, right

    m = re.match(r"^([A-Za-z]+)([0-9].*)$", s)
    if m:
        return m.group(1), m.group(2)

    m = re.match(r"^(.*?)(\d+)$", s)
    if m and m.group(1) and m.group(2):
        return m.group(1), m.group(2)

    return s, ""


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


def _click_generate_button(page, timeout_ms: int = 2500):
    last = None
    button_locators = [
        page.locator('button.css-1oz1bg8.ant-btn.ant-btn-primary:has(span:has-text("生成"))').first,
        page.locator('button.ant-btn.ant-btn-primary:has(span:has-text("生成"))').first,
        page.get_by_role("button", name="生成").first,
        page.locator('button:has-text("生成")').first,
    ]
    for btn in button_locators:
        try:
            btn.wait_for(state="visible", timeout=timeout_ms)
            try:
                btn.scroll_into_view_if_needed(timeout=1200)
            except Exception:
                pass
            try:
                btn.click(timeout=1500)
            except Exception:
                btn.click(timeout=1500, force=True)
            return True
        except Exception as e:
            last = e
            continue

    span_locators = [
        page.locator('button.css-1oz1bg8.ant-btn.ant-btn-primary span:has-text("生成")').first,
        page.locator('button.ant-btn.ant-btn-primary span:has-text("生成")').first,
        page.locator('span:has-text("生成")').first,
    ]
    for span in span_locators:
        try:
            span.wait_for(state="visible", timeout=timeout_ms)
            host_btn = span.locator("xpath=ancestor::button[1]").first
            try:
                host_btn.scroll_into_view_if_needed(timeout=1200)
            except Exception:
                pass
            try:
                host_btn.click(timeout=1500)
            except Exception:
                host_btn.click(timeout=1500, force=True)
            return True
        except Exception as e:
            last = e
            continue

    if last is not None:
        raise last
    return False


def fill_sku_advanced_prefix_suffix(page, sku: str, progress=None):
    prefix, suffix = split_sku_prefix_suffix(sku)
    prefix = (prefix or "").strip()
    suffix = (suffix or "").strip()
    if not prefix:
        raise RuntimeError(f"无法从序列号解析前缀：{sku}")

    if progress:
        progress("打开高级SKU设置…")

    _click_first(
        [
            page.locator('span.link:has-text("高级")').first,
            page.get_by_text("高级").first,
            page.locator('xpath=//span[contains(@class,"link") and contains(normalize-space(.),"高级")]').first,
        ],
        timeout_ms=2500,
    )

    try:
        page.wait_for_timeout(180)
    except Exception:
        time.sleep(0.18)

    if progress:
        progress("填写SKU前缀/后缀…")

    prefix_candidates = [
        page.locator('xpath=//input[@type="text" and contains(@class,"ant-input") and contains(@class,"!w-120")]').first,
        page.locator('xpath=//input[@type="text" and contains(@class,"ant-input") and contains(@class,"text-align-center")]').first,
        page.locator('input.ant-input').first,
    ]
    prefix_inp = None
    for loc in prefix_candidates:
        try:
            loc.wait_for(state="visible", timeout=2500)
            prefix_inp = loc
            break
        except Exception:
            continue
    if prefix_inp is None:
        raise RuntimeError("未找到SKU前缀输入框")

    suffix_candidates = [
        page.locator('xpath=//input[@type="text" and contains(@class,"ant-input") and contains(@class,"ant-input-sm") and contains(@class,"!w-100")]').first,
        page.locator('xpath=//input[@type="text" and contains(@class,"ant-input") and contains(@class,"ant-input-sm")]').first,
    ]
    suffix_inp = None
    for loc in suffix_candidates:
        try:
            loc.wait_for(state="visible", timeout=2500)
            suffix_inp = loc
            break
        except Exception:
            continue
    if suffix_inp is None:
        raise RuntimeError("未找到SKU后缀输入框")

    try:
        prefix_inp.scroll_into_view_if_needed(timeout=900)
    except Exception:
        pass
    try:
        prefix_inp.click(timeout=900)
    except Exception:
        pass
    prefix_inp.fill(prefix, timeout=1500)

    if suffix:
        try:
            suffix_inp.scroll_into_view_if_needed(timeout=900)
        except Exception:
            pass
        try:
            suffix_inp.click(timeout=900)
        except Exception:
            pass
        suffix_inp.fill(suffix, timeout=1500)

    if progress:
        progress("生成SKU货号…")

    if not _click_generate_button(page, timeout_ms=2500):
        raise RuntimeError("未找到“生成”按钮")

    try:
        page.wait_for_timeout(220)
    except Exception:
        time.sleep(0.22)
