import os
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import ctypes
from urllib.parse import urlparse

from PyQt5 import QtCore

from browser_launch import launch_persistent_context_with_fallback
from cdp_utils import close_cdp_page, list_cdp_pages, open_cdp_page
from album_cleanup_flow import clear_album_space
from dianxiaomi_flows import (
    HOME_URL,
    TEMU_ADD_URL,
    auto_fill_login,
    ensure_logged_in_account,
    enter_create_product_page_flow,
    fill_login_flow,
    select_shop_category_flow,
)
from publish_logger import finish_publish_log, start_publish_log, write_publish_log


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


def _is_dianxiaomi_home_page(url: str) -> bool:
    try:
        parsed = urlparse((url or "").strip())
    except Exception:
        return False
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").rstrip("/").lower()
    return host == "www.dianxiaomi.com" and path == "/home.htm"


class BrowserWorker(QtCore.QThread):
    started_ok = QtCore.pyqtSignal()
    failed = QtCore.pyqtSignal(str)

    def __init__(self, user_data_dir: str, port: int, url: str, username: str, password: str, browser_preference: str = "auto"):
        super().__init__()
        self.user_data_dir = user_data_dir
        self.port = int(port)
        self.url = url
        self.username = username
        self.password = password
        self.browser_preference = (browser_preference or "auto").strip().lower()
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        _silence_playwright_node_warnings()
        try:
            from playwright.sync_api import sync_playwright
        except Exception:
            self.failed.emit(
                "缺少依赖 playwright，请先安装：pip install playwright 并执行 python -m playwright install chromium"
            )
            return

        user_data_dir = (self.user_data_dir or "").strip()
        if not user_data_dir:
            self.failed.emit("浏览器配置目录为空")
            return
        os.makedirs(user_data_dir, exist_ok=True)

        url = (self.url or "").strip() or HOME_URL
        port = int(self.port)
        args = [
            f"--remote-debugging-port={port}",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
        ]

        try:
            with sync_playwright() as p:
                context = launch_persistent_context_with_fallback(
                    p.chromium,
                    user_data_dir,
                    args,
                    browser_preference=self.browser_preference,
                )
                try:
                    page = context.pages[0] if context.pages else context.new_page()
                    try:
                        page.on("dialog", _auto_dismiss_dialog)
                    except Exception:
                        pass
                    page.bring_to_front()
                    page.goto(url, wait_until="domcontentloaded")
                    try:
                        auto_fill_login(page, self.username, self.password)
                    except Exception:
                        pass
                    self.started_ok.emit()
                    while not self._stop:
                        time.sleep(0.25)
                finally:
                    try:
                        context.close()
                    except Exception:
                        pass
        except Exception as e:
            self.failed.emit(str(e))


class CdpActionWorker(QtCore.QThread):
    ok = QtCore.pyqtSignal(str)
    failed = QtCore.pyqtSignal(str)
    progress = QtCore.pyqtSignal(str)

    def __init__(
        self,
        action: str,
        cdp: str,
        page_url: str,
        page_ws: str = "",
        username: str = "",
        password: str = "",
        shop_name: str = "",
        category: str = "",
        title: str = "",
        sku: str = "",
        color: str = "",
    ):
        super().__init__()
        self.action = action
        self.cdp = cdp
        self.page_url = page_url
        self.page_ws = page_ws
        self.username = username
        self.password = password
        self.shop_name = shop_name
        self.category = category
        self.title = title
        self.sku = sku
        self.color = color

    def run(self):
        try:
            if self.action == "enter_create":
                enter_create_product_page_flow(self.cdp, self.page_url, self.page_ws)
                self.ok.emit("已进入创建产品页面")
                return
            if self.action == "select_shop_category":
                select_shop_category_flow(
                    self.cdp,
                    self.page_url,
                    self.shop_name,
                    self.category,
                    self.title,
                    self.sku,
                    self.color,
                    page_ws=self.page_ws,
                    progress=self.progress.emit,
                )
                self.ok.emit("已完成")
                return
            if self.action == "fill_login":
                fill_login_flow(self.cdp, self.page_url, self.page_ws, self.username, self.password)
                self.ok.emit("已填写账号密码，请手动输入验证码并登录")
                return
            self.failed.emit(f"未知动作：{self.action}")
        except Exception as e:
            self.failed.emit(str(e))


