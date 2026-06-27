import re
import time


ALBUM_URL = "https://www.dianxiaomi.com/album/index.htm"
ALBUM_CLEAN_URL = "https://www.dianxiaomi.com/album/index.htm?cleanup=1"
DEFAULT_CLEANUP_TIMEOUT_S = 240


def _text_re(*parts):
    items = [re.escape((part or "").strip()) for part in parts if (part or "").strip()]
    if not items:
        return re.compile(r".+")
    return re.compile("|".join(items), re.I)


def _first_visible(locators, timeout_ms: int):
    for loc in locators:
        try:
            loc.wait_for(state="visible", timeout=timeout_ms)
            return loc
        except Exception:
            continue
    return None


def _click_locator(loc, timeout_ms: int = 1200):
    try:
        loc.wait_for(state="visible", timeout=timeout_ms)
    except Exception:
        return False
    try:
        loc.scroll_into_view_if_needed(timeout=min(timeout_ms, 800))
    except Exception:
        pass
    for action in [
        lambda: loc.click(timeout=timeout_ms),
        lambda: loc.click(timeout=timeout_ms, force=True),
        lambda: loc.evaluate("el => el.click()"),
    ]:
        try:
            action()
            return True
        except Exception:
            continue
    return False


def _remaining_seconds(deadline: float) -> float:
    return max(0.0, float(deadline) - time.time())


def _ensure_time_left(deadline: float, stage: str):
    if _remaining_seconds(deadline) <= 0:
        raise RuntimeError(f"图片空间清理超时：{stage}")


def _bounded_timeout_s(deadline: float, wanted_s: float, min_s: float = 0.4) -> float:
    left = _remaining_seconds(deadline)
    if left <= 0:
        return 0.0
    return max(min_s, min(float(wanted_s), left))


def _action_locators(scope, *names):
    name_re = _text_re(*names)
    return [
        scope.get_by_role("button", name=name_re).first,
        scope.locator("button", has_text=name_re).first,
        scope.locator("a", has_text=name_re).first,
        scope.locator("span", has_text=name_re).first,
        scope.locator("div[role='button']", has_text=name_re).first,
        scope.locator('input[type="button"][value]').filter(has_text=name_re).first,
        scope.locator('input[type="submit"][value]').filter(has_text=name_re).first,
        scope.get_by_text(name_re).first,
    ]


def _visible_dialog(page, timeout_ms: int = 350):
    return _first_visible(
        [
            page.locator("div.ant-modal-wrap:visible").last,
            page.locator("div.ant-modal:visible").last,
            page.locator('div[role="dialog"]:visible').last,
            page.locator("div[aria-modal='true']:visible").last,
        ],
        timeout_ms,
    )


def _select_all_candidates(page):
    return [
        page.get_by_role("checkbox", name=_text_re("全选")).first,
        page.locator('label:has-text("全选") input[type="checkbox"]').first,
        page.locator("thead input[type='checkbox']").first,
        page.locator("table input[type='checkbox']").first,
        page.locator('input[type="checkbox"][onclick*="selAll"]').first,
        page.locator('input[onclick*="selAll"]').first,
    ]


def _checked_checkbox_count(page):
    try:
        return int(
            page.evaluate(
                """() => Array.from(document.querySelectorAll('input[type="checkbox"]'))
                    .filter(el => el.checked && !el.disabled).length"""
            )
            or 0
        )
    except Exception:
        return 0


def _select_all_by_script(page):
    try:
        return bool(
            page.evaluate(
                """() => {
                    const visibleEnough = el => {
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        return style.visibility !== 'hidden' && style.display !== 'none';
                    };
                    for (const name of ['selAll', 'selectAll', 'checkAll']) {
                        const fn = window[name];
                        if (typeof fn === 'function') {
                            try {
                                fn(true);
                            } catch (e) {
                                try { fn(); } catch (_) {}
                            }
                        }
                    }
                    const candidates = Array.from(document.querySelectorAll(
                        'input[onclick*="selAll"], thead input[type="checkbox"], table input[type="checkbox"], input[type="checkbox"]'
                    )).filter(el => !el.disabled && visibleEnough(el));
                    const target = candidates.find(el => /selAll/i.test(el.getAttribute('onclick') || '')) || candidates[0];
                    if (!target) return false;
                    if (!target.checked) {
                        try {
                            target.click();
                        } catch (e) {
                            target.checked = true;
                        }
                    }
                    target.dispatchEvent(new Event('change', { bubbles: true }));
                    target.dispatchEvent(new Event('click', { bubbles: true }));
                    return true;
                }"""
            )
        )
    except Exception:
        return False


