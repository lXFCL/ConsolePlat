import re
import time


def _first_visible(locator, timeout_ms: int):
    try:
        locator.wait_for(state="visible", timeout=timeout_ms)
        return locator
    except Exception:
        return None


def _text_re(*parts):
    items = [re.escape((part or "").strip()) for part in parts if (part or "").strip()]
    if not items:
        return re.compile(r".+")
    return re.compile("|".join(items), re.I)


def _find_visible_container(page, locators, timeout_ms: int = 1000):
    for loc in locators:
        if _first_visible(loc, timeout_ms):
            return loc
    return None


def _action_locators(scope, *names, include_menu: bool = False):
    name_re = _text_re(*names)
    locators = [
        scope.get_by_role("button", name=name_re).first,
        scope.locator("button", has_text=name_re).first,
        scope.locator("a", has_text=name_re).first,
        scope.locator("span", has_text=name_re).first,
        scope.locator("div[role='button']", has_text=name_re).first,
        scope.get_by_text(name_re).first,
    ]
    if include_menu:
        locators = [
            scope.get_by_role("menuitem", name=name_re).first,
            scope.locator("[role='menuitem']", has_text=name_re).first,
            scope.locator("li", has_text=name_re).first,
            scope.locator("div.ant-dropdown-menu-item", has_text=name_re).first,
            scope.locator("span", has_text=name_re).first,
            scope.get_by_text(name_re).first,
        ] + locators
    return locators


def _save_action_locators(scope):
    return [
        scope.locator("button.ant-btn-default.btn-orange.m-left10").filter(has_text=re.compile(r"保\s*存", re.I)).first,
        scope.locator("button.css-1oz1bg8.ant-btn.ant-btn-default.btn-orange.m-left10").filter(has_text=re.compile(r"保\s*存", re.I)).first,
        scope.locator("button.ant-btn-default.btn-orange.m-left10 span", has_text=re.compile(r"保\s*存", re.I)).locator("xpath=ancestor::button[1]").first,
        scope.locator("button.btn-orange").filter(has_text=re.compile(r"保\s*存", re.I)).first,
        scope.locator("button.ant-btn-primary").filter(has_text=re.compile(r"保\s*存", re.I)).first,
        scope.locator("button.ant-btn-default").filter(has_text=re.compile(r"保\s*存", re.I)).first,
        scope.locator("button", has_text=re.compile(r"保\s*存|保存描述|保存并关闭", re.I)).first,
        scope.locator("span", has_text=re.compile(r"保\s*存|保存描述|保存并关闭", re.I)).locator("xpath=ancestor::button[1]").first,
        scope.locator("span", has_text=re.compile(r"保\s*存|保存描述|保存并关闭", re.I)).locator("xpath=ancestor::*[@role='button'][1]").first,
        scope.locator("div.footer, div.modal-footer, div.ant-modal-footer, div[class*='footer']", has_text=re.compile(r"保\s*存", re.I))
        .locator("button, [role='button'], a, span")
        .filter(has_text=re.compile(r"保\s*存|保存描述|保存并关闭", re.I))
        .first,
    ] + _action_locators(scope, "保存", "保存描述", "保存并关闭")


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


def _open_description_editor(page):
    ctx = page.context
    before = list(ctx.pages)

    box = None
    for loc in [
        page.locator("#wirelessDescBox").first,
        page.locator("div.wireless-description-box").first,
        page.locator('div:has(button:has-text("编辑描述"))').first,
        page.locator("div", has_text=_text_re("编辑描述")).first,
    ]:
        if _first_visible(loc, 1200):
            box = loc
            break
    if box is None:
        raise RuntimeError("未找到“编辑描述”区域")

    try:
        box.scroll_into_view_if_needed(timeout=900)
    except Exception:
        pass
    try:
        box.hover(timeout=1000)
    except Exception:
        pass

    clicked = False
    for _ in range(8):
        try:
            _click_first(
                _action_locators(box, "编辑描述") + _action_locators(page, "编辑描述"),
                timeout_ms=900,
            )
            clicked = True
            break
        except Exception:
            try:
                box.hover(timeout=700)
            except Exception:
                pass
            try:
                box.click(timeout=700, force=True)
            except Exception:
                pass
            try:
                page.wait_for_timeout(180)
            except Exception:
                time.sleep(0.18)
    if not clicked:
        raise RuntimeError("未找到“编辑描述”按钮")

    for _ in range(12):
        now = list(ctx.pages)
        if len(now) > len(before):
            newest = now[-1]
            try:
                newest.wait_for_load_state("domcontentloaded", timeout=4000)
            except Exception:
                pass
            return newest
        try:
            page.wait_for_timeout(200)
        except Exception:
            time.sleep(0.2)
    try:
        page.wait_for_load_state("domcontentloaded", timeout=3500)
    except Exception:
        pass
    return page


