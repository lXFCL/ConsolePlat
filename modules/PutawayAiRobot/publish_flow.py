import time


def _first_visible(locator, timeout_ms: int):
    try:
        locator.wait_for(state="visible", timeout=timeout_ms)
        return locator
    except Exception:
        return None


def _click_with_retry(locators, timeout_ms: int):
    deadline = time.time() + max(0.8, timeout_ms / 1000.0)
    last = None
    while time.time() < deadline:
        for loc in locators:
            try:
                loc.wait_for(state="visible", timeout=450)
                try:
                    loc.scroll_into_view_if_needed(timeout=600)
                except Exception:
                    pass
                try:
                    loc.click(timeout=700)
                    return True
                except Exception:
                    try:
                        loc.click(timeout=700, force=True)
                        return True
                    except Exception:
                        try:
                            loc.evaluate("el => el.click()")
                            return True
                        except Exception as e:
                            last = e
            except Exception as e:
                last = e
                continue
        try:
            loc = locators[0]
            page = loc.page
            page.wait_for_timeout(120)
        except Exception:
            time.sleep(0.12)
    if last is not None:
        raise last
    return False


def publish_now(page, progress=None):
    def _wait_publish_accepted(timeout_s: float = 12.0):
        deadline = time.time() + max(2.0, float(timeout_s))
        ok_words = ["发布成功", "发布中", "已提交", "提交成功", "加入发布", "提交发布"]
        while time.time() < deadline:
            for loc in [
                page.locator(".ant-message:visible"),
                page.locator(".ant-message-notice:visible"),
                page.locator(".ant-notification-notice:visible"),
                page.locator(".ant-modal:visible"),
                page.locator(".el-message:visible"),
            ]:
                try:
                    txt = (loc.inner_text(timeout=300) or "").strip()
                except Exception:
                    txt = ""
                if txt and any(w in txt for w in ok_words):
                    return True
            for loc in [
                page.locator('button:has-text("发布中")').first,
                page.locator('button.ant-btn[disabled]:has-text("发布")').first,
            ]:
                if _first_visible(loc, 250):
                    return True
            try:
                page.wait_for_timeout(180)
            except Exception:
                time.sleep(0.18)
        return False

    if progress:
        progress("点击发布…")

    publish_btn = None
    for loc in [
        page.locator('button.ant-btn.btn-green:has-text("发布")').first,
        page.locator('button.ant-btn-default.btn-green:has-text("发布")').first,
        page.get_by_role("button", name="发布").first,
        page.locator('button:has-text("发布")').first,
    ]:
        if _first_visible(loc, 1200):
            publish_btn = loc
            break
    if publish_btn is None:
        raise RuntimeError("未找到“发布”按钮")

    _click_with_retry([publish_btn], timeout_ms=5200)

    if progress:
        progress("选择立即发布…")

    picked = False
    for _ in range(10):
        try:
            publish_btn.click(timeout=700)
        except Exception:
            try:
                publish_btn.click(timeout=700, force=True)
            except Exception:
                pass
        try:
            page.locator("ul.ant-dropdown-menu:visible, div.ant-dropdown:visible").first.wait_for(state="visible", timeout=450)
        except Exception:
            pass
        try:
            _click_with_retry(
                [
                    page.locator('li.ant-dropdown-menu-item[data-menu-id="2"]:visible').first,
                    page.locator('li.ant-dropdown-menu-item[title="立即发布"]:visible').first,
                    page.locator('li.ant-dropdown-menu-item:has-text("立即发布"):visible').first,
                    page.locator('ul.ant-dropdown-menu:visible li:has-text("立即发布")').first,
                    page.get_by_role("menuitem", name="立即发布").first,
                    page.get_by_text("立即发布").first,
                ],
                timeout_ms=1200,
            )
            picked = True
            break
        except Exception:
            try:
                page.wait_for_timeout(120)
            except Exception:
                time.sleep(0.12)
            continue
    if not picked:
        raise RuntimeError("未找到“立即发布”菜单项")

    if progress:
        progress("等待发布受理…")
    if not _wait_publish_accepted(timeout_s=12.0):
        raise RuntimeError("未检测到“立即发布”已受理，请检查是否真正点击成功")