def _page_size_select_candidates(page):
    return [
        page.locator('select[name="pageselct"]').first,
        page.locator('select.form-component[name="pageselct"]').first,
        page.locator('select[name*="page"]').first,
        page.locator('select[id*="page"]').first,
        page.locator("select").first,
    ]


def _delete_action_candidates(page):
    return [
        page.locator('button.btn-orange[onclick*="batchDelPic"]').first,
        page.locator('[onclick*="batchDelPic"]').first,
        page.locator('input[type="button"][value*="批量删除"]').first,
        page.locator('input[type="button"][value*="删除"]').first,
        page.locator('input[type="submit"][value*="删除"]').first,
    ] + _action_locators(page, "批量删除", "删除图片", "删除", "清空")


def _trigger_delete_by_script(page):
    try:
        return bool(
            page.evaluate(
                """() => {
                    const call = name => {
                        const fn = window[name];
                        if (typeof fn === 'function') {
                            fn();
                            return true;
                        }
                        return false;
                    };
                    if (call('batchDelPic') || call('batchDeletePic') || call('batchDelete')) return true;
                    const nodes = Array.from(document.querySelectorAll('button, a, input[type="button"], input[type="submit"], [role="button"]'));
                    const btn = nodes.find(el => {
                        const txt = ((el.innerText || el.textContent || el.value || '') + '').trim();
                        const onclick = el.getAttribute('onclick') || '';
                        return /batchDelPic/i.test(onclick) || /批量删除|删除图片|删除|清空/.test(txt);
                    });
                    if (!btn) return false;
                    btn.click();
                    return true;
                }"""
            )
        )
    except Exception:
        return False


def _confirm_action_candidates(page):
    dialog = _visible_dialog(page, timeout_ms=250)
    scopes = [dialog, page] if dialog is not None else [page]
    locators = []
    for scope in scopes:
        locators.extend(
            [
                scope.locator('div:has-text("图片删除后不可恢复"):visible').last.locator('button:has-text("确定"), a:has-text("确定"), input[value*="确定"]').last,
                scope.locator('div:has-text("你确定要删除吗"):visible').last.locator('button:has-text("确定"), a:has-text("确定"), input[value*="确定"]').last,
                scope.locator('button.button.btn-determine:visible', has_text=re.compile(r"确\s*定", re.I)).last,
                scope.locator('button.btn-determine:visible', has_text=re.compile(r"确\s*定", re.I)).last,
                scope.locator('button.button.btn-determine:visible').last,
                scope.locator('button.btn-determine:visible').last,
                scope.locator('input[type="button"][value*="确定"]').first,
                scope.locator('input[type="button"][value*="确认"]').first,
                scope.locator('input[type="submit"][value*="确定"]').first,
                scope.locator('input[type="submit"][value*="确认"]').first,
                scope.locator("button.button.btn-determine", has_text=re.compile(r"确\s*定", re.I)).last,
                scope.locator("div.ant-modal-confirm-btns button.ant-btn-primary").first,
                scope.locator("div.ant-modal-confirm-btns button", has_text=re.compile(r"确\s*定", re.I)).first,
                scope.locator("button.ant-btn-primary", has_text=re.compile(r"确\s*定|确认|删除", re.I)).first,
                scope.locator("button", has_text=re.compile(r"确\s*定|确认删除|确认|删除", re.I)).first,
                scope.locator("button span", has_text=re.compile(r"确\s*定|确认|删除", re.I)).locator("xpath=ancestor::button[1]").first,
                scope.locator(
                    "xpath=.//button[contains(normalize-space(@class),'btn-determine') and contains(normalize-space(.), '确定')]"
                ).first,
                scope.locator(
                    "xpath=.//div[contains(@class,'ant-modal-confirm-btns')]//button[contains(@class,'ant-btn-primary') or .//span[contains(normalize-space(.), '确定')]]"
                ).first,
            ]
        )
        locators.extend(_action_locators(scope, "确定", "确认", "删除", "是"))
    return locators