def _open_batch_upload(editor_page):
    _click_first(
        [
            editor_page.locator('span.menu-button.ant-dropdown-trigger').filter(has_text=_text_re("批量操作")).first,
            editor_page.locator(".ant-dropdown-trigger", has_text=_text_re("批量操作")).first,
        ] + _action_locators(editor_page, "批量操作"),
        timeout_ms=2500,
    )
    _click_first(
        _action_locators(editor_page, "批量传图", "批量上传", include_menu=True),
        timeout_ms=2500,
    )


def _upload_local_files(editor_page, file_paths):
    panel = _find_visible_container(
        editor_page,
        [
        editor_page.locator("div.ant-modal-wrap:visible").last,
        editor_page.locator("div.ant-modal:visible").last,
        editor_page.locator('div[role="dialog"]:visible').last,
        ],
        timeout_ms=1000,
    )
    if panel is None:
        panel = editor_page

    choose_btn = None
    choose_candidates = (
        _action_locators(panel, "选择图片", "选择文件", "上传图片")
        + _action_locators(editor_page, "选择图片", "选择文件", "上传图片")
    )
    for loc in choose_candidates:
        if _first_visible(loc, 1200):
            choose_btn = loc
            break
    if choose_btn is None:
        raise RuntimeError("未找到“选择图片”按钮")

    opened = False
    for _ in range(6):
        try:
            choose_btn.scroll_into_view_if_needed(timeout=700)
        except Exception:
            pass
        try:
            with editor_page.expect_file_chooser(timeout=900) as fc:
                choose_btn.click(timeout=900)
            fc.value.set_files(file_paths)
            return
        except Exception:
            try:
                choose_btn.click(timeout=900, force=True)
                opened = True
            except Exception:
                try:
                    choose_btn.evaluate("el => el.click()")
                    opened = True
                except Exception:
                    opened = False
        if opened:
            for menu in _action_locators(editor_page, "本地上传", "本地图片", "上传本地", include_menu=True):
                if _first_visible(menu, 350):
                    break
            else:
                opened = False
        if opened:
            break
        try:
            editor_page.wait_for_timeout(180)
        except Exception:
            time.sleep(0.18)
    if not opened:
        raise RuntimeError("“选择图片”按钮点击后未打开上传菜单")

    picked = False
    uploaded = False
    for loc in _action_locators(editor_page, "本地上传", "本地图片", "上传本地", include_menu=True):
        try:
            loc.wait_for(state="visible", timeout=1200)
            try:
                with editor_page.expect_file_chooser(timeout=1400) as fc:
                    loc.click(timeout=1200)
                chooser = fc.value
                chooser.set_files(file_paths)
                picked = True
                uploaded = True
                break
            except Exception:
                try:
                    loc.click(timeout=1200, force=True)
                    picked = True
                    break
                except Exception:
                    try:
                        loc.evaluate("el => el.click()")
                        picked = True
                        break
                    except Exception:
                        continue
        except Exception:
            continue

    if not picked:
        raise RuntimeError("未找到“本地上传”菜单")

    if uploaded:
        return

    set_ok = False
    for loc in [
        editor_page.locator('input[type="file"]:visible').last,
        editor_page.locator('input[type="file"]').last,
    ]:
        try:
            loc.set_input_files(file_paths, timeout=3500)
            set_ok = True
            break
        except Exception:
            continue
    if not set_ok:
        raise RuntimeError("未找到上传控件")


