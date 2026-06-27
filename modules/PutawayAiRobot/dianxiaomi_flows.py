import os
import re
import time

from element_ui_select import get_el_form_item_value, open_el_form_item_dropdown, select_el_option_by_text

HOME_URL = "https://www.dianxiaomi.com/home.htm"
TEMU_ADD_URL = "https://www.dianxiaomi.com/web/temu/add?ll=undefined"
TEMU_ADD_PATH = "/web/temu/add"


def _silence_playwright_node_warnings():
    cur = os.environ.get("NODE_OPTIONS", "")
    if "--no-deprecation" in cur:
        return
    os.environ["NODE_OPTIONS"] = (cur + " --no-deprecation").strip()

def _auto_dismiss_dialog(dialog):
    try:
        dialog.dismiss()
    except Exception:
        try:
            dialog.accept()
        except Exception:
            pass


def _pick_category_option_text(category: str) -> str:
    category = (category or "").strip()
    if not category:
        return ""
    parts = [p.strip() for p in re.split(r"[>/、\\s]+", category) if p.strip()]
    return parts[-1] if parts else category


def _text_re_shop_field():
    return re.compile(r"(店铺|店铺名称|店铺名|选择店铺)", re.I)


def _text_re_category_field():
    return re.compile(r"(产品分类|商品分类|分类|选择分类)", re.I)


def _open_field_for_select(page, field_re):
    for loc in [
        page.get_by_role("combobox", name=field_re).first,
        page.get_by_label(field_re).first,
        page.get_by_placeholder(field_re).first,
    ]:
        try:
            loc.click(timeout=2000)
            return True
        except Exception:
            continue

    for loc in [
        page.locator('input[placeholder*="店铺"]') if "店铺" in field_re.pattern else page.locator('input[placeholder*="分类"]'),
        page.locator('input[aria-label*="店铺"]') if "店铺" in field_re.pattern else page.locator('input[aria-label*="分类"]'),
    ]:
        try:
            loc.first.click(timeout=2000)
            return True
        except Exception:
            continue
    return False


def _find_ant_select_container(page, label_text: str):
    label_text = (label_text or "").strip()
    if not label_text:
        return None
    for loc in [
        page.locator('input#rc_select_0').first.locator('xpath=ancestor::div[contains(@class,"ant-select")][1]').first if "店铺" in label_text else page.locator('input#rc_select_1').first.locator('xpath=ancestor::div[contains(@class,"ant-select")][1]').first,
        page.locator(f'xpath=//*[contains(normalize-space(.),"{label_text}")]/following::div[contains(@class,"ant-select")][1]').first,
        page.locator(f'div.ant-form-item:has-text("{label_text}") div.ant-select').first,
    ]:
        try:
            loc.wait_for(state="visible", timeout=350)
            return loc
        except Exception:
            continue
    return None


def _ant_select_selected_text(container):
    for loc in [
        container.locator(".ant-select-selection-item").first,
        container.locator(".ant-select-selection-placeholder").first,
    ]:
        try:
            txt = (loc.inner_text(timeout=300) or "").strip()
            if txt:
                return txt
        except Exception:
            continue
    return ""


def _open_ant_select_by_label(page, label_text: str):
    container = _find_ant_select_container(page, label_text)
    if container is None:
        return False
    for loc in [
        container.locator(".ant-select-selector").first,
        container.locator(".ant-select-arrow").first,
        container,
    ]:
        try:
            try:
                loc.scroll_into_view_if_needed(timeout=700)
            except Exception:
                pass
            loc.click(timeout=500, force=True)
            return True
        except Exception:
            continue
    return False


def _select_ant_option_fast(page, label_text: str, option_text: str):
    option_text = (option_text or "").strip()
    if not option_text:
        return False
    container = _find_ant_select_container(page, label_text)
    if container is None:
        return False
    before = _ant_select_selected_text(container)
    if option_text in before:
        return True
    if not _open_ant_select_by_label(page, label_text):
        return False
    try:
        page.locator("div.ant-select-dropdown:visible").first.wait_for(state="visible", timeout=350)
    except Exception:
        pass
    typed = False
    for inp in [container.locator("input.ant-select-selection-search-input").first, page.locator('input.ant-select-selection-search-input:visible').last]:
        try:
            inp.wait_for(state="attached", timeout=280)
            try:
                inp.fill(option_text, timeout=300)
                typed = True
                break
            except Exception:
                continue
        except Exception:
            continue
    for loc in [
        page.locator(f'div.ant-select-dropdown:visible .ant-select-item-option[title="{option_text}"]').first,
        page.locator(f'div.ant-select-dropdown:visible [title="{option_text}"]').first,
        page.locator("div.ant-select-dropdown:visible .ant-select-item-option", has_text=option_text).first,
        page.locator("div.ant-select-dropdown:visible [role='option']", has_text=option_text).first,
        page.locator("div.ant-select-dropdown:visible .ant-select-item-option-content", has_text=option_text).first,
    ]:
        try:
            loc.wait_for(state="visible", timeout=260)
            try:
                loc.scroll_into_view_if_needed(timeout=300)
            except Exception:
                pass
            loc.click(timeout=500, force=True)
            try:
                page.wait_for_timeout(60)
            except Exception:
                time.sleep(0.06)
            after = _ant_select_selected_text(container)
            if option_text in after:
                return True
            try:
                hidden = int(page.locator("div.ant-select-dropdown:visible").count()) == 0
            except Exception:
                hidden = False
            if hidden:
                return True
        except Exception:
            continue
    try:
        if typed:
            page.keyboard.press("Enter")
            try:
                page.wait_for_timeout(60)
            except Exception:
                time.sleep(0.06)
            after = _ant_select_selected_text(container)
            return option_text in after
        try:
            page.keyboard.press("ArrowDown")
            page.keyboard.press("Enter")
            try:
                page.wait_for_timeout(120)
            except Exception:
                time.sleep(0.12)
            after = _ant_select_selected_text(container)
            if option_text in after:
                return True
            try:
                hidden = int(page.locator("div.ant-select-dropdown:visible").count()) == 0
            except Exception:
                hidden = False
            return hidden
        except Exception:
            return False
    except Exception:
        return False