def _click_visible_btn_determine_by_script(page):
    try:
        return bool(
            page.evaluate(
                """() => {
                    const visible = el => {
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
                    };
                    const buttons = Array.from(document.querySelectorAll('button.button.btn-determine, button.btn-determine'))
                        .filter(el => !el.disabled && visible(el));
                    const target = buttons.reverse().find(el => /确定/.test((el.innerText || el.textContent || '').trim()));
                    if (!target) return false;
                    target.click();
                    return true;
                }"""
            )
        )
    except Exception:
        return False


def _click_delete_warning_confirm_by_script(page):
    try:
        return bool(
            page.evaluate(
                """() => {
                    const visible = el => {
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
                    };
                    const warningRe = /图片删除后不可恢复|你确定要删除吗|确定要删除吗/;
                    const confirmRe = /确定|确认/;
                    const dialogs = Array.from(document.querySelectorAll(
                        '.modal, .dialog, .popup, .layui-layer, .ui-dialog, .ant-modal, .ant-modal-wrap, [role="dialog"], [aria-modal="true"], body > div'
                    )).filter(el => visible(el) && warningRe.test((el.innerText || el.textContent || '').trim()));
                    for (const dialog of dialogs.reverse()) {
                        const controls = Array.from(dialog.querySelectorAll('button, a, input[type="button"], input[type="submit"], [role="button"]'))
                            .filter(el => !el.disabled && visible(el));
                        const target = controls.find(el => confirmRe.test(((el.innerText || el.textContent || el.value || '') + '').trim()));
                        if (target) {
                            target.click();
                            return true;
                        }
                    }
                    return false;
                }"""
            )
        )
    except Exception:
        return False


def _confirm_with_enter(page):
    for key in ["Enter", "NumpadEnter"]:
        try:
            page.keyboard.press(key)
            return True
        except Exception:
            continue
    return False


def _wait_after_confirm_attempt(page, deadline: float, timeout_s: float, min_ready_wait_s: float = 1.6):
    return _wait_post_delete_state(
        page,
        timeout_s=_bounded_timeout_s(deadline, timeout_s),
        min_ready_wait_s=min_ready_wait_s,
    )


def _click_confirm_candidates(page, rounds: int = 4):
    for _ in range(max(1, int(rounds))):
        for loc in _confirm_action_candidates(page):
            try:
                if _click_locator(loc, timeout_ms=900):
                    return True
            except Exception:
                continue
        if _click_visible_btn_determine_by_script(page):
            return True
        if _click_delete_warning_confirm_by_script(page):
            return True
        try:
            page.wait_for_timeout(180)
        except Exception:
            time.sleep(0.18)
    return False


def _confirm_delete_dialog(page, deadline: float, progress=None):
    clicked_ok = _click_confirm_candidates(page, rounds=4)
    if clicked_ok:
        return _wait_after_confirm_attempt(page, deadline, 10.0, min_ready_wait_s=1.8)

    if progress:
        progress("确认按钮未识别，尝试按 Enter 确认当前弹窗…")
    if _confirm_with_enter(page):
        state = _wait_after_confirm_attempt(page, deadline, 5.0, min_ready_wait_s=1.6)
        if state:
            return state

    if progress:
        progress("未检测到确认按钮，检查删除是否已被浏览器弹窗自动受理…")
    return _wait_after_confirm_attempt(page, deadline, 5.0, min_ready_wait_s=1.6)


def _pick_any_page(browser):
    for ctx in browser.contexts:
        if ctx.pages:
            return ctx.pages[0], ctx
    if browser.contexts:
        ctx = browser.contexts[0]
        return ctx.new_page(), ctx
    raise RuntimeError("CDP已连接，但未发现可用上下文")


def _pick_album_page(browser):
    for ctx in browser.contexts:
        for pg in ctx.pages:
            try:
                u = (pg.url or "").lower()
            except Exception:
                u = ""
            if "/album/index.htm" in u:
                return pg, ctx
    return None, None


def _close_page_quietly(page):
    if page is None:
        return
    try:
        if page.is_closed():
            return
    except Exception:
        pass
    try:
        page.close()
    except Exception:
        pass