def _confirm_and_save(editor_page):
    def _wait_upload_done(timeout_ms=2600):
        end = time.time() + max(0.4, timeout_ms / 1000.0)
        while time.time() < end:
            has_items = False
            uploading = False
            for loc in [
                editor_page.locator(".ant-upload-list-item:visible"),
                editor_page.locator(".ant-upload-list-picture-card-container:visible"),
            ]:
                try:
                    if int(loc.count()) > 0:
                        has_items = True
                        break
                except Exception:
                    continue
            for loc in [
                editor_page.locator(".ant-upload-list-item-uploading:visible"),
                editor_page.locator(".ant-progress:visible"),
                editor_page.locator(":text('上传中'):visible"),
            ]:
                try:
                    if int(loc.count()) > 0:
                        uploading = True
                        break
                except Exception:
                    continue
            if has_items and (not uploading):
                return
            try:
                editor_page.wait_for_timeout(120)
            except Exception:
                time.sleep(0.12)

    def _wait_idle(timeout_ms=3000):
        deadline = time.time() + max(0.4, timeout_ms / 1000.0)
        while time.time() < deadline:
            busy = False
            for loc in [
                editor_page.locator("div.ant-modal-wrap:visible"),
                editor_page.locator("div.ant-modal-mask:visible"),
                editor_page.locator(".ant-spin-spinning:visible"),
                editor_page.locator(".ant-message-notice:visible"),
            ]:
                try:
                    if int(loc.count()) > 0:
                        busy = True
                        break
                except Exception:
                    continue
            if not busy:
                return
            try:
                editor_page.wait_for_timeout(120)
            except Exception:
                time.sleep(0.12)

    def _click_with_retry(locators, timeout_ms: int):
        last = None
        for _ in range(8):
            _wait_idle(1200)
            for loc in locators:
                try:
                    loc.wait_for(state="visible", timeout=600)
                    try:
                        loc.scroll_into_view_if_needed(timeout=700)
                    except Exception:
                        pass
                    try:
                        loc.click(timeout=700)
                        return
                    except Exception:
                        try:
                            loc.click(timeout=700, force=True)
                            return
                        except Exception:
                            try:
                                loc.evaluate("el => el.click()")
                                return
                            except Exception as e:
                                last = e
                except Exception as e:
                    last = e
                    continue
            try:
                editor_page.wait_for_timeout(160)
            except Exception:
                time.sleep(0.16)
        if last is not None:
            raise last

    try:
        editor_page.wait_for_timeout(700)
    except Exception:
        time.sleep(0.7)
    _wait_upload_done(2600)

    dialog = _find_visible_container(
        editor_page,
        [
            editor_page.locator("div.ant-modal-wrap:visible").last,
            editor_page.locator("div.ant-modal:visible").last,
            editor_page.locator('div[role="dialog"]:visible').last,
        ],
        timeout_ms=350,
    )

    confirm_locators = []
    for scope in [dialog, editor_page]:
        if scope is None:
            continue
        confirm_locators.extend(_action_locators(scope, "确定", "确认", "提交"))

    _click_with_retry(
        confirm_locators,
        timeout_ms=4500,
    )

    _wait_idle(2200)

    save_locators = _save_action_locators(editor_page)
    _click_with_retry(
        save_locators,
        timeout_ms=5200,
    )


def fill_product_description_images(page, sku: str, color: str, progress=None):
    if progress:
        progress("打开编辑描述…")

    editor_page = _open_description_editor(page)

    if progress:
        progress("进入批量传图…")
    _open_batch_upload(editor_page)

    if progress:
        progress("上传描述图片…")
    from image_resolver import resolve_variant_image_paths

    file_paths = resolve_variant_image_paths(sku, color)
    _upload_local_files(editor_page, file_paths)

    if progress:
        progress("保存产品描述…")
    _confirm_and_save(editor_page)