def auto_fill_login(page, username: str, password: str):
    username = (username or "").strip()
    password = password or ""
    if not username or not password:
        return False

    def _try_fill(locator, value: str):
        try:
            count = locator.count()
        except Exception:
            return False
        for i in range(min(int(count), 6)):
            try:
                locator.nth(i).fill(value, timeout=800)
                return True
            except Exception:
                continue
        return False

    filled_user = False
    for loc in [
        page.locator('input[placeholder*="手机号"]'),
        page.locator('input[placeholder*="手机"]'),
        page.locator('input[placeholder*="邮箱"]'),
        page.locator('input[placeholder*="账号"]'),
        page.locator('input[placeholder*="用户名"]'),
        page.locator('input[name*="user" i]'),
        page.locator('input[name*="account" i]'),
        page.locator('input[type="tel"]'),
        page.locator('input[type="text"]'),
    ]:
        if _try_fill(loc, username):
            filled_user = True
            break

    filled_pwd = _try_fill(page.locator('input[type="password"]'), password)

    if filled_user and filled_pwd:
        for cap in [
            page.locator('input[placeholder*="验证码"]'),
            page.locator('input[name*="captcha" i]'),
        ]:
            try:
                cap.first.click(timeout=500)
                break
            except Exception:
                continue
        return True
    return False


def _fill_product_title(page, title: str):
    title = (title or "").strip()
    if not title:
        return
    cur = get_el_form_item_value(page, "产品标题")
    if cur == title:
        return
    try:
        page.get_by_text("产品标题").first.wait_for(timeout=3000)
    except Exception:
        pass

    locators = [
        page.locator('.el-form-item__label:has-text("产品标题")').locator(
            'xpath=ancestor::div[contains(@class,"el-form-item")][1]'
        ).locator("textarea, input, [contenteditable=\"true\"]").first,
        page.locator('xpath=//*[contains(normalize-space(.),"产品标题")]/following::textarea[1]').first,
        page.locator('xpath=//*[contains(normalize-space(.),"产品标题")]/following::input[1]').first,
        page.locator('.el-form-item:has-text("产品标题") textarea').first,
        page.locator('.el-form-item:has-text("产品标题") input').first,
        page.locator('.el-form-item:has-text("产品标题") [contenteditable="true"]').first,
        page.get_by_label(re.compile(r"产品标题", re.I)).first,
        page.get_by_placeholder(re.compile(r"产品标题", re.I)).first,
    ]

    last_err = None
    for loc in locators:
        try:
            loc.wait_for(state="attached", timeout=1200)
            try:
                loc.scroll_into_view_if_needed(timeout=1200)
            except Exception:
                pass
            try:
                loc.click(timeout=800)
            except Exception:
                pass
            try:
                loc.fill(title, timeout=1500)
                return
            except Exception:
                try:
                    page.keyboard.press("Control+A")
                    page.keyboard.type(title, delay=3)
                    return
                except Exception as e:
                    last_err = e
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"未找到“产品标题”输入框：{last_err}")


def _resolve_sku_image_path(sku: str):
    from image_resolver import resolve_sku_image_path

    return resolve_sku_image_path(sku)


def _upload_material_image(page, sku: str):
    file_path = _resolve_sku_image_path(sku)

    try:
        page.get_by_text("产品素材图").first.wait_for(timeout=3000)
    except Exception:
        pass

    def _material_area():
        for loc in [
            page.locator('.el-form-item__label:has-text("产品素材图")').locator(
                'xpath=ancestor::div[contains(@class,"el-form-item")][1]'
            ).first,
            page.locator('.el-form-item:has-text("产品素材图")').first,
            page.locator('xpath=//*[contains(normalize-space(.),"产品素材图")]/following::div[contains(@class,"el-form-item")][1]').first,
        ]:
            try:
                loc.wait_for(state="attached", timeout=350)
                return loc
            except Exception:
                continue
        return None

    def _wait_material_upload_done(timeout_s: float = 22.0):
        started = time.time()
        deadline = started + max(1.0, float(timeout_s))
        quiet_seen = 0
        while time.time() < deadline:
            area = _material_area()
            scopes = [area, page] if area is not None else [page]
            uploading = False
            has_preview = False
            for scope in scopes:
                for loc in [
                    scope.locator(".el-upload-list__item.is-uploading:visible"),
                    scope.locator(".el-progress:visible"),
                    scope.locator(".ant-progress:visible"),
                    scope.locator(".el-loading-mask:visible"),
                    scope.locator(".ant-spin-spinning:visible"),
                    scope.locator(':text("上传中"):visible'),
                ]:
                    try:
                        if int(loc.count()) > 0:
                            uploading = True
                            break
                    except Exception:
                        continue
                if uploading:
                    break
            if area is not None:
                for loc in [
                    area.locator(".el-upload-list__item:visible"),
                    area.locator("img[src]:visible"),
                    area.locator('[class*="upload-list"] img:visible'),
                ]:
                    try:
                        if int(loc.count()) > 0:
                            has_preview = True
                            break
                    except Exception:
                        continue
            elapsed = time.time() - started
            if elapsed >= 1.2 and has_preview and not uploading:
                return True
            if elapsed >= 2.5 and not uploading:
                quiet_seen += 1
                if quiet_seen >= 3:
                    return True
            else:
                quiet_seen = 0
            try:
                page.wait_for_timeout(220)
            except Exception:
                time.sleep(0.22)
        return True

    def _try_hover_once():
        area = _material_area()
        targets = [
            area.locator('img, .el-upload, .el-upload--picture-card, [class*="upload"]').first if area is not None else None,
            page.locator('xpath=//*[contains(normalize-space(.),"产品素材图")]/following::div[contains(@class,"el-upload")][1]').first,
            page.locator('xpath=//*[contains(normalize-space(.),"产品素材图")]/following::img[1]').first,
            page.locator('.el-form-item:has-text("产品素材图") img').first,
            page.locator('.el-form-item:has-text("产品素材图") .el-upload').first,
            page.get_by_text("暂无图片").first,
        ]
        for t in targets:
            if t is None:
                continue
            try:
                t.wait_for(state="attached", timeout=800)
                try:
                    t.scroll_into_view_if_needed(timeout=1200)
                except Exception:
                    pass
                t.hover(timeout=1200)
                return True
            except Exception:
                continue
        return False

    hovered = _try_hover_once()
    if not hovered:
        for _ in range(8):
            try:
                page.mouse.wheel(0, 900)
            except Exception:
                try:
                    page.evaluate("window.scrollBy(0, 900)")
                except Exception:
                    pass
            try:
                page.wait_for_timeout(80)
            except Exception:
                time.sleep(0.08)
            if _try_hover_once():
                hovered = True
                break
    if not hovered:
        raise RuntimeError("未找到“产品素材图/暂无图片”区域")

    clicked = False
    for loc in [
        page.get_by_text("本地图片").first,
        page.locator('li:has-text("本地图片")').first,
        page.locator('span:has-text("本地图片")').first,
    ]:
        try:
            with page.expect_file_chooser(timeout=3000) as fc:
                loc.click(timeout=1500)
            chooser = fc.value
            chooser.set_files(file_path)
            clicked = True
            break
        except Exception:
            continue

    if not clicked:
        area = _material_area()
        for inp in [
            area.locator('input[type="file"]').last if area is not None else None,
            page.locator('xpath=//*[contains(normalize-space(.),"产品素材图")]/following::input[@type="file"][1]').first,
        ]:
            if inp is None:
                continue
            try:
                inp.set_input_files(file_path, timeout=3000)
                clicked = True
                break
            except Exception:
                continue

    if not clicked:
        raise RuntimeError("未能触发“本地图片”文件选择或上传控件")

    _wait_material_upload_done()