def _close_album_pages(browser):
    for ctx in browser.contexts:
        for pg in list(ctx.pages):
            try:
                u = (pg.url or "").lower()
            except Exception:
                u = ""
            if "/album/index.htm" not in u:
                continue
            _close_page_quietly(pg)


def _wait_album_pages_closed(browser, timeout_s: float = 3.0):
    end = time.time() + max(0.5, float(timeout_s))
    while time.time() < end:
        found = False
        for ctx in browser.contexts:
            for pg in list(ctx.pages):
                try:
                    if pg.is_closed():
                        continue
                except Exception:
                    pass
                try:
                    u = (pg.url or "").lower()
                except Exception:
                    u = ""
                if "/album/index.htm" in u:
                    found = True
                    break
            if found:
                break
        if not found:
            return True
        time.sleep(0.12)
    return False


def _is_no_data(page, timeout_ms: int = 250):
    for loc in [
        page.locator('div.m-top50.f-center:has-text("无符合条件的数据！")').first,
        page.get_by_text("无符合条件的数据！").first,
    ]:
        try:
            loc.wait_for(state="visible", timeout=timeout_ms)
            return True
        except Exception:
            continue
    return False


def _wait_cleanup_settled(page, timeout_s: float = 10.0):
    deadline = time.time() + max(1.0, float(timeout_s))
    stable_empty = 0
    while time.time() < deadline:
        if _is_no_data(page, timeout_ms=180):
            stable_empty += 1
            if stable_empty >= 2:
                return True
        else:
            stable_empty = 0
        try:
            page.wait_for_timeout(260)
        except Exception:
            time.sleep(0.26)
    return _is_no_data(page, timeout_ms=220)


def _refresh_album_page(page):
    try:
        page.evaluate(f"window.location.href={ALBUM_URL!r}")
        return
    except Exception:
        pass
    try:
        page.goto(ALBUM_URL, wait_until="commit", timeout=2500)
        return
    except Exception:
        pass
    try:
        page.wait_for_timeout(500)
    except Exception:
        time.sleep(0.5)


def _has_album_controls(page, timeout_ms: int = 900):
    if _first_visible(
        _select_all_candidates(page) + _delete_action_candidates(page),
        timeout_ms,
    ) is not None:
        return True
    try:
        return bool(
            page.evaluate(
                """() => {
                    const text = (document.body && document.body.innerText || '').trim();
                    if (!text) return false;
                    if (/全选/.test(text) && /删除/.test(text)) return true;
                    const controls = Array.from(document.querySelectorAll('button, a, input[type="button"], input[type="submit"]'));
                    const hasDelete = controls.some(el => /删除|批量删除/.test(((el.innerText || el.textContent || el.value || '') + '').trim()));
                    const hasCheckbox = document.querySelectorAll('input[type="checkbox"]').length > 0;
                    return hasDelete && hasCheckbox;
                }"""
            )
        )
    except Exception:
        return False


def _has_album_rows(page, timeout_ms: int = 300):
    for loc in [
        page.locator("table tbody tr").first,
        page.locator(".table tbody tr").first,
        page.locator("tr:has(input[type='checkbox'])").first,
        page.locator("li:has(input[type='checkbox'])").first,
    ]:
        try:
            loc.wait_for(state="attached", timeout=timeout_ms)
            return True
        except Exception:
            continue
    try:
        return bool(
            page.evaluate(
                """() => {
                    const text = (document.body && document.body.innerText || '').trim();
                    if (/第\\s*1\\s*-\\s*\\d+\\s*条/.test(text) || /共\\s*\\d+\\s*条/.test(text)) return true;
                    if (/选用/.test(text) && /复制图片网址/.test(text)) return true;
                    const imgs = Array.from(document.querySelectorAll('img')).filter(img => {
                        const rect = img.getBoundingClientRect();
                        return rect.width > 40 && rect.height > 40;
                    });
                    return imgs.length > 0 && document.querySelectorAll('input[type="checkbox"]').length > 0;
                }"""
            )
        )
    except Exception:
        return False


def _is_album_ready(page, timeout_ms: int = 900):
    if _is_no_data(page, timeout_ms=timeout_ms):
        return True
    return _has_album_controls(page, timeout_ms=timeout_ms) or _has_album_rows(page, timeout_ms=timeout_ms)