class AlbumCleanupWorker(QtCore.QThread):
    ok = QtCore.pyqtSignal(str)
    failed = QtCore.pyqtSignal(str)
    progress = QtCore.pyqtSignal(str)

    def __init__(self, cdp: str, max_rounds: int = 40):
        super().__init__()
        self.cdp = (cdp or "").strip()
        self.max_rounds = max(1, int(max_rounds or 40))

    def run(self):
        try:
            clear_album_space(self.cdp, progress=self.progress.emit, max_rounds=self.max_rounds)
            self.ok.emit("图片空间清理完成")
        except Exception as e:
            self.failed.emit(str(e))


class BatchPublishWorker(QtCore.QThread):
    ok = QtCore.pyqtSignal(str)
    failed = QtCore.pyqtSignal(str)
    progress = QtCore.pyqtSignal(str)
    row_done = QtCore.pyqtSignal(object, bool, str)

    def __init__(
        self,
        cdp: str,
        page_url: str,
        page_ws: str,
        rows: list,
        parallel_count: int,
        screen_geometry: dict = None,
        cleanup_every: int = 50,
        cleanup_max_rounds: int = 40,
        upload_fail_stop_threshold: int = 3,
        login_username: str = "",
        login_password: str = "",
    ):
        super().__init__()
        self.cdp = (cdp or "").strip()
        self.page_url = (page_url or "").strip()
        self.page_ws = (page_ws or "").strip()
        self.rows = rows or []
        self.parallel_count = max(1, int(parallel_count or 1))
        self.cleanup_every = max(1, int(cleanup_every or 50))
        self.cleanup_max_rounds = max(1, int(cleanup_max_rounds or 40))
        self.upload_fail_stop_threshold = max(0, int(upload_fail_stop_threshold if upload_fail_stop_threshold is not None else 3))
        self.login_username = (login_username or "").strip()
        self.login_password = login_password or ""
        self._slot_count = 1
        self.screen_geometry = screen_geometry or {}

    def _valid_rows(self):
        valid = []
        for r in self.rows:
            shop_name = (r.get("shop_name") or "").strip()
            category = (r.get("category") or "").strip()
            if not shop_name or not category:
                continue
            valid.append(
                {
                    "shop_name": shop_name,
                    "category": category,
                    "title": (r.get("title") or "").strip(),
                    "sku": (r.get("sku") or "").strip(),
                    "color": (r.get("color") or "").strip(),
                }
            )
        return valid

    def _window_bounds(self, slot: int, total_slots: int):
        left0 = int((self.screen_geometry or {}).get("left") or 0)
        top0 = int((self.screen_geometry or {}).get("top") or 0)
        sw = int((self.screen_geometry or {}).get("width") or 0)
        sh = int((self.screen_geometry or {}).get("height") or 0)
        if sw <= 0 or sh <= 0:
            try:
                user32 = ctypes.windll.user32
                sw = int(user32.GetSystemMetrics(0))
                sh = int(user32.GetSystemMetrics(1))
                left0 = 0
                top0 = 0
            except Exception:
                return None
        if sw <= 0 or sh <= 0:
            return None
        if total_slots <= 1:
            return {"left": left0, "top": top0, "width": sw, "height": sh}
        if total_slots == 2:
            half = max(320, sw // 2)
            left = left0 if int(slot) % 2 == 0 else (left0 + half)
            return {"left": left, "top": top0, "width": half, "height": sh}
        cols = min(3, total_slots)
        rows = (total_slots + cols - 1) // cols
        c = int(slot) % cols
        r = int(slot) // cols
        w = max(320, sw // cols)
        h = max(260, sh // max(1, rows))
        return {"left": left0 + c * w, "top": top0 + r * h, "width": w, "height": h}

    def _set_target_window_bounds(self, target_id: str, slot: int, total_slots: int):
        target_id = (target_id or "").strip()
        if not target_id:
            return
        bounds = self._window_bounds(slot, total_slots)
        if not bounds:
            return
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(self.cdp)
                try:
                    page = None
                    for ctx in browser.contexts:
                        if ctx.pages:
                            page = ctx.pages[0]
                            break
                    if page is None:
                        return
                    sess = page.context.new_cdp_session(page)
                    info = sess.send("Browser.getWindowForTarget", {"targetId": target_id})
                    win_id = int((info or {}).get("windowId") or 0)
                    if win_id > 0:
                        sess.send("Browser.setWindowBounds", {"windowId": win_id, "bounds": bounds})
                finally:
                    if hasattr(browser, "disconnect"):
                        browser.disconnect()
                    else:
                        browser.close()
        except Exception:
            pass

    def _open_target(self, seed: int = 0, slot: int = 0, total_slots: int = 1):
        url = f"{TEMU_ADD_URL}&batch_slot={int(time.time() * 1000)}_{seed}"
        target_id = ""
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(self.cdp)
                try:
                    page = None
                    for ctx in browser.contexts:
                        if ctx.pages:
                            page = ctx.pages[0]
                            break
                    if page is not None:
                        sess = page.context.new_cdp_session(page)
                        created = sess.send("Target.createTarget", {"url": url, "newWindow": True, "background": True})
                        target_id = ((created or {}).get("targetId") or "").strip()
                        if target_id:
                            try:
                                info = sess.send("Browser.getWindowForTarget", {"targetId": target_id})
                                win_id = int((info or {}).get("windowId") or 0)
                                bounds = self._window_bounds(slot, total_slots)
                                if win_id > 0 and bounds:
                                    sess.send("Browser.setWindowBounds", {"windowId": win_id, "bounds": bounds})
                            except Exception:
                                pass
                finally:
                    if hasattr(browser, "disconnect"):
                        browser.disconnect()
                    else:
                        browser.close()
        except Exception:
            target_id = ""

        if target_id:
            for _ in range(15):
                try:
                    pages = list_cdp_pages(self.cdp)
                    for p in pages:
                        ws = (p.get("webSocketDebuggerUrl") or "").strip()
                        if ws.endswith("/" + target_id):
                            return {"url": (p.get("url") or url).strip(), "ws": ws}
                except Exception:
                    pass
                time.sleep(0.12)

        opened = open_cdp_page(self.cdp, url)
        ws = (opened.get("webSocketDebuggerUrl") or "").strip()
        if "/devtools/page/" in ws:
            tid = ws.rsplit("/devtools/page/", 1)[-1].strip()
            self._set_target_window_bounds(tid, slot, total_slots)
        return {"url": (opened.get("url") or url).strip(), "ws": ws}

    def _ensure_targets(self, needed: int):
        return [{} for _ in range(max(1, int(needed)))]

    def _is_non_blocking_publish_error(self, err_msg: str):
        t = (err_msg or "").strip()
        if not t:
            return False
        if ("立即发布" in t and "受理" in t and "未检测到" in t) or ("发布未受理" in t):
            return True
        return False

    def _is_upload_failure(self, err_msg: str):
        t = (err_msg or "").strip()
        if not t:
            return False
        material_signals = [
            "产品素材图",
            "本地图片",
            "未找到序列号对应图片",
            "未能触发",
            "文件选择",
            "上传控件",
            "上传后未检测到完成状态",
        ]
        variant_signals = [
            "选择图片",
            "多图选择",
            "图片路径解析",
            "颜色套图",
            "未找到颜色套图",
        ]
        if any(s in t for s in material_signals) and ("图片" in t or "上传" in t or "文件" in t):
            return True
        if any(s in t for s in variant_signals) and ("图片" in t or "上传" in t or "文件" in t):
            return True
        return False

    def _close_browser_quietly(self):
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(self.cdp)
                try:
                    page = None
                    for ctx in browser.contexts:
                        if ctx.pages:
                            page = ctx.pages[0]
                            break
                    if page is None:
                        return
                    sess = page.context.new_cdp_session(page)
                    sess.send("Browser.close")
                finally:
                    try:
                        if hasattr(browser, "disconnect"):
                            browser.disconnect()
                        else:
                            browser.close()
                    except Exception:
                        pass
        except Exception:
            pass

    def _close_home_pages_after_start(self):
        closed = 0
        try:
            pages = list_cdp_pages(self.cdp)
        except Exception as e:
            self.progress.emit(f"关闭店小秘首页失败，无法读取标签页：{e}")
            return 0
        for page in pages:
            url = (page.get("url") or "").strip()
            if not _is_dianxiaomi_home_page(url):
                continue
            ws = (page.get("webSocketDebuggerUrl") or "").strip()
            try:
                if close_cdp_page(self.cdp, page_ws=ws):
                    closed += 1
                else:
                    self.progress.emit(f"关闭店小秘首页失败：未能关闭 {url}")
            except Exception as e:
                self.progress.emit(f"关闭店小秘首页失败：{e}")
        if closed:
            self.progress.emit(f"已关闭店小秘首页标签页：{closed} 个")
        return closed

    def _run_one(self, target: dict, row: dict, index: int, total: int, slot: int):
        prefix = f"[{index}/{total}]"
        sku = row.get("sku") or "-"
        self.progress.emit(f"{prefix} SKU:{sku} 开始")
        created_here = False
        success = False
        use_target = target or {}
        if not (use_target.get("url") or "").strip():
            use_target = self._open_target(index, slot=slot, total_slots=self._slot_count)
            created_here = True
        try:
            select_shop_category_flow(
                self.cdp,
                use_target.get("url") or "",
                row.get("shop_name") or "",
                row.get("category") or "",
                row.get("title") or "",
                row.get("sku") or "",
                row.get("color") or "",
                page_ws=use_target.get("ws") or "",
                progress=lambda m: self.progress.emit(f"{prefix} SKU:{sku} {m}"),
            )
            success = True
            return True
        except Exception as e:
            msg = str(e)
            if self._is_non_blocking_publish_error(msg):
                self.progress.emit(f"{prefix} SKU:{sku} 立即发布未受理，关闭当前失败页并继续")
                if created_here or (use_target.get("ws") or "").strip():
                    try:
                        close_cdp_page(self.cdp, page_ws=use_target.get("ws") or "")
                    except Exception:
                        pass
                raise RuntimeError(f"[NON_BLOCKING] {msg}")
            self.progress.emit(f"{prefix} SKU:{sku} 失败，保留页面供检查")
            raise e
        finally:
            if success and (created_here or (use_target.get("ws") or "").strip()):
                try:
                    close_cdp_page(self.cdp, page_ws=use_target.get("ws") or "")
                except Exception:
                    pass

    def run(self):
        try:
            def _clear_album_with_retry(stage: str):
                last = None
                for attempt in range(3):
                    try:
                        clear_album_space(
                            self.cdp,
                            progress=self.progress.emit,
                            max_rounds=self.cleanup_max_rounds,
                            max_seconds=max(90, min(240, int(self.cleanup_max_rounds or 40) * 6)),
                        )
                        return
                    except Exception as e:
                        last = e
                        self.progress.emit(f"{stage}清理图片空间第{attempt + 1}次失败，准备重试：{e}")
                        try:
                            time.sleep(1.2)
                        except Exception:
                            pass
                raise RuntimeError(f"{stage}清理图片空间失败：{last}")

            started = time.time()
            rows = self._valid_rows()
            if not rows:
                raise RuntimeError("没有可发布的数据（店铺名称或产品分类为空）")
            total = len(rows)
            slots = min(self.parallel_count, total)
            self._slot_count = slots
            targets = self._ensure_targets(slots)
            if not targets:
                raise RuntimeError("未找到可用页面")
            task_name = f"批量上架_{total}条_并发{slots}"
            log_session = start_publish_log(task_name)
            self.progress.emit(f"日志文件：{log_session.get('file_path')}")
            if self.login_username:
                self.progress.emit(f"检测店小秘登录账号：目标账号 {self.login_username}")
                ensure_logged_in_account(
                    self.cdp,
                    self.page_url,
                    self.page_ws,
                    self.login_username,
                    self.login_password,
                    progress=self.progress.emit,
                    timeout_s=240,
                )
            self._close_home_pages_after_start()
            self.progress.emit("开始前清理图片空间…")
            try:
                _clear_album_with_retry("开始前")
                write_publish_log(log_session, 0, total, {}, ok=True, reason="开始前已清理图片空间")
            except Exception as e:
                write_publish_log(log_session, 0, total, {}, ok=False, reason=f"开始前清理图片空间失败：{e}")
                raise RuntimeError(f"开始前清理图片空间失败，已停止上架：{e}")

            self.progress.emit(f"准备并发发布：{len(targets)} 个页面，{total} 条数据")

            next_idx = 0
            done = 0
            success_count = 0
            failed_count = 0
            future_map = {}
            pause_for_cleanup = False
            next_cleanup_at = self.cleanup_every
            consecutive_upload_failures = 0
            stop_reason = ""
            with ThreadPoolExecutor(max_workers=len(targets)) as ex:
                for i, target in enumerate(targets):
                    if next_idx >= total:
                        break
                    row = rows[next_idx]
                    idx = next_idx + 1
                    seed_target = target if i == 0 else {}
                    fut = ex.submit(self._run_one, seed_target, row, idx, total, i)
                    future_map[fut] = {"row": row, "index": idx, "slot": i}
                    next_idx += 1

                while (future_map or next_idx < total) and not stop_reason:
                    if pause_for_cleanup and (not future_map):
                        self.progress.emit(f"已成功{success_count}条，暂停上架并清理图片空间…")
                        try:
                            _clear_album_with_retry(f"成功{success_count}条后")
                            write_publish_log(log_session, 0, total, {}, ok=True, reason=f"成功{success_count}条后已清理图片空间")
                        except Exception as e:
                            write_publish_log(log_session, 0, total, {}, ok=False, reason=f"成功{success_count}条后清理图片空间失败：{e}")
                            raise RuntimeError(f"成功{success_count}条后清理图片空间失败，已停止上架：{e}")
                        while next_cleanup_at <= success_count:
                            next_cleanup_at += self.cleanup_every
                        pause_for_cleanup = False

                    if (not future_map) and (next_idx < total) and (not pause_for_cleanup):
                        for i in range(slots):
                            if next_idx >= total:
                                break
                            row = rows[next_idx]
                            idx = next_idx + 1
                            nf = ex.submit(self._run_one, {}, row, idx, total, i)
                            future_map[nf] = {"row": row, "index": idx, "slot": i}
                            next_idx += 1
                    if not future_map:
                        continue

                    finished, _ = wait(list(future_map.keys()), return_when=FIRST_COMPLETED)
                    for fut in finished:
                        meta = future_map.pop(fut, None) or {}
                        row = meta.get("row") or {}
                        idx = int(meta.get("index") or 0)
                        slot = int(meta.get("slot") or 0)
                        err_msg = ""
                        ok = False
                        try:
                            fut.result()
                            ok = True
                        except Exception as e:
                            err_msg = str(e)
                            ok = False
                        if (not ok) and err_msg.startswith("[NON_BLOCKING]"):
                            err_msg = err_msg.replace("[NON_BLOCKING]", "", 1).strip()
                        done += 1
                        if ok:
                            success_count += 1
                            consecutive_upload_failures = 0
                            self.progress.emit(f"已完成 {done}/{total}")
                            if success_count >= next_cleanup_at:
                                pause_for_cleanup = True
                        else:
                            failed_count += 1
                            sku = (row.get("sku") or "-").strip() or "-"
                            self.progress.emit(f"[{idx}/{total}] SKU:{sku} 失败并跳过：{err_msg}")
                            if self._is_upload_failure(err_msg):
                                consecutive_upload_failures += 1
                                if self.upload_fail_stop_threshold > 0:
                                    self.progress.emit(
                                        f"连续上传失败 {consecutive_upload_failures}/{self.upload_fail_stop_threshold}"
                                    )
                            else:
                                consecutive_upload_failures = 0
                        try:
                            write_publish_log(log_session, idx, total, row, ok=ok, reason=err_msg)
                        except Exception:
                            pass
                        try:
                            self.row_done.emit(row, bool(ok), err_msg)
                        except Exception:
                            pass
                        if (
                            self.upload_fail_stop_threshold > 0
                            and consecutive_upload_failures >= self.upload_fail_stop_threshold
                        ):
                            stop_reason = (
                                f"连续 {consecutive_upload_failures} 个产品图片上传失败，已停止上架并尝试关闭浏览器。"
                                "可能是图片目录、货号、颜色套图、页面上传控件或运行设置有问题，请检查后再重新运行。"
                            )
                            self.progress.emit(stop_reason)
                            for pending in list(future_map.keys()):
                                try:
                                    pending.cancel()
                                except Exception:
                                    pass
                            self._close_browser_quietly()
                            break
                        if (next_idx < total) and (not pause_for_cleanup):
                            row = rows[next_idx]
                            idx = next_idx + 1
                            nf = ex.submit(self._run_one, {}, row, idx, total, slot)
                            future_map[nf] = {"row": row, "index": idx, "slot": slot}
                            next_idx += 1
                    if stop_reason:
                        break
            elapsed = max(0.0, time.time() - started)
            mm = int(elapsed // 60)
            ss = int(elapsed % 60)
            try:
                finish_publish_log(
                    log_session,
                    success_count,
                    failed_count,
                    done,
                    total,
                    elapsed,
                    stopped=bool(stop_reason),
                    reason=stop_reason,
                )
            except Exception:
                pass
            if stop_reason:
                self.failed.emit(
                    f"{stop_reason}\n\n本次已处理 {done}/{total}，成功{success_count}，失败{failed_count}，用时{mm:02d}:{ss:02d}"
                )
                return
            self.ok.emit(f"发布完成：成功{success_count}，失败{failed_count}，总计{done}/{total}，用时{mm:02d}:{ss:02d}")
        except Exception as e:
            self.failed.emit(str(e))