def _select_variant_template(page, template_name: str):
    template_name = (template_name or "").strip() or "T恤"

    try:
        page.get_by_text("变种属性").first.wait_for(timeout=3000)
    except Exception:
        pass

    opened = open_el_form_item_dropdown(page, "引用模板", re.compile(r"请选择.*引用模板", re.I))
    if not opened:
        for loc in [
            page.locator('input[placeholder*="引用模板"]').first,
            page.locator('xpath=//*[contains(normalize-space(.),"变种属性")]/following::input[contains(@placeholder,"引用模板")][1]').first,
            page.locator('xpath=//*[contains(normalize-space(.),"变种属性")]/following::div[contains(@class,"el-select")][1]').first,
            page.locator('.el-form-item:has-text("变种属性") input').first,
            page.locator('.el-form-item:has-text("变种属性") .el-select').first,
        ]:
            try:
                loc.scroll_into_view_if_needed(timeout=1200)
            except Exception:
                pass
            try:
                loc.click(timeout=1800)
                opened = True
                break
            except Exception:
                continue
    if not opened:
        raise RuntimeError("未找到“变种属性”右侧的“引用模板”下拉框")

    select_el_option_by_text(page, template_name)
    try:
        page.wait_for_timeout(180)
    except Exception:
        time.sleep(0.18)
    for loc in [
        page.locator('div.el-message-box__wrapper:visible button:has-text("确定")').first,
        page.locator('div.el-dialog__wrapper:visible button:has-text("确定")').first,
        page.get_by_role("button", name="确定").first,
        page.get_by_text("确定", exact=True).first,
    ]:
        try:
            loc.click(timeout=1200, force=True)
            break
        except Exception:
            continue


def _is_checkbox_selected(checkbox, timeout_ms: int = 120) -> bool:
    for loc in [checkbox.locator('input[type="checkbox"]').first, checkbox]:
        try:
            if loc.is_checked(timeout=timeout_ms):
                return True
        except Exception:
            continue
    for loc in [checkbox.locator('input.checkbox-input[type="checkbox"]').first, checkbox]:
        try:
            checked = loc.evaluate("el => !!el.checked")
            if bool(checked):
                return True
        except Exception:
            continue
    for loc in [checkbox.locator('input[type="checkbox"]').first, checkbox]:
        try:
            v = loc.get_attribute("checked", timeout=timeout_ms)
            if v is not None:
                return True
        except Exception:
            continue
    for loc in [checkbox.locator(".el-checkbox__input").first, checkbox]:
        try:
            cls = (loc.get_attribute("class", timeout=timeout_ms) or "").strip()
            if "is-checked" in cls:
                return True
        except Exception:
            continue
    try:
        aria = (checkbox.get_attribute("aria-checked", timeout=timeout_ms) or "").strip().lower()
        if aria == "true":
            return True
    except Exception:
        pass
    return False


def _fill_and_select_variant_color(page, color: str, progress=None):
    color = (color or "").strip()
    if not color:
        return

    try:
        page.get_by_text("变种属性").first.scroll_into_view_if_needed(timeout=900)
    except Exception:
        pass
    try:
        page.mouse.wheel(0, 420)
    except Exception:
        pass

    def _find_checkbox(text: str, timeout_ms: int = 120):
        text_re = re.compile(re.escape(text), re.I)
        value_hint = ""
        t = (text or "").strip().lower()
        if t in {"黑", "黑色", "black"}:
            value_hint = "3002"
        elif t in {"白", "白色", "white"}:
            value_hint = "2001"
        candidates = []
        if value_hint:
            candidates.extend(
                [
                    page.locator(f'input.checkbox-input[type="checkbox"][value="{value_hint}"]').first,
                    page.locator(f'input[type="checkbox"][value="{value_hint}"]').first,
                ]
            )
        candidates.extend(
            [
                page.locator("label.el-checkbox", has_text=text_re).first,
                page.locator(".el-checkbox", has_text=text_re).first,
                page.locator("tr", has_text=text_re).locator("label.el-checkbox").first,
                page.locator("li", has_text=text_re).locator("label.el-checkbox").first,
                page.get_by_role("checkbox", name=text_re).first,
            ]
        )
        for loc in candidates:
            try:
                loc.wait_for(state="attached", timeout=timeout_ms)
                try:
                    tag = (loc.evaluate("el => (el.tagName || '').toLowerCase()") or "").strip()
                except Exception:
                    tag = ""
                if tag == "input":
                    try:
                        wrap = loc.locator("xpath=ancestor::label[1]").first
                        wrap.wait_for(state="attached", timeout=80)
                        return wrap
                    except Exception:
                        return loc
                return loc
            except Exception:
                continue
        return None

    def _wait_checkbox_state(text: str, checked: bool, timeout_ms: int = 1200):
        deadline = time.time() + max(0.2, timeout_ms / 1000.0)
        last = None
        while time.time() < deadline:
            cb = _find_checkbox(text, timeout_ms=120)
            if cb is not None:
                last = cb
                now = _is_checkbox_selected(cb, timeout_ms=120)
                if now == checked:
                    return cb
            try:
                page.wait_for_timeout(70)
            except Exception:
                time.sleep(0.07)
        return last

    def _uncheck_if_selected(text: str):
        cb = _wait_checkbox_state(text, checked=True, timeout_ms=350)
        if cb is None or not _is_checkbox_selected(cb, timeout_ms=120):
            return
        for _ in range(3):
            try:
                cb.scroll_into_view_if_needed(timeout=280)
            except Exception:
                pass
            try:
                cb.click(timeout=420, force=True)
            except Exception:
                pass
            now = _wait_checkbox_state(text, checked=False, timeout_ms=520)
            if now is not None and not _is_checkbox_selected(now, timeout_ms=120):
                return
            cb = now or cb
        if _is_checkbox_selected(cb, timeout_ms=120):
            raise RuntimeError(f"取消颜色失败：{text}")

    if color.lower() not in {"黑", "黑色"}:
        if progress:
            progress("取消默认黑色…")
        _uncheck_if_selected("黑色")
        _uncheck_if_selected("黑")

    if progress:
        progress("勾选目标颜色…")
    target = _find_checkbox(color, timeout_ms=350)
    if target is None:
        raise RuntimeError(f"未找到颜色选项：{color}")

    if not _is_checkbox_selected(target, timeout_ms=120):
        ok = False
        for _ in range(3):
            try:
                target.scroll_into_view_if_needed(timeout=280)
            except Exception:
                pass
            try:
                target.click(timeout=420, force=True)
            except Exception:
                pass
            now = _wait_checkbox_state(color, checked=True, timeout_ms=620)
            if now is not None and _is_checkbox_selected(now, timeout_ms=120):
                ok = True
                target = now
                break
            target = now or target
        if not ok:
            raise RuntimeError(f"颜色“{color}”点击后未勾选成功")

    if color.lower() not in {"黑", "黑色"}:
        _uncheck_if_selected("黑色")
        _uncheck_if_selected("黑")