def _wait_album_ready(page, timeout_s: float = 6.0):
    end = time.time() + max(1.0, float(timeout_s))
    while time.time() < end:
        if _is_album_ready(page, timeout_ms=220):
            return True
        try:
            page.wait_for_timeout(220)
        except Exception:
            time.sleep(0.22)
    return _is_album_ready(page, timeout_ms=450)


def _wait_post_delete_state(page, timeout_s: float = 12.0, min_ready_wait_s: float = 0.8):
    deadline = time.time() + max(1.0, float(timeout_s))
    ready_after = time.time() + max(0.0, float(min_ready_wait_s))
    stable_empty = 0
    stable_ready = 0
    while time.time() < deadline:
        if _is_no_data(page, timeout_ms=180):
            stable_empty += 1
            stable_ready = 0
            if stable_empty >= 2:
                return "empty"
        elif time.time() >= ready_after and _has_album_controls(page, timeout_ms=180):
            stable_ready += 1
            stable_empty = 0
            if stable_ready >= 2:
                return "ready"
        else:
            stable_empty = 0
            stable_ready = 0
        try:
            page.wait_for_timeout(260)
        except Exception:
            time.sleep(0.26)
    if _is_no_data(page, timeout_ms=220):
        return "empty"
    if _has_album_controls(page, timeout_ms=220):
        return "ready"
    return ""


def _album_open_url(base_url: str, suffix: str):
    base = (base_url or "").strip() or ALBUM_URL
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}_ts={int(time.time() * 1000)}_{suffix}"


def _open_album_window(browser):
    seed_page, _ = _pick_any_page(browser)
    marker = f"album_window_{int(time.time() * 1000)}"
    target_url = _album_open_url(ALBUM_CLEAN_URL, marker)
    sess = seed_page.context.new_cdp_session(seed_page)
    created = sess.send("Target.createTarget", {"url": target_url, "newWindow": True, "background": False})
    want_tid = ((created or {}).get("targetId") or "").strip()
    end = time.time() + 6.0
    while time.time() < end:
        for ctx in browser.contexts:
            for pg in list(ctx.pages):
                try:
                    if pg.is_closed():
                        continue
                except Exception:
                    pass
                if want_tid:
                    try:
                        info = pg.context.new_cdp_session(pg).send("Target.getTargetInfo")
                        tid = (((info or {}).get("targetInfo") or {}).get("targetId") or "").strip()
                        if tid != want_tid:
                            continue
                    except Exception:
                        continue
                else:
                    try:
                        u = (pg.url or "").strip()
                    except Exception:
                        u = ""
                    if marker not in u:
                        continue
                try:
                    pg.bring_to_front()
                except Exception:
                    pass
                try:
                    pg.wait_for_timeout(250)
                except Exception:
                    pass
                return pg
        time.sleep(0.15)
    raise RuntimeError("图片空间独立窗口打开失败")


def _open_album_page(page, retries: int = 4):
    for i in range(max(1, int(retries))):
        try:
            page.bring_to_front()
        except Exception:
            pass
        url = _album_open_url(ALBUM_CLEAN_URL if "cleanup=1" in ALBUM_CLEAN_URL else ALBUM_URL, str(i))
        try:
            page.evaluate(f"window.location.href={url!r}")
        except Exception:
            try:
                page.goto(url, wait_until="commit", timeout=2500)
            except Exception:
                pass
        if _wait_album_ready(page, timeout_s=8.0):
            try:
                page.evaluate("window.stop && window.stop()")
            except Exception:
                pass
            return True
        for spin in [
            page.locator(".ant-spin-spinning:visible").first,
            page.locator(".loading:visible").first,
            page.locator(".spinner:visible").first,
        ]:
            try:
                spin.wait_for(state="visible", timeout=180)
                try:
                    page.evaluate("window.stop && window.stop()")
                except Exception:
                    pass
                break
            except Exception:
                continue
        try:
            page.evaluate("window.stop && window.stop()")
            page.evaluate(f"window.location.href={url!r}")
        except Exception:
            pass
        if _wait_album_ready(page, timeout_s=4.0):
            try:
                page.evaluate("window.stop && window.stop()")
            except Exception:
                pass
            return True
    return False