def _fill_skc_code(page, sku: str):
    sku = (sku or "").strip()
    if not sku:
        return None

    for loc in [
        page.locator('.el-form-item:has-text("SKC编码") input').first,
        page.locator('.el-form-item:has-text("货号") input').first,
        page.locator('xpath=//*[contains(normalize-space(.),"SKC编码（货号）")]/following::input[1]').first,
        page.locator('xpath=//*[contains(normalize-space(.),"SKC编码")]/following::input[1]').first,
        page.locator('xpath=//*[contains(normalize-space(.),"货号")]/following::input[1]').first,
    ]:
        try:
            loc.wait_for(state="attached", timeout=600)
            loc.scroll_into_view_if_needed(timeout=500)
        except Exception:
            continue
        try:
            loc.click(timeout=500)
            loc.fill(sku, timeout=700)
            return loc
        except Exception:
            continue
    raise RuntimeError("未找到“SKC编码（货号）”输入框")


def _select_images_for_skc_row(page, skc_input, sku: str, color: str):
    sku = (sku or "").strip()
    if not sku:
        return
    try:
        from image_resolver import resolve_variant_image_paths
    except Exception as e:
        raise RuntimeError(f"图片路径解析模块加载失败：{e}")

    file_paths = resolve_variant_image_paths(sku, color)

    candidates = []
    try:
        candidates.append(
            page.locator(f'.el-table__body-wrapper tr:has-text("{sku}")')
            .first.locator('button:has-text("选择图片"), a:has-text("选择图片"), span:has-text("选择图片")')
            .first
        )
    except Exception:
        pass
    try:
        candidates.append(
            skc_input.locator('xpath=ancestor::div[contains(@class,"el-form-item")][1]')
            .locator('button:has-text("选择图片"), a:has-text("选择图片"), span:has-text("选择图片")')
            .first
        )
    except Exception:
        pass
    try:
        candidates.append(
            skc_input.locator('xpath=ancestor::div[contains(@class,"el-row")][1]')
            .locator('button:has-text("选择图片"), a:has-text("选择图片"), span:has-text("选择图片")')
            .first
        )
    except Exception:
        pass
    candidates.extend(
        [
            page.get_by_role("button", name="选择图片").first,
            page.get_by_text("选择图片").first,
            page.locator('button:has-text("选择图片"), a:has-text("选择图片"), span:has-text("选择图片")').first,
        ]
    )

    clicked = False
    for btn in candidates:
        try:
            btn.wait_for(state="attached", timeout=900)
            try:
                btn.scroll_into_view_if_needed(timeout=900)
            except Exception:
                pass
            btn.click(timeout=1200)
            clicked = True
            break
        except Exception:
            continue
    if not clicked:
        raise RuntimeError("未找到序列号同行右侧“选择图片”按钮")

    try:
        page.wait_for_timeout(180)
    except Exception:
        time.sleep(0.18)

    def _safe_count(locator):
        try:
            return int(locator.count())
        except Exception:
            return -1

    def _pick_overlay():
        for loc in [
            page.locator("div.el-dialog__wrapper:visible").last,
            page.locator('div[role="dialog"]:visible').last,
            page.locator("div.el-popover:visible").last,
            page.locator("ul.el-dropdown-menu:visible").last,
            page.locator("div.ant-dropdown:visible").last,
            page.locator("ul.ant-dropdown-menu:visible").last,
        ]:
            try:
                loc.wait_for(state="visible", timeout=450)
                return loc
            except Exception:
                continue
        return page

    overlay = _pick_overlay()

    before_inputs = _safe_count(page.locator('input[type="file"]'))

    clicked = False
    for loc in [
        overlay.get_by_text("本地图片").first,
        overlay.get_by_text("本地图⽚").first,
        overlay.locator('li.ant-dropdown-menu-item[data-menu-id="local"]').first,
        overlay.locator('li.ant-dropdown-menu-item[title="本地图片"]').first,
        overlay.locator('li:has-text("本地图片")').first,
        overlay.locator('li:has-text("本地图")').first,
        overlay.locator('span:has-text("本地图片")').first,
        overlay.locator('span:has-text("本地图")').first,
        page.get_by_text("本地图片").first,
        page.get_by_text("本地图⽚").first,
        page.locator('li.ant-dropdown-menu-item[data-menu-id="local"]').first,
        page.locator('li.ant-dropdown-menu-item[title="本地图片"]').first,
        page.locator('li:has-text("本地图片")').first,
        page.locator('li:has-text("本地图")').first,
        page.locator('span:has-text("本地图片")').first,
        page.locator('span:has-text("本地图")').first,
    ]:
        try:
            loc.wait_for(state="visible", timeout=900)
            try:
                loc.scroll_into_view_if_needed(timeout=900)
            except Exception:
                pass
            try:
                with page.expect_file_chooser(timeout=1200) as fc:
                    loc.click(timeout=1500)
                chooser = fc.value
                chooser.set_files(file_paths)
                clicked = True
                break
            except Exception:
                loc.click(timeout=1500)
            clicked = True
            break
        except Exception:
            continue

    if not clicked:
        try:
            inp = overlay.locator('input[type="file"]').first
            inp.set_input_files(file_paths, timeout=3000)
            clicked = True
        except Exception:
            pass
    if not clicked:
        try:
            inp = page.locator('input[type="file"]').last
            inp.set_input_files(file_paths, timeout=3000)
            clicked = True
        except Exception:
            pass
    if clicked:
        after_inputs = before_inputs
        for _ in range(25):
            after_inputs = _safe_count(page.locator('input[type="file"]'))
            if after_inputs > before_inputs and after_inputs > 0:
                break
            try:
                page.wait_for_timeout(120)
            except Exception:
                time.sleep(0.12)
        if after_inputs > 0:
            try:
                inp = overlay.locator('input[type="file"]').last
                inp.set_input_files(file_paths, timeout=3000)
                return
            except Exception:
                pass
            try:
                inp = page.locator('input[type="file"]').nth(after_inputs - 1)
                inp.set_input_files(file_paths, timeout=3000)
                return
            except Exception:
                pass

    if not clicked:
        raise RuntimeError("未能触发“本地图片”多图选择或上传控件")


def _select_shop_and_category(page, shop_name: str, category: str, title: str, sku: str, color: str = "", progress=None):
    shop_name = (shop_name or "").strip()
    category = (category or "").strip()
    if not shop_name:
        raise RuntimeError("店铺名称为空")
    if not category:
        raise RuntimeError("产品分类为空")

    try:
        page.get_by_text("店铺名称").first.wait_for(timeout=8000)
    except Exception:
        pass

    cur_shop = get_el_form_item_value(page, "店铺名称")
    if cur_shop != shop_name:
        if progress:
            progress("选择店铺名称…")
        if not _select_ant_option_fast(page, "店铺名称", shop_name):
            opened = open_el_form_item_dropdown(page, "店铺名称", re.compile(r"请选择.*店铺", re.I))
            if not opened and not _open_field_for_select(page, _text_re_shop_field()):
                raise RuntimeError("未找到店铺选择框")
            select_el_option_by_text(page, shop_name)

    cur_cat = get_el_form_item_value(page, "产品分类")
    want_cat = _pick_category_option_text(category)
    if cur_cat == want_cat:
        if progress:
            progress("引用产品模板…")
        _apply_template_after_category(page, want_cat)
        if progress:
            progress("填写产品标题…")
        _fill_product_title(page, title)
        if progress:
            progress("上传产品素材图…")
        _upload_material_image(page, sku)
        if progress:
            progress("选择变种属性引用模板…")
        _select_variant_template(page, "T恤")
        if progress:
            progress("设置颜色并勾选…")
        _fill_and_select_variant_color(page, color, progress=progress)
        if progress:
            progress("填写SKC编码（货号）…")
        skc_input = _fill_skc_code(page, sku)
        if skc_input is not None:
            if progress:
                progress("自动选择图片…")
            _select_images_for_skc_row(page, skc_input, sku, color)
            if progress:
                progress("添加尺码表…")
            from size_chart_flow import add_size_chart_by_template

            add_size_chart_by_template(page, "T恤 店小秘模板", progress=progress)
            if progress:
                progress("选择模特信息…")
            from model_info_flow import select_model_tryon_size

            select_model_tryon_size(page, "M", progress=progress)
            if progress:
                progress("填写SKU高级前后缀…")
            from sku_advanced_flow import fill_sku_advanced_prefix_suffix

            fill_sku_advanced_prefix_suffix(page, sku, progress=progress)
            if progress:
                progress("填写申报价格…")
            from declare_price_flow import fill_declare_price_batch

            fill_declare_price_batch(page, "13", progress=progress)
            if progress:
                progress("填写包裹尺寸…")
            from package_size_flow import fill_package_size_batch

            fill_package_size_batch(page, "30", "25", "1", progress=progress)
            from weight_flow import fill_weight_sequence

            fill_weight_sequence(page, 142, 5, 5, progress=progress)
            from suggest_price_flow import fill_suggest_price_apply_all

            fill_suggest_price_apply_all(page, "7", progress=progress)
            from product_description_flow import fill_product_description_images

            fill_product_description_images(page, sku, color, progress=progress)
            from publish_flow import publish_now

            publish_now(page, progress=progress)
        return

    if progress:
        progress("选择产品分类…")
    if not _select_ant_option_fast(page, "产品分类", want_cat):
        opened = open_el_form_item_dropdown(page, "产品分类", re.compile(r"请选择.*分类", re.I))
        if not opened and not _open_field_for_select(page, _text_re_category_field()):
            raise RuntimeError("未找到产品分类选择框")
        select_el_option_by_text(page, want_cat)
    if progress:
        progress("引用产品模板…")
    _apply_template_after_category(page, want_cat)
    if progress:
        progress("填写产品标题…")
    _fill_product_title(page, title)
    if progress:
        progress("上传产品素材图…")
    _upload_material_image(page, sku)
    if progress:
        progress("选择变种属性引用模板…")
    _select_variant_template(page, "T恤")
    if progress:
        progress("设置颜色并勾选…")
    _fill_and_select_variant_color(page, color, progress=progress)
    if progress:
        progress("填写SKC编码（货号）…")
    skc_input = _fill_skc_code(page, sku)
    if skc_input is not None:
        if progress:
            progress("自动选择图片…")
        _select_images_for_skc_row(page, skc_input, sku, color)
        if progress:
            progress("添加尺码表…")
        from size_chart_flow import add_size_chart_by_template

        add_size_chart_by_template(page, "T恤 店小秘模板", progress=progress)
        if progress:
            progress("选择模特信息…")
        from model_info_flow import select_model_tryon_size

        select_model_tryon_size(page, "M", progress=progress)
        if progress:
            progress("填写SKU高级前后缀…")
        from sku_advanced_flow import fill_sku_advanced_prefix_suffix

        fill_sku_advanced_prefix_suffix(page, sku, progress=progress)
        if progress:
            progress("填写申报价格…")
        from declare_price_flow import fill_declare_price_batch

        fill_declare_price_batch(page, "13", progress=progress)
        if progress:
            progress("填写包裹尺寸…")
        from package_size_flow import fill_package_size_batch

        fill_package_size_batch(page, "30", "25", "1", progress=progress)
        from weight_flow import fill_weight_sequence

        fill_weight_sequence(page, 142, 5, 5, progress=progress)
        from suggest_price_flow import fill_suggest_price_apply_all

        fill_suggest_price_apply_all(page, "7", progress=progress)
        from product_description_flow import fill_product_description_images

        fill_product_description_images(page, sku, color, progress=progress)
        from publish_flow import publish_now

        publish_now(page, progress=progress)