def _refresh_then_open_album_cleanup(page):
    try:
        u = (page.url or "").lower()
    except Exception:
        u = ""
    if "/album/index.htm" in u and _wait_album_ready(page, timeout_s=3.0):
        try:
            page.evaluate("window.stop && window.stop()")
        except Exception:
            pass
        return True
    return _open_album_page(page, retries=3)


def _reuse_or_open_album_window(
    browser,
    current_page=None,
    progress=None,
    progress_text: str = "刷新当前图片空间页面…",
    attempts: int = 3,
    force_new: bool = False,
):
    page = current_page
    try:
        if page is not None and page.is_closed():
            page = None
    except Exception:
        page = None
    if force_new and page is not None:
        _close_page_quietly(page)
        page = None
    if page is None and not force_new:
        page, _ = _pick_album_page(browser)
    if page is not None:
        for idx in range(max(1, int(attempts))):
            if progress:
                progress(progress_text if idx == 0 else "重新刷新当前图片空间页面…")
            try:
                page.on("dialog", lambda d: d.accept())
            except Exception:
                pass
            if _refresh_then_open_album_cleanup(page):
                return page
        _close_page_quietly(page)
        page = None
    if progress:
        progress("当前图片空间页面不可用，打开新的独立图片空间窗口…")
    for idx in range(max(1, int(attempts))):
        if progress and idx > 0:
            progress("重新打开独立图片空间窗口…")
        new_page = _open_album_window(browser)
        try:
            new_page.on("dialog", lambda d: d.accept())
        except Exception:
            pass
        if _refresh_then_open_album_cleanup(new_page):
            return new_page
        _close_page_quietly(new_page)
    raise RuntimeError("图片空间页面打开失败（页面持续转圈或超时），请检查网络和账号状态")


def _restore_album_page(page):
    for i in range(3):
        url = _album_open_url(ALBUM_URL, f"restore_{i}")
        try:
            page.evaluate(f"window.location.href={url!r}")
        except Exception:
            try:
                page.goto(url, wait_until="commit", timeout=2500)
            except Exception:
                pass
        if _wait_album_ready(page, timeout_s=5.0):
            return True
    return False