def _apply_template_after_category(page, template_keyword: str):
    template_keyword = (template_keyword or "").strip()

    clicked = False
    for loc in [
        page.get_by_role("button", name="引用产品").first,
        page.get_by_text("引用产品").first,
        page.locator('button:has-text("引用产品")').first,
        page.locator('.el-dropdown:has-text("引用产品")').first,
    ]:
        try:
            loc.click(timeout=2500)
            clicked = True
            break
        except Exception:
            continue
    if not clicked:
        raise RuntimeError("未找到“引用产品”按钮")

    clicked = False
    for loc in [
        page.get_by_role("menuitem", name="引用产品模板").first,
        page.get_by_text("引用产品模板").first,
        page.locator('li.el-dropdown-menu__item:has-text("引用产品模板")').first,
        page.locator('ul.el-dropdown-menu:visible li:has-text("引用产品模板")').first,
    ]:
        try:
            loc.click(timeout=2500)
            clicked = True
            break
        except Exception:
            continue
    if not clicked:
        raise RuntimeError("未找到“引用产品模板”菜单项")

    dialog = None
    title_re = re.compile(r"引用模[板版]", re.I)
    try:
        title = page.locator(".el-dialog__title", has_text=title_re).first
        title.wait_for(state="visible", timeout=3500)
        dlg = title.locator('xpath=ancestor::div[contains(@class,"el-dialog__wrapper")]').first
        dlg.wait_for(state="visible", timeout=900)
        dialog = dlg
    except Exception:
        pass
    if dialog is None:
        try:
            dlg = page.locator("div.el-dialog__wrapper:visible", has_text=title_re).first
            dlg.wait_for(state="visible", timeout=3500)
            dialog = dlg
        except Exception:
            pass
    if dialog is None:
        try:
            dlg = page.locator('div[role="dialog"]:visible', has_text=title_re).first
            dlg.wait_for(state="visible", timeout=3500)
            dialog = dlg
        except Exception:
            pass
    if dialog is None:
        raise RuntimeError("未检测到“引用模板”弹窗")

    def _click_quote_from_bottom():
        for list_loc in [
            dialog.locator('div.el-table__fixed-right span.link:has-text("引用"):visible'),
            dialog.locator('span.link:has-text("引用"):visible'),
        ]:
            try:
                n = int(list_loc.count())
            except Exception:
                n = 0
            if n <= 0:
                continue
            for i in range(min(n, 12)):
                idx = n - 1 - i
                try:
                    loc = list_loc.nth(idx)
                    try:
                        loc.scroll_into_view_if_needed(timeout=350)
                    except Exception:
                        pass
                    loc.click(timeout=500, force=True)
                    return True
                except Exception:
                    continue
        return False

    if _click_quote_from_bottom():
        try:
            page.locator("div.el-dialog__wrapper:visible").first.wait_for(state="hidden", timeout=900)
        except Exception:
            pass
        return

    def _try_fast_quote_click():
        for loc in [
            page.locator('div.el-dialog__wrapper:visible div.el-table__fixed-right span.link:has-text("引用")').first,
            page.locator('div.el-dialog__wrapper:visible span.link:has-text("引用")').first,
        ]:
            try:
                loc.wait_for(state="visible", timeout=350)
                try:
                    loc.scroll_into_view_if_needed(timeout=450)
                except Exception:
                    pass
                loc.click(timeout=500, force=True)
                return True
            except Exception:
                continue
        return False

    if _try_fast_quote_click():
        try:
            page.locator("div.el-dialog__wrapper:visible").first.wait_for(state="hidden", timeout=1200)
        except Exception:
            pass
        return

    template_keyword = ""
    if template_keyword:
        try:
            search_input = dialog.locator('.el-form-item:has-text("模板名称") input').first
            try:
                search_input.wait_for(state="visible", timeout=1500)
            except Exception:
                search_input = dialog.locator("input").first
            search_input.fill(template_keyword, timeout=1500)
        except Exception:
            pass
        for loc in [
            dialog.get_by_role("button", name="搜索").first,
            dialog.get_by_text("搜索").first,
        ]:
            try:
                loc.click(timeout=1500)
                break
            except Exception:
                continue
        try:
            dialog.wait_for_timeout(60)
        except Exception:
            time.sleep(0.06)

    try:
        dialog.locator('div.el-table__fixed-right span.link:has-text("引用")').first.wait_for(state="visible", timeout=900)
    except Exception:
        try:
            dialog.locator('span.link:has-text("引用")').first.wait_for(state="visible", timeout=900)
        except Exception:
            pass

    def _click_quote_in_row(row_locator):
        for loc in [
            row_locator.locator('span.link:has-text("引用")').first,
            row_locator.locator('a:has-text("引用")').first,
            row_locator.get_by_role("link", name="引用").first,
            row_locator.get_by_role("button", name="引用").first,
            row_locator.get_by_text("引用", exact=True).first,
            row_locator.get_by_text("引用").first,
        ]:
            try:
                try:
                    loc.scroll_into_view_if_needed(timeout=600)
                except Exception:
                    pass
                loc.click(timeout=700, force=True)
                return True
            except Exception:
                continue
        return False

    def _count(locator):
        try:
            return int(locator.count())
        except Exception:
            return -1

    clicked = False
    row_idx = None
    if template_keyword:
        rows = None
        try:
            rows = dialog.locator(".el-table__body-wrapper tr")
        except Exception:
            rows = dialog.locator("tr")
        n = _count(rows)
        if n > 0:
            for i in range(min(n, 30)):
                try:
                    txt = (rows.nth(i).inner_text(timeout=800) or "").strip()
                except Exception:
                    continue
                if template_keyword in txt:
                    row_idx = i
                    break
        if row_idx is not None:
            try:
                fixed_rows = dialog.locator(".el-table__fixed-right .el-table__fixed-body-wrapper tr")
                fn = _count(fixed_rows)
                if fn > row_idx:
                    if _click_quote_in_row(fixed_rows.nth(row_idx)):
                        clicked = True
            except Exception:
                pass
            if not clicked:
                try:
                    if _click_quote_in_row(rows.nth(row_idx)):
                        clicked = True
                except Exception:
                    pass

    if not clicked:
        try:
            fixed_first = dialog.locator(".el-table__fixed-right .el-table__fixed-body-wrapper tr").first
            if _count(fixed_first) != 0 and _click_quote_in_row(fixed_first):
                clicked = True
        except Exception:
            pass
        if not clicked:
            try:
                first_row = dialog.locator(".el-table__body-wrapper tr").first
            except Exception:
                first_row = dialog.locator("tr").first
            try:
                if _count(first_row) != 0 and _click_quote_in_row(first_row):
                    clicked = True
            except Exception:
                pass

    if not clicked:
        for loc in [
            dialog.locator('div.el-table__fixed-right span.link:has-text("引用")').first,
            dialog.locator('span.link:has-text("引用")').first,
            dialog.locator('a:has-text("引用")').first,
            dialog.get_by_role("link", name="引用").first,
            dialog.get_by_text("引用", exact=True).first,
        ]:
            try:
                try:
                    loc.scroll_into_view_if_needed(timeout=600)
                except Exception:
                    pass
                loc.click(timeout=700, force=True)
                clicked = True
                break
            except Exception:
                continue
    if not clicked:
        quote_cnt = _count(dialog.locator('span.link:has-text("引用")'))
        fixed_quote_cnt = _count(dialog.locator('div.el-table__fixed-right span.link:has-text("引用")'))
        row_cnt = _count(dialog.locator(".el-table__body-wrapper tr"))
        hint = f"quote={quote_cnt}, fixed_quote={fixed_quote_cnt}, rows={row_cnt}"
        raise RuntimeError(f"未找到弹窗“操作”列中的“引用”按钮（{hint}）")

    try:
        dialog.locator("button.el-dialog__headerbtn").first.click(timeout=800)
    except Exception:
        pass

    try:
        dialog.wait_for(state="hidden", timeout=1200)
    except Exception:
        pass
    try:
        page.locator("div.v-modal:visible").first.wait_for(state="hidden", timeout=1200)
    except Exception:
        pass


def _pick_target_page(pages, page_url: str, page_ws: str = ""):
    page_url = (page_url or "").strip()
    page_ws = (page_ws or "").strip()
    if page_ws and "/devtools/page/" in page_ws:
        want_tid = page_ws.rsplit("/devtools/page/", 1)[-1].strip()
        if want_tid:
            for pg in pages:
                try:
                    sess = pg.context.new_cdp_session(pg)
                    info = sess.send("Target.getTargetInfo")
                    tid = ((info or {}).get("targetInfo") or {}).get("targetId") or ""
                    if tid and tid.strip() == want_tid:
                        return pg
                except Exception:
                    continue
    if page_url:
        for pg in pages:
            if (pg.url or "").strip() == page_url:
                return pg
    for pg in pages:
        if TEMU_ADD_PATH in ((pg.url or "").strip()):
            return pg
    return pages[0]


def _pick_home_or_login_page(pages, page_url: str = "", page_ws: str = ""):
    page_url = (page_url or "").strip()
    page_ws = (page_ws or "").strip()
    if page_ws or page_url:
        try:
            return _pick_target_page(pages, page_url, page_ws)
        except Exception:
            pass
    for pg in pages:
        url = (pg.url or "").strip()
        if "dianxiaomi.com" in url and ("/web/home" in url or "/home.htm" in url or "login" in url):
            return pg
    for pg in pages:
        if "dianxiaomi.com" in ((pg.url or "").strip()):
            return pg
    return pages[0]


def _normalize_account_name(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip()).lower()


def get_logged_in_username(page) -> str:
    selectors = [
        ".li-hover.user.relative .user-name",
        ".head-nav-right .user-name",
        ".btn-user .user-name",
        "[class*='user-name'][title]",
        "[class*='user'] [title]",
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="attached", timeout=500)
            title = (loc.get_attribute("title", timeout=300) or "").strip()
            text = (loc.inner_text(timeout=300) or "").strip()
            name = title or text
            if name and "退出" not in name and len(name) <= 80:
                return name
        except Exception:
            continue
    try:
        name = page.evaluate(
            """() => {
                const nodes = Array.from(document.querySelectorAll('.head-nav-right .user-name, .li-hover.user.relative .user-name, [class*="user-name"]'));
                for (const el of nodes) {
                    const v = (el.getAttribute('title') || el.textContent || '').trim();
                    if (v && !v.includes('退出') && v.length <= 80) return v;
                }
                return '';
            }"""
        )
        return (name or "").strip()
    except Exception:
        return ""


def _is_login_page(page) -> bool:
    url = (page.url or "").lower()
    if "login" in url:
        return True
    for loc in [
        page.locator('input[type="password"]'),
        page.locator('input[placeholder*="验证码"]'),
        page.locator('input[placeholder*="账号"]'),
    ]:
        try:
            if int(loc.count()) > 0:
                return True
        except Exception:
            continue
    return False


def logout_current_account(page):
    for loc in [
        page.locator(".li-hover.user.relative .btn-user").first,
        page.locator(".head-nav-right .btn-user").first,
        page.locator(".li-hover.user.relative").first,
        page.locator(".head-nav-right .user-name").first,
        page.locator("[class*='user-name']").first,
    ]:
        try:
            loc.wait_for(state="visible", timeout=800)
            try:
                loc.hover(timeout=800)
            except Exception:
                pass
            try:
                loc.click(timeout=800, force=True)
            except Exception:
                pass
            break
        except Exception:
            continue

    clicked = False
    for loc in [
        page.locator(".dropdown-list").get_by_text("退出", exact=True).first,
        page.locator(".dropdown-list a:has-text('退出')").first,
        page.locator(".dropdown-list li:has-text('退出')").first,
        page.locator("a:has-text('退出')").last,
        page.get_by_text("退出", exact=True).last,
    ]:
        try:
            loc.wait_for(state="visible", timeout=1200)
            loc.click(timeout=1500, force=True)
            clicked = True
            break
        except Exception:
            continue
    if not clicked:
        raise RuntimeError("当前账号不匹配，但未找到店小秘首页“退出”入口")

    for loc in [
        page.get_by_role("button", name="确定").first,
        page.get_by_role("button", name="确认").first,
        page.locator("button:has-text('确定')").first,
        page.locator("button:has-text('确认')").first,
    ]:
        try:
            loc.click(timeout=1000, force=True)
            break
        except Exception:
            continue

    end = time.time() + 12
    while time.time() < end:
        if _is_login_page(page):
            return True
        try:
            page.wait_for_timeout(300)
        except Exception:
            time.sleep(0.3)
    return True