def clear_album_space(
    cdp_base_url: str,
    progress=None,
    max_rounds: int = 40,
    max_seconds: int = DEFAULT_CLEANUP_TIMEOUT_S,
    force_new_page: bool = True,
):
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise RuntimeError("缺少依赖 playwright，请先安装：pip install playwright 并执行 python -m playwright install chromium") from e

    cdp_base_url = (cdp_base_url or "").strip().rstrip("/")
    if not cdp_base_url:
        raise RuntimeError("CDP地址为空")

    deadline = time.time() + max(30.0, float(max_seconds or DEFAULT_CLEANUP_TIMEOUT_S))

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(cdp_base_url)
        page = None
        keep_page_open = False
        try:
            if progress:
                progress("准备图片空间窗口…")
            _ensure_time_left(deadline, "准备图片空间窗口")
            if force_new_page:
                if progress:
                    progress("关闭旧图片空间窗口，重新打开清理页面…")
                _close_album_pages(browser)
                _wait_album_pages_closed(browser, timeout_s=3.0)
            page = _reuse_or_open_album_window(
                browser,
                progress=progress,
                progress_text="打开新的图片空间清理页面…",
                attempts=4,
                force_new=force_new_page,
            )
            keep_page_open = False

            for i in range(max(1, int(max_rounds))):
                _ensure_time_left(deadline, f"第{i+1}轮开始前")
                if progress:
                    progress(f"清理图片空间（第{i+1}轮）…")
                if _is_no_data(page, timeout_ms=450):
                    if _wait_cleanup_settled(page, timeout_s=_bounded_timeout_s(deadline, 1.6)):
                        if progress:
                            progress("清理完成，关闭图片空间页面…")
                        return True
                try:
                    page.wait_for_timeout(220)
                except Exception:
                    time.sleep(0.22)
                _ensure_time_left(deadline, f"第{i+1}轮检查空数据")
                if _is_no_data(page, timeout_ms=220) and _wait_cleanup_settled(page, timeout_s=_bounded_timeout_s(deadline, 1.6)):
                    if progress:
                        progress("清理完成，关闭图片空间页面…")
                    return True

                if i == 0:
                    for loc in _page_size_select_candidates(page):
                        try:
                            loc.wait_for(state="visible", timeout=500)
                            current_value = ""
                            try:
                                current_value = (loc.input_value(timeout=300) or "").strip()
                            except Exception:
                                pass
                            if current_value != "300":
                                loc.select_option("300", timeout=1200)
                            break
                        except Exception:
                            continue

                try:
                    page.bring_to_front()
                except Exception:
                    pass
                try:
                    page.wait_for_timeout(220)
                except Exception:
                    time.sleep(0.22)

                checked = _select_all_by_script(page)
                if not checked or _checked_checkbox_count(page) <= 0:
                    checked = False
                    for loc in _select_all_candidates(page):
                        try:
                            loc.wait_for(state="visible", timeout=1200)
                            try:
                                loc.check(timeout=900, force=True)
                            except Exception:
                                loc.click(timeout=900, force=True)
                            checked = True
                            break
                        except Exception:
                            continue
                if (not checked) or _checked_checkbox_count(page) <= 0:
                    if progress:
                        progress("常规全选未确认，尝试脚本全选…")
                    checked = _select_all_by_script(page)
                    try:
                        page.wait_for_timeout(180)
                    except Exception:
                        time.sleep(0.18)
                    checked = checked and _checked_checkbox_count(page) > 0
                if not checked:
                    _ensure_time_left(deadline, f"第{i+1}轮全选失败后重试")
                    page = _reuse_or_open_album_window(
                        browser,
                        current_page=page,
                        progress=progress,
                        progress_text="全选未就绪，重开图片空间清理页面重试…",
                        attempts=3,
                        force_new=True,
                    )
                    continue

                clicked_del = _trigger_delete_by_script(page)
                for loc in _delete_action_candidates(page):
                    if clicked_del:
                        break
                    try:
                        if _click_locator(loc, timeout_ms=1200):
                            clicked_del = True
                            break
                    except Exception:
                        continue
                if not clicked_del:
                    if progress:
                        progress("常规删除按钮未触发，尝试脚本触发删除…")
                    clicked_del = _trigger_delete_by_script(page)
                if not clicked_del:
                    _ensure_time_left(deadline, f"第{i+1}轮删除按钮失败后重试")
                    page = _reuse_or_open_album_window(
                        browser,
                        current_page=page,
                        progress=progress,
                        progress_text="删除按钮未就绪，重开图片空间清理页面重试…",
                        attempts=3,
                        force_new=True,
                    )
                    continue

                try:
                    page.wait_for_timeout(260)
                except Exception:
                    time.sleep(0.26)

                post_delete_state = _confirm_delete_dialog(page, deadline, progress=progress)
                if not post_delete_state:
                    _ensure_time_left(deadline, f"第{i+1}轮确认按钮失败后重试")
                    page = _reuse_or_open_album_window(
                        browser,
                        current_page=page,
                        progress=progress,
                        progress_text="确认按钮未就绪，重开图片空间清理页面重试…",
                        attempts=3,
                        force_new=True,
                    )
                    continue

                if post_delete_state == "empty":
                    if progress:
                        progress("清理完成，关闭图片空间页面…")
                    return True
                if post_delete_state != "ready":
                    page = _reuse_or_open_album_window(
                        browser,
                        current_page=page,
                        progress=progress,
                        progress_text="页面状态未稳定，重开图片空间清理页面继续…",
                        attempts=3,
                        force_new=True,
                    )
                    continue
                if progress:
                    progress("本轮删除完成，继续在当前图片空间页面全选删除…")
                _ensure_time_left(deadline, f"第{i+1}轮删除后等待页面稳定")
                if not _wait_post_delete_state(
                    page,
                    timeout_s=_bounded_timeout_s(deadline, 4.0),
                    min_ready_wait_s=0.8,
                ):
                    try:
                        page.wait_for_timeout(500)
                    except Exception:
                        time.sleep(0.5)
            raise RuntimeError("图片空间清理未完成：达到最大清理轮次后仍有图片")
        finally:
            try:
                if page is not None and not keep_page_open:
                    page.close()
            except Exception:
                pass
            if hasattr(browser, "disconnect"):
                browser.disconnect()
            else:
                browser.close()