def ensure_logged_in_account(
    cdp_base_url: str,
    page_url: str = "",
    page_ws: str = "",
    username: str = "",
    password: str = "",
    progress=None,
    timeout_s: int = 180,
):
    _silence_playwright_node_warnings()
    username = (username or "").strip()
    password = password or ""
    if not username:
        return
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise RuntimeError("缺少依赖 playwright，请先安装：pip install playwright 并执行 python -m playwright install chromium") from e

    cdp_base_url = (cdp_base_url or "").strip().rstrip("/")
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(cdp_base_url)
        try:
            pages = []
            for ctx in browser.contexts:
                pages.extend(ctx.pages)
            if not pages:
                raise RuntimeError("CDP已连接，但未发现任何页面(tab)")
            target = _pick_home_or_login_page(pages, page_url, page_ws)
            try:
                target.on("dialog", _auto_dismiss_dialog)
            except Exception:
                pass
            try:
                target.bring_to_front()
            except Exception:
                pass

            if "dianxiaomi.com" not in ((target.url or "").lower()):
                target.goto(HOME_URL, wait_until="domcontentloaded", timeout=12000)

            current = get_logged_in_username(target)
            if current and _normalize_account_name(current) == _normalize_account_name(username):
                if progress:
                    progress(f"当前店小秘账号已匹配：{current}")
                return

            if current:
                if progress:
                    progress(f"当前店小秘账号为 {current}，目标账号为 {username}，正在退出当前账号…")
                logout_current_account(target)
            elif not _is_login_page(target):
                if progress:
                    progress("未识别到当前登录账号，正在打开店小秘首页检查登录状态…")
                try:
                    target.goto(HOME_URL, wait_until="domcontentloaded", timeout=12000)
                except Exception:
                    pass

            if not password:
                raise RuntimeError(f"目标账号 {username} 未保存密码，无法自动填写登录信息")

            filled_once = False
            deadline = time.time() + max(30, int(timeout_s or 180))
            while time.time() < deadline:
                current = get_logged_in_username(target)
                if current and _normalize_account_name(current) == _normalize_account_name(username):
                    if progress:
                        progress(f"检测到目标账号 {current} 已登录，继续上架")
                    return

                if not filled_once and (_is_login_page(target) or "dianxiaomi.com" in ((target.url or "").lower())):
                    ok = auto_fill_login(target, username, password)
                    if ok and not filled_once:
                        filled_once = True
                        if progress:
                            progress("已填写目标账号密码，请手动输入验证码并完成登录，软件会等待后继续")
                try:
                    target.wait_for_timeout(1000)
                except Exception:
                    time.sleep(1)

            raise RuntimeError(f"等待目标账号 {username} 登录超时，请确认验证码已填写并登录成功")
        finally:
            if hasattr(browser, "disconnect"):
                browser.disconnect()
            else:
                browser.close()


def enter_create_product_page_flow(cdp_base_url: str, page_url: str, page_ws: str = ""):
    _silence_playwright_node_warnings()
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise RuntimeError("缺少依赖 playwright，请先安装：pip install playwright 并执行 python -m playwright install chromium") from e

    cdp_base_url = (cdp_base_url or "").strip().rstrip("/")
    page_url = (page_url or "").strip()

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(cdp_base_url)
        try:
            pages = []
            for ctx in browser.contexts:
                pages.extend(ctx.pages)
            if not pages:
                raise RuntimeError("CDP已连接，但未发现任何页面(tab)")

            target = _pick_target_page(pages, page_url, page_ws)
            try:
                target.on("dialog", _auto_dismiss_dialog)
            except Exception:
                pass

            clicked = False
            for loc in [
                target.get_by_role("link", name="产品", exact=True).first,
                target.get_by_role("button", name="产品", exact=True).first,
                target.get_by_text("产品", exact=True).first,
            ]:
                try:
                    loc.click(timeout=3000)
                    clicked = True
                    break
                except Exception:
                    continue
            if not clicked:
                raise RuntimeError("未找到首页菜单栏“产品”")

            try:
                target.wait_for_load_state("domcontentloaded", timeout=1200)
            except Exception:
                pass

            time.sleep(0.05)
            clicked = False
            for loc in [
                target.get_by_role("menuitem", name="创建产品").first,
                target.get_by_role("link", name="创建产品").first,
                target.get_by_role("button", name="创建产品").first,
                target.get_by_text("创建产品").first,
            ]:
                try:
                    loc.click(timeout=3000)
                    clicked = True
                    break
                except Exception:
                    continue
            if not clicked:
                raise RuntimeError("未找到产品衍生菜单“创建产品”")
        finally:
            if hasattr(browser, "disconnect"):
                browser.disconnect()
            else:
                browser.close()


def select_shop_category_flow(
    cdp_base_url: str,
    page_url: str,
    shop_name: str,
    category: str,
    title: str = "",
    sku: str = "",
    color: str = "",
    page_ws: str = "",
    progress=None,
):
    _silence_playwright_node_warnings()
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise RuntimeError("缺少依赖 playwright，请先安装：pip install playwright 并执行 python -m playwright install chromium") from e

    cdp_base_url = (cdp_base_url or "").strip().rstrip("/")
    page_url = (page_url or "").strip()

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(cdp_base_url)
        try:
            pages = []
            for ctx in browser.contexts:
                pages.extend(ctx.pages)
            if not pages:
                raise RuntimeError("CDP已连接，但未发现任何页面(tab)")

            target = _pick_target_page(pages, page_url, page_ws)
            try:
                target.on("dialog", _auto_dismiss_dialog)
            except Exception:
                pass
            if TEMU_ADD_PATH not in ((target.url or "").strip()):
                try:
                    target.goto(TEMU_ADD_URL, wait_until="domcontentloaded", timeout=8000)
                except Exception:
                    pass
            if progress:
                progress("开始执行…")
            _select_shop_and_category(target, shop_name, category, title, sku, color, progress=progress)
        finally:
            if hasattr(browser, "disconnect"):
                browser.disconnect()
            else:
                browser.close()


def fill_login_flow(cdp_base_url: str, page_url: str, page_ws: str = "", username: str = "", password: str = ""):
    _silence_playwright_node_warnings()
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise RuntimeError("缺少依赖 playwright，请先安装：pip install playwright 并执行 python -m playwright install chromium") from e

    cdp_base_url = (cdp_base_url or "").strip().rstrip("/")
    page_url = (page_url or "").strip()

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(cdp_base_url)
        try:
            pages = []
            for ctx in browser.contexts:
                pages.extend(ctx.pages)
            if not pages:
                raise RuntimeError("CDP已连接，但未发现任何页面(tab)")

            target = _pick_target_page(pages, page_url, page_ws)
            try:
                target.on("dialog", _auto_dismiss_dialog)
            except Exception:
                pass
            ok = auto_fill_login(target, username, password)
            if not ok:
                raise RuntimeError("未找到可填写的登录输入框（页面可能已登录或登录页结构变化）")
        finally:
            if hasattr(browser, "disconnect"):
                browser.disconnect()
            else:
                browser.close()
