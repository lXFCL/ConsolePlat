from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen

from consoleplat.config import ShopAccount
from consoleplat.services.monitor_service import MonitorEvent, MonitorSnapshot, UrgencyOrder


TARGET_URL = "https://agentseller.temu.com/stock/fully-mgt/order-manage-urgency"
KNOWN_MONITOR_SHOPS = ("YUHOOBO", "YUHAOBO")


class LoginRequiredError(RuntimeError):
    """Raised when the browser is waiting for manual login or verification."""


class ShopSwitchError(RuntimeError):
    """Raised when the target shop cannot be selected safely."""


def monitor_shop_names(target_shop: str) -> tuple[str, ...]:
    names = [target_shop.strip().upper()]
    for name in KNOWN_MONITOR_SHOPS:
        if name not in names:
            names.append(name)
    return tuple(name for name in names if name)


def _shop_token(value: str) -> str:
    return re.sub(r"[^A-Z0-9_-]+", "", (value or "").upper())


def choose_current_shop_name(elements: list[dict[str, Any]], known_shops: tuple[str, ...]) -> str:
    known = {_shop_token(name) for name in known_shops if _shop_token(name)}
    candidates: list[tuple[float, str]] = []
    for item in elements:
        text = _shop_token(str(item.get("text") or ""))
        if not text:
            continue
        x = float(item.get("x") or 0)
        y = float(item.get("y") or 0)
        w = float(item.get("w") or 0)
        h = float(item.get("h") or 0)
        if w <= 0 or h <= 0 or y > 120:
            continue
        tokens = [name for name in known if name and name in text]
        if not tokens:
            tokens = re.findall(r"\bYU[A-Z0-9_-]{3,}\b", text)
        for token in tokens:
            candidates.append((abs(y - 24) + (w * h) / 10000 + len(text) / 20, token))
    if not candidates:
        return ""
    return min(candidates, key=lambda item: item[0])[1]


def choose_shop_click_point(elements: list[dict[str, Any]], current_shop: str) -> tuple[int, int] | None:
    target = _shop_token(current_shop)
    candidates = []
    for item in elements:
        text = _shop_token(str(item.get("text") or ""))
        x = float(item.get("x") or 0)
        y = float(item.get("y") or 0)
        w = float(item.get("w") or 0)
        h = float(item.get("h") or 0)
        if not target or target not in text or w <= 0 or h <= 0 or y > 120:
            continue
        candidates.append((abs(y - 24) + (w * h) / 10000 + len(text) / 20, x, y, w, h))
    if not candidates:
        return None
    _, x, y, w, h = min(candidates, key=lambda item: item[0])
    return int(x + w / 2), int(y + h / 2)


def choose_target_shop_switch_point(elements: list[dict[str, Any]], target_shop: str) -> tuple[int, int] | None:
    target = _shop_token(target_shop)
    rows = []
    for item in elements:
        text = _shop_token(str(item.get("text") or ""))
        x = float(item.get("x") or 0)
        y = float(item.get("y") or 0)
        w = float(item.get("w") or 0)
        h = float(item.get("h") or 0)
        if target and target in text and "切换" in str(item.get("text") or "") and w > 0 and h > 0:
            rows.append((x, y, w, h))
    for row_x, row_y, row_w, row_h in sorted(rows, key=lambda row: row[1]):
        for item in elements:
            text = str(item.get("text") or "").strip()
            x = float(item.get("x") or 0)
            y = float(item.get("y") or 0)
            w = float(item.get("w") or 0)
            h = float(item.get("h") or 0)
            if text == "切换" and row_y <= y <= row_y + row_h and x > row_x + row_w / 2 and w > 0 and h > 0:
                return int(x + w / 2), int(y + h / 2)
    return None


def is_login_page_text(text: str) -> bool:
    clean = (text or "").replace(" ", "")
    if not clean:
        return False
    if is_authorization_confirm_text(text):
        return True
    if is_business_page_text(text):
        return False
    login_markers = ("登录", "密码", "手机号", "确认授权并前往", "授权登录")
    return any(marker in clean for marker in login_markers)


def is_business_page_text(text: str) -> bool:
    clean = (text or "").replace(" ", "")
    if not clean:
        return False
    has_page_title = "紧急备货建议" in clean
    has_stock_table = "备货单号" in clean or "备货件数" in clean or "暂无数据" in clean
    has_stock_tabs = any(marker in clean for marker in ("全部(", "全部（", "待创建", "待发货", "已入库"))
    return has_page_title and (has_stock_table or has_stock_tabs)


def is_auth_gateway_text(text: str) -> bool:
    clean = (text or "").replace(" ", "")
    if not clean:
        return False
    return "中国地区" in clean and "商家中心" in clean and "敬请期待" in clean


def is_authorization_confirm_text(text: str) -> bool:
    clean = (text or "").replace(" ", "")
    return "即将前往SellerCentral" in clean and "确认授权并前往" in clean


def choose_auth_gateway_click_point(elements: list[dict[str, Any]]) -> tuple[int, int] | None:
    candidates = []
    for item in elements:
        text = str(item.get("text") or "")
        if "商家中心" not in text:
            continue
        x = float(item.get("x") or 0)
        y = float(item.get("y") or 0)
        w = float(item.get("w") or 0)
        h = float(item.get("h") or 0)
        if w <= 0 or h <= 0:
            continue
        if x < 500 or y < 220:
            continue
        candidates.append((w * h, x, y, w, h))
    if not candidates:
        return None
    _, x, y, w, h = min(candidates, key=lambda value: value[0])
    return int(x + w / 2), int(y + h / 2)


def choose_preferred_page(urls: list[str]) -> int | None:
    if not urls:
        return None

    def score(url: str) -> int:
        parsed = urlparse(url or "")
        host = parsed.netloc.lower()
        path = parsed.path.lower()
        if host == "agentseller.temu.com" and path == "/stock/fully-mgt/order-manage-urgency":
            return 0
        if host == "seller.kuajingmaihuo.com" and path == "/settle/seller-login":
            return 1
        if host == "agentseller.temu.com" and path == "/auth/authentication":
            return 2
        if host == "agentseller.temu.com":
            return 3
        return 9

    return min(range(len(urls)), key=lambda index: (score(urls[index]), -index))


def choose_new_page(before_urls: list[str], after_urls: list[str]) -> int | None:
    before_counts: dict[str, int] = {}
    for url in before_urls:
        before_counts[url] = before_counts.get(url, 0) + 1
    for index in range(len(after_urls) - 1, -1, -1):
        url = after_urls[index]
        count = before_counts.get(url, 0)
        if count:
            before_counts[url] = count - 1
            continue
        return index
    return None


def phone_login_selectors() -> list[str]:
    return [
        "input[name='usernameId']",
        "input[placeholder*='手机号码']",
        "input[placeholder*='手机号']",
        "input[placeholder*='账号']",
        "input[name*='phone']",
        "input[type='tel']",
    ]


def login_submit_labels() -> list[str]:
    return ["授权登录", "确认授权并前往", "登录"]


def choose_policy_click_point(elements: list[dict[str, Any]]) -> tuple[int, int] | None:
    primary_candidates = []
    fallback_candidates = []
    for item in elements:
        text = str(item.get("text") or "")
        x = float(item.get("x") or 0)
        y = float(item.get("y") or 0)
        w = float(item.get("w") or 0)
        h = float(item.get("h") or 0)
        if w <= 0 or h <= 0:
            continue
        if "授权您的账号ID" in text:
            primary_candidates.append((w * h, x, y, w, h))
        elif "隐私政策" in text:
            fallback_candidates.append((w * h, x, y, w, h))
    candidates = primary_candidates or fallback_candidates
    if not candidates:
        return None
    _, x, y, _w, h = min(candidates, key=lambda value: value[0])
    return int(max(x - 10, 0)), int(y + min(h / 2, 8))


def should_navigate_to_target(url: str, text: str) -> bool:
    if is_business_page_text(text) or is_login_page_text(text) or is_auth_gateway_text(text):
        return False
    parsed = urlparse(url or "")
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    if host == "agentseller.temu.com" and path == "/stock/fully-mgt/order-manage-urgency":
        return False
    if host == "seller.kuajingmaihuo.com" and path == "/settle/seller-login":
        return False
    if host == "agentseller.temu.com" and path == "/auth/authentication":
        return False
    return True


EXTRACT_MONITOR_SCRIPT = r"""
() => {
  const norm = s => (s || '').replace(/\s+/g, ' ').trim();
  const pick = (text, re) => {
    const m = text.match(re);
    return m ? norm(m[1]) : '';
  };
  const splitAttr = attr => {
    const clean = norm(attr);
    const idx = clean.lastIndexOf('-');
    if (idx <= 0) return { color: clean, size: '' };
    return { color: clean.slice(0, idx), size: clean.slice(idx + 1) };
  };
  const parseQty = value => {
    const m = String(value || '').match(/\d+/);
    return m ? Number(m[0]) : 0;
  };
  const text = norm(document.body ? document.body.innerText : '');
  const tabCounts = {};
  for (const m of text.matchAll(/(全部|待创建|待发货|已送货|已收货|抽检全部退回|已验收|已入库|已作废|已取消|已超时)\s*[（(]?(\d+)[）)]?/g)) {
    tabCounts[m[1]] = Number(m[2]);
  }
  const tables = Array.from(document.querySelectorAll('table'));
  const table = tables.find(t => {
    const tText = norm(t.innerText || t.textContent);
    return t.querySelectorAll('td').length > 0 && (tText.includes('备货母单号') || tText.includes('SKU 货号') || /\bWB\d+/.test(tText));
  }) || tables.find(t => {
    const tText = norm(t.innerText || t.textContent);
    return t.querySelectorAll('td').length > 0 && (tText.includes('备货单') || tText.includes('SKU') || tText.includes('备货件数'));
  });
  const rows = [];
  if (table) {
    for (const tr of Array.from(table.querySelectorAll('tr'))) {
      const cells = Array.from(tr.querySelectorAll('td')).map(td => norm(td.innerText || td.textContent));
      const rowText = norm(tr.innerText || tr.textContent);
      if (cells.length || /WB\d+|SKU 货号|货号/.test(rowText)) {
        rows.push({ text: rowText, cells });
      }
    }
  }
  const records = [];
  let current = null;
  if (table) {
    const tableRows = Array.from(table.querySelectorAll('tr')).map(tr => {
      return Array.from(tr.querySelectorAll('td')).map(td => ({
        text: norm(td.innerText || td.textContent),
        imgs: Array.from(td.querySelectorAll('img'))
          .map(img => img.currentSrc || img.src || img.getAttribute('src'))
          .filter(Boolean)
      }));
    });
    for (const cells of tableRows) {
      if (!cells.length) continue;
      const rowText = cells.map(c => c.text).join(' ');
      if (/^合计\b/.test(rowText)) continue;
      const hasProduct = rowText.includes('备货母单号:') || rowText.includes('备货母单号：') || rowText.includes('备货单号');
      const hasSku = rowText.includes('SKU 货号') || /\b(?:SZW|BO)-\d+-(?:S|M|L|XL|XXL)\b/i.test(rowText);
      if (hasProduct) {
        const productCell = cells.find(c => c.text.includes('备货母单号') || c.text.includes('商品信息')) || { text: rowText, imgs: [] };
        current = {
          beihuo_order: pick(rowText, /(WB\d+)/),
          parent_order: pick(productCell.text, /备货母单号[:：]\s*([^\s]+)/),
          product_sku: pick(productCell.text, /货号[:：]\s*([A-Za-z0-9-]+)/),
          image_url: (productCell.imgs[0] || '').split('?')[0]
        };
      }
      if (hasSku && current) {
        const skuCell = cells.find(c => c.text.includes('SKU 货号') || c.text.includes('属性')) || cells[0] || { text: '' };
        const attr = pick(skuCell.text, /属性[:：]\s*(.*?)\s*SKU(?:\s*ID|\s*货号)/) || pick(skuCell.text, /属性[:：]\s*([^\s]+)/);
        const parts = splitAttr(attr);
        const skuCode = pick(skuCell.text, /SKU\s*货号[:：]\s*([A-Za-z0-9-]+)/) || pick(rowText, /\b((?:SZW|BO)-\d+-(?:S|M|L|XL|XXL))\b/i);
        let qty = 0;
        for (const cell of cells.slice().reverse()) {
          if (/^\d{1,5}$/.test(cell.text)) {
            qty = parseQty(cell.text);
            break;
          }
        }
        if (!qty) qty = parseQty(rowText.match(/备货件数\s*(\d+)/)?.[1] || '');
        records.push({
          ...current,
          sku_attr: attr,
          color: parts.color,
          size: parts.size,
          sku_id: pick(skuCell.text, /SKU ID[:：]\s*(\d+)/),
          sku_code: skuCode,
          quantity: qty
        });
      }
    }
  }
  return { tab_counts: tabCounts, rows, records, page_text: text.slice(0, 20000), url: location.href, title: document.title };
}
"""


def _pick(text: str, patterns: tuple[str, ...]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return (match.group(1) or "").strip()
    return ""


def _parse_attr(text: str, sku_code: str) -> tuple[str, str]:
    attr = _pick(text, (r"属性[:：]\s*([^\s]+)",))
    if attr and "-" in attr:
        color, size = attr.rsplit("-", 1)
        return color.strip(), size.strip()
    if sku_code and "-" in sku_code:
        return "", sku_code.rsplit("-", 1)[-1].strip()
    return "", ""


def _parse_quantity(text: str, cells: list[str]) -> int:
    qty_text = _pick(text, (r"备货件数\s*(\d+)", r"申报件数[:：]?\s*(\d+)"))
    if qty_text:
        return int(qty_text)
    for cell in reversed(cells):
        match = re.fullmatch(r"\d{1,5}", cell.strip())
        if match:
            return int(match.group(0))
    return 0


def parse_monitor_payload(
    payload: dict[str, Any],
    shop_name: str,
    refresh_interval_seconds: int,
) -> MonitorSnapshot:
    now = datetime.now()
    orders: list[UrgencyOrder] = []
    for raw in payload.get("records") or []:
        if not isinstance(raw, dict):
            continue
        sku_code = str(raw.get("sku_code") or "")
        product_sku = str(raw.get("product_sku") or "")
        color = str(raw.get("color") or "")
        size = str(raw.get("size") or "")
        if not product_sku and sku_code and "-" in sku_code:
            product_sku = sku_code.rsplit("-", 1)[0]
            size = size or sku_code.rsplit("-", 1)[-1]
        quantity = int(raw.get("quantity") or 0)
        if not (raw.get("beihuo_order") or product_sku or sku_code):
            continue
        orders.append(
            UrgencyOrder(
                order_id=str(raw.get("beihuo_order") or "-"),
                product_sku=product_sku,
                sku_code=sku_code,
                color=color,
                size=size,
                quantity=quantity,
                age_minutes=0,
                status="待发货",
            )
        )
    fallback_rows = [] if orders else (payload.get("rows") or [])
    for raw in fallback_rows:
        if not isinstance(raw, dict):
            continue
        cells = [str(cell) for cell in (raw.get("cells") or [])]
        text = str(raw.get("text") or " ".join(cells))
        order_id = _pick(text, (r"(WB\d+)",))
        product_sku = _pick(text, (r"货号[:：]\s*([A-Za-z0-9-]+)", r"\b((?:SZW|BO)-\d+)\b"))
        sku_code = _pick(text, (r"SKU\s*货号[:：]\s*([A-Za-z0-9-]+)", r"\b((?:SZW|BO)-\d+-[A-Za-z0-9]+)\b"))
        color, size = _parse_attr(text, sku_code)
        quantity = _parse_quantity(text, cells)
        if not (order_id or product_sku or sku_code):
            continue
        candidate = UrgencyOrder(
            order_id=order_id or "-",
            product_sku=product_sku,
            sku_code=sku_code,
            color=color,
            size=size,
            quantity=quantity,
            age_minutes=0,
            status="待发货",
        )
        if candidate not in orders:
            orders.append(
                candidate
            )

    tab_counts = payload.get("tab_counts") or {}
    total_quantity = sum(order.quantity for order in orders)
    metrics = {
        "待发货": int(tab_counts.get("待发货") or len(orders)),
        "备货件数": total_quantity,
        "高优先级": len([order for order in orders if order.quantity >= 10]),
        "异常提醒": 0,
    }
    count_summary = "，".join(
        f"{name} {int(tab_counts.get(name) or 0)}"
        for name in ("全部", "待创建", "待发货", "已入库", "已作废", "已超时")
        if name in tab_counts
    )
    summary_text = count_summary or f"待发货 {metrics['待发货']}"
    events = (
        MonitorEvent(
            now.strftime("%H:%M:%S"),
            "ok",
            f"YUHOOBO 页面读取完成：{summary_text}，解析明细 {len(orders)} 条",
        ),
    )
    return MonitorSnapshot(
        shop_name=shop_name,
        region="全球",
        fetched_at=now,
        refresh_interval_seconds=refresh_interval_seconds,
        metrics=metrics,
        orders=tuple(orders),
        events=events,
        source_status="Temu 实时页面",
    )


class TemuMonitorSource:
    def __init__(
        self,
        account: ShopAccount,
        cdp_endpoint: str = "http://127.0.0.1:9222",
        refresh_interval_seconds: int = 5,
    ) -> None:
        self.account = account
        self.cdp_endpoint = cdp_endpoint
        self.refresh_interval_seconds = refresh_interval_seconds
        self._playwright = None
        self._browser = None
        self._context = None
        self._owns_context = False

    def fetch(self) -> MonitorSnapshot:
        page = self._ensure_page()
        text = self._body_text(page)
        if should_navigate_to_target(page.url, text):
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_load_state("domcontentloaded", timeout=15000)
        page = self._ensure_ready_for_read(page)
        page = self._ensure_target_shop(page)
        self._open_pending_ship_tab(page)
        self._ensure_page_size_100(page)
        self._wait_for_monitor_content(page)
        payload = page.evaluate(EXTRACT_MONITOR_SCRIPT)
        return parse_monitor_payload(payload, self.account.shop_name or "YUHOOBO", self.refresh_interval_seconds)

    def close(self) -> None:
        try:
            if self._owns_context and self._context is not None:
                self._context.close()
        finally:
            if self._playwright is not None:
                self._playwright.stop()
                self._playwright = None
            self._context = None
            self._browser = None
            self._owns_context = False

    def close_monitor_pages(self) -> int:
        if getattr(self, "_context", None) is None:
            if self._playwright is None:
                from playwright.sync_api import sync_playwright

                self._playwright = sync_playwright().start()
            try:
                self._browser = self._playwright.chromium.connect_over_cdp(self.cdp_endpoint)
                self._context = self._browser.contexts[0] if self._browser.contexts else None
            except Exception:
                return 0
        if self._context is None:
            return 0
        closed_count = 0
        for page in list(self._context.pages):
            parsed = urlparse(getattr(page, "url", "") or "")
            if parsed.netloc.lower() != "agentseller.temu.com":
                continue
            if parsed.path.lower() != "/stock/fully-mgt/order-manage-urgency":
                continue
            try:
                page.close()
                closed_count += 1
            except Exception:
                continue
        return closed_count

    def _ensure_page(self):
        if self._playwright is None:
            from playwright.sync_api import sync_playwright

            self._playwright = sync_playwright().start()
        if self._context is None:
            try:
                self._browser = self._playwright.chromium.connect_over_cdp(self.cdp_endpoint)
                self._context = self._browser.contexts[0] if self._browser.contexts else self._browser.new_context()
            except Exception:
                self._launch_chrome_for_cdp()
                self._browser = self._playwright.chromium.connect_over_cdp(self.cdp_endpoint)
                self._context = self._browser.contexts[0] if self._browser.contexts else self._browser.new_context()
            self._owns_context = False
        pages = list(self._context.pages)
        return self._preferred_page() or (pages[0] if pages else self._context.new_page())

    def _launch_chrome_for_cdp(self) -> None:
        endpoint = urlparse(self.cdp_endpoint)
        port = endpoint.port or 9222
        chrome = self._chrome_executable()
        if not chrome:
            raise RuntimeError("未找到 Chrome，无法启动监控浏览器")
        extension_dir = self._extension_dir()
        args = [
            chrome,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={self._profile_dir()}",
            "--no-first-run",
            "--disable-blink-features=AutomationControlled",
            f"--disable-extensions-except={extension_dir}",
            f"--load-extension={extension_dir}",
            TARGET_URL,
        ]
        subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0),
        )
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                with urlopen(self.cdp_endpoint.rstrip("/") + "/json/version", timeout=1):
                    return
            except Exception:
                time.sleep(0.5)
        raise RuntimeError("已启动 Chrome，但调试端口暂时无法连接")

    def _chrome_executable(self) -> str:
        candidates = [
            Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
            Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
            Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe",
        ]
        for path in candidates:
            if path.exists():
                return str(path)
        return ""

    def _ensure_ready_for_read(self, page):
        deadline = datetime.now().timestamp() + 120
        login_attempted = False
        last_state = "unknown"
        while datetime.now().timestamp() < deadline:
            page = self._preferred_page(page) or page
            text = self._body_text(page)
            state = self._page_state(page, text)
            last_state = state
            if state == "business":
                return page
            if state == "auth_gateway":
                page = self._click_china_seller_center(page)
            elif state == "login":
                if not (self.account.phone and self.account.password):
                    raise LoginRequiredError("需要登录，但未配置 YUHOOBO 账号密码")
                if is_authorization_confirm_text(text):
                    self._confirm_authorization(page)
                elif not login_attempted:
                    page = self._try_fill_login(page)
                    login_attempted = True
                else:
                    page.wait_for_timeout(1500)
            else:
                page.wait_for_timeout(1500)
        if login_attempted or last_state == "login":
            raise LoginRequiredError("已尝试登录，浏览器仍等待验证码、短信、滑块或授权确认；请在浏览器完成后再点立即刷新")
        raise LoginRequiredError("目标页尚未加载出业务内容；请确认浏览器是否停在登录、授权或空白加载页")

    def _body_text(self, page) -> str:
        try:
            return page.locator("body").inner_text(timeout=5000)
        except Exception:
            return ""

    def _wait_for_monitor_content(self, page) -> None:
        deadline = datetime.now().timestamp() + 30
        while datetime.now().timestamp() < deadline:
            text = self._body_text(page)
            clean = text.replace(" ", "")
            has_tabs = bool(re.search(r"(全部|待发货)[（(]?\d+[）)]?", text))
            has_finished = "暂无数据" in text or "共有" in text or bool(re.search(r"\bWB\d+", text))
            if has_tabs and has_finished and "加载中" not in clean:
                return
            page.wait_for_timeout(1000)

    def _open_pending_ship_tab(self, page) -> None:
        try:
            clicked = page.evaluate(
                r"""
() => {
  const visible = el => {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
  };
  const candidates = Array.from(document.querySelectorAll('div, span, button, [role="tab"]')).filter(el => {
    if (!visible(el)) return false;
    const text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
    const rect = el.getBoundingClientRect();
    return /^待发货[（(]?\d+[）)]?$/.test(text) && rect.y > 100;
  }).sort((a, b) => a.getBoundingClientRect().y - b.getBoundingClientRect().y);
  const target = candidates[0];
  if (!target) return false;
  target.scrollIntoView({block: 'center', inline: 'center'});
  target.click();
  return true;
}
"""
            )
            if clicked:
                page.wait_for_timeout(1500)
        except Exception:
            return

    def _ensure_page_size_100(self, page) -> None:
        if self._set_page_size_100(page):
            return
        try:
            changed = page.evaluate(
                r"""
() => {
  const norm = s => (s || '').replace(/\s+/g, ' ').trim();
  const bodyText = norm(document.body ? document.body.innerText : '');
  if (/每页\s*100\s*条/.test(bodyText)) return false;

  const visible = el => {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
  };

  for (const select of Array.from(document.querySelectorAll('select'))) {
    if (!visible(select)) continue;
    const option = Array.from(select.options || []).find(item => norm(item.textContent) === '100' || norm(item.textContent) === '100 条');
    if (!option) continue;
    select.value = option.value;
    select.dispatchEvent(new Event('input', {bubbles: true}));
    select.dispatchEvent(new Event('change', {bubbles: true}));
    return true;
  }

  const controls = Array.from(document.querySelectorAll('button,[role="button"],div,span')).filter(el => {
    if (!visible(el)) return false;
    const text = norm(el.innerText || el.textContent);
    const rect = el.getBoundingClientRect();
    return rect.y > window.innerHeight * 0.45 && (/每页/.test(text) || /^10$|^20$|^50$|^100$/.test(text));
  }).sort((a, b) => b.getBoundingClientRect().y - a.getBoundingClientRect().y);

  const trigger = controls.find(el => /每页/.test(norm(el.innerText || el.textContent))) || controls[0];
  if (!trigger) return false;
  trigger.click();
  return true;
}
"""
            )
            if changed:
                page.wait_for_timeout(700)
                page.evaluate(
                    r"""
() => {
  const norm = s => (s || '').replace(/\s+/g, ' ').trim();
  const visible = el => {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
  };
  const options = Array.from(document.querySelectorAll('li,div,span,button,[role="option"],[role="menuitem"]')).filter(el => {
    if (!visible(el)) return false;
    const text = norm(el.innerText || el.textContent);
    return text === '100' || text === '100 条';
  }).sort((a, b) => {
    const ar = a.getBoundingClientRect();
    const br = b.getBoundingClientRect();
    return (br.y - ar.y) || ((ar.width * ar.height) - (br.width * br.height));
  });
  const target = options[0];
  if (!target) return false;
  target.click();
  return true;
}
"""
                )
                page.wait_for_timeout(1500)
        except Exception:
            return

    def _set_page_size_100(self, page) -> bool:
        try:
            already_100 = page.evaluate(
                r"""
() => {
  const norm = s => (s || '').replace(/\s+/g, ' ').trim();
  const isPageSize100 = text => {
    const clean = norm(text);
    if (!clean) return false;
    const everyPage = String.fromCharCode(0x6bcf, 0x9875);
    const item = String.fromCharCode(0x6761);
    const page = String.fromCharCode(0x9875);
    return new RegExp(everyPage + '\\s*100\\s*' + item).test(clean)
      || new RegExp('100\\s*' + item + '\\s*/\\s*' + page).test(clean)
      || new RegExp('100\\s*/\\s*page', 'i').test(clean)
      || clean === '100';
  };
  const visible = el => {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
  };
  const bodyText = norm(document.body ? document.body.innerText : '');
  if (isPageSize100(bodyText)) return true;
  return Array.from(document.querySelectorAll('button,[role="button"],div,span,select')).some(el => {
    if (!visible(el)) return false;
    const rect = el.getBoundingClientRect();
    if (rect.y < window.innerHeight * 0.45) return false;
    return isPageSize100(el.innerText || el.textContent || el.value || '');
  });
}
"""
            )
            if already_100:
                return True
            changed = page.evaluate(
                r"""
() => {
  const norm = s => (s || '').replace(/\s+/g, ' ').trim();
  window.scrollTo({top: document.body ? document.body.scrollHeight : 0, behavior: 'instant'});

  const visible = el => {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
  };
  const clickableParent = el => {
    let node = el;
    for (let depth = 0; node && node !== document.body && depth < 8; depth += 1, node = node.parentElement) {
      if (!visible(node)) continue;
      const role = node.getAttribute('role') || '';
      const aria = node.getAttribute('aria-haspopup') || '';
      const cls = String(node.className || '').toLowerCase();
      const style = getComputedStyle(node);
      if (
        node.tagName === 'BUTTON'
        || node.tagName === 'SELECT'
        || role === 'button'
        || role === 'combobox'
        || aria === 'listbox'
        || aria === 'menu'
        || style.cursor === 'pointer'
        || cls.includes('select')
        || cls.includes('dropdown')
        || cls.includes('pagination')
      ) {
        return node;
      }
    }
    return el;
  };
  const fireClick = el => {
    const target = clickableParent(el);
    target.scrollIntoView({block: 'center', inline: 'center'});
    for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
      target.dispatchEvent(new MouseEvent(type, {bubbles: true, cancelable: true, view: window}));
    }
    return true;
  };
  const scoreBottomRight = el => {
    const rect = el.getBoundingClientRect();
    return Math.abs(window.innerWidth - rect.right) + Math.abs(window.innerHeight - rect.bottom);
  };
  const pageText = String.fromCharCode(0x6bcf, 0x9875);
  const itemText = String.fromCharCode(0x6761);
  const pageChar = String.fromCharCode(0x9875);
  const isPageSize100 = text => {
    const clean = norm(text);
    return clean === '100'
      || clean === '100 ' + itemText
      || new RegExp('100\\s*' + itemText + '\\s*/\\s*' + pageChar).test(clean)
      || /100\s*\/\s*page/i.test(clean)
      || new RegExp(pageText + '\\s*100\\s*' + itemText).test(clean);
  };
  const findBeastPageSizeTrigger = () => {
    const paginationRoots = Array.from(document.querySelectorAll('div,ul,li')).filter(el => {
      if (!visible(el)) return false;
      const rect = el.getBoundingClientRect();
      const text = norm(el.innerText || el.textContent);
      const cls = String(el.className || '');
      return rect.y > window.innerHeight * 0.45
        && (
          cls.includes('pagination')
          || cls.includes('sticky-table-bottom')
          || text.includes(pageText)
          || text.includes(itemText)
        );
    }).sort((a, b) => scoreBottomRight(a) - scoreBottomRight(b));
    const root = paginationRoots[0] || document;
    const selectors = [
      '[data-testid="beast-core-select"]',
      '[data-testid="beast-core-select-header"]',
      '[class*="PGT_sizeSelect"]',
      '[class*="PGT_sizeChanger"] [data-testid="beast-core-select"]',
      '[class*="PGT_sizeChanger"] [data-testid="beast-core-select-header"]'
    ];
    for (const selector of selectors) {
      const candidates = Array.from(root.querySelectorAll(selector)).filter(el => {
        if (!visible(el)) return false;
        const rect = el.getBoundingClientRect();
        return rect.y > window.innerHeight * 0.45;
      }).sort((a, b) => scoreBottomRight(a) - scoreBottomRight(b));
      const candidate = candidates[0];
      if (!candidate) continue;
      return candidate.querySelector('[data-testid="beast-core-select-header"]') || candidate;
    }
    return null;
  };
  const findPageSizeTrigger = () => {
    const controls = Array.from(document.querySelectorAll('button,[role="button"],div,span,[aria-haspopup="listbox"],[aria-haspopup="menu"]')).filter(el => {
      if (!visible(el)) return false;
      const text = norm(el.innerText || el.textContent);
      const rect = el.getBoundingClientRect();
      const paginationText = text.includes(pageText)
        || text.includes(itemText + '/' + pageChar)
        || /10|20|50|100/.test(text);
      return rect.y > window.innerHeight * 0.45 && paginationText;
    }).sort((a, b) => scoreBottomRight(a) - scoreBottomRight(b));
    return controls.find(el => {
      const text = norm(el.innerText || el.textContent);
      return text.includes(pageText) || text.includes(itemText + '/' + pageChar) || /\b(10|20|50|100)\b/.test(text);
    }) || controls[0];
  };

  for (const select of Array.from(document.querySelectorAll('select'))) {
    if (!visible(select)) continue;
    const option = Array.from(select.options || []).find(item => {
      const text = norm(item.textContent);
      return isPageSize100(text);
    });
    if (!option) continue;
    select.value = option.value;
    select.dispatchEvent(new Event('input', {bubbles: true}));
    select.dispatchEvent(new Event('change', {bubbles: true}));
    return true;
  }

  const trigger = findBeastPageSizeTrigger() || findPageSizeTrigger();
  if (!trigger) return false;
  return fireClick(trigger);
}
"""
            )
            if not changed:
                return True
            page.wait_for_timeout(700)
            page.evaluate(
                r"""
() => {
  const norm = s => (s || '').replace(/\s+/g, ' ').trim();
  const visible = el => {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
  };
  const clickableParent = el => {
    let node = el;
    for (let depth = 0; node && node !== document.body && depth < 6; depth += 1, node = node.parentElement) {
      if (!visible(node)) continue;
      const role = node.getAttribute('role') || '';
      const cls = String(node.className || '').toLowerCase();
      const style = getComputedStyle(node);
      if (node.tagName === 'LI' || node.tagName === 'BUTTON' || role === 'option' || role === 'menuitem' || style.cursor === 'pointer' || cls.includes('option') || cls.includes('item')) {
        return node;
      }
    }
    return el;
  };
  const fireClick = el => {
    const target = clickableParent(el);
    for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
      target.dispatchEvent(new MouseEvent(type, {bubbles: true, cancelable: true, view: window}));
    }
    return true;
  };
  const item100 = '100 ' + String.fromCharCode(0x6761);
  const itemPerPage100 = '100' + String.fromCharCode(0x6761, 0x002f, 0x9875);
  const optionSelectors = [
    '[data-testid="beast-core-portal"] li[role="option"]',
    '[data-testid="beast-core-portal"] [role="option"]',
    '[data-testid="beast-core-portal"] li',
    'li[role="option"]',
    'li,div,span,button,[role="option"],[role="menuitem"]'
  ];
  let options = [];
  for (const selector of optionSelectors) {
    options = Array.from(document.querySelectorAll(selector)).filter(el => {
      if (!visible(el)) return false;
      const text = norm(el.innerText || el.textContent);
      return text === '100' || text === item100 || text === itemPerPage100 || /100\s*\/\s*page/i.test(text);
    });
    if (options.length) break;
  }
  options = options.sort((a, b) => {
    const ar = a.getBoundingClientRect();
    const br = b.getBoundingClientRect();
    return (br.y - ar.y) || ((ar.width * ar.height) - (br.width * br.height));
  });
  const target = options[0];
  if (!target) return false;
  return fireClick(target);
}
"""
            )
            page.wait_for_timeout(1500)
            return bool(
                page.evaluate(
                    r"""
() => {
  const norm = s => (s || '').replace(/\s+/g, ' ').trim();
  const everyPage = String.fromCharCode(0x6bcf, 0x9875);
  const item = String.fromCharCode(0x6761);
  const page = String.fromCharCode(0x9875);
  const isPageSize100 = text => {
    const clean = norm(text);
    return new RegExp(everyPage + '\\s*100\\s*' + item).test(clean)
      || new RegExp('100\\s*' + item + '\\s*/\\s*' + page).test(clean)
      || /100\s*\/\s*page/i.test(clean)
      || clean === '100';
  };
  const visible = el => {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
  };
  return Array.from(document.querySelectorAll('[data-testid="beast-core-select"],[data-testid="beast-core-select-header"],[class*="PGT_sizeSelect"],button,[role="button"],div,span,select')).some(el => {
    if (!visible(el)) return false;
    const rect = el.getBoundingClientRect();
    if (rect.y < window.innerHeight * 0.45) return false;
    return isPageSize100(el.innerText || el.textContent || el.value || '');
  });
}
"""
                )
            )
        except Exception:
            return False

    def _ensure_target_shop(self, page):
        target_shop = _shop_token(self.account.shop_name or "YUHOOBO")
        current_shop = self._current_shop_name(page)
        if not current_shop or current_shop == target_shop:
            return page
        self._open_shop_menu(page, current_shop)
        self._select_shop(page, target_shop)
        try:
            page.wait_for_load_state("domcontentloaded", timeout=8000)
        except Exception:
            pass
        page.wait_for_timeout(2000)
        page = self._preferred_page(page) or page
        current_after = self._current_shop_name(page)
        if current_after != target_shop:
            raise ShopSwitchError(f"当前店铺是 {current_after or current_shop}，未能切换到 {target_shop}")
        return page

    def _current_shop_name(self, page) -> str:
        try:
            elements = page.evaluate(
                r"""
() => Array.from(document.querySelectorAll('button,[role="button"],div,span,a')).map(el => {
  const text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
  const rect = el.getBoundingClientRect();
  const style = getComputedStyle(el);
  return {text, x: rect.x, y: rect.y, w: rect.width, h: rect.height, display: style.display, visibility: style.visibility};
}).filter(item => item.text && item.w > 0 && item.h > 0 && item.display !== 'none' && item.visibility !== 'hidden')
"""
            )
        except Exception:
            return ""
        return choose_current_shop_name(elements, monitor_shop_names(self.account.shop_name or "YUHOOBO"))

    def _open_shop_menu(self, page, current_shop: str) -> None:
        clicked = self._click_shop_by_script(page, current_shop, True)
        if clicked:
            page.wait_for_timeout(1000)
            return
        elements = self._shop_elements(page)
        point = choose_shop_click_point(elements, current_shop)
        if point:
            page.mouse.click(point[0], point[1])
            page.wait_for_timeout(1000)
            return
        raise ShopSwitchError(f"页面当前店铺为 {current_shop}，但未找到店铺切换入口")

    def _select_shop(self, page, target_shop: str) -> None:
        deadline = datetime.now().timestamp() + 12
        while datetime.now().timestamp() < deadline:
            if self._click_target_shop_switch(page, target_shop):
                page.wait_for_timeout(1500)
                return
            if self._click_first_switch_entry(page):
                page.wait_for_timeout(1000)
                continue
            point = choose_target_shop_switch_point(self._shop_elements(page), target_shop)
            if point:
                page.mouse.click(point[0], point[1])
                page.wait_for_timeout(1500)
                return
            page.wait_for_timeout(500)
        raise ShopSwitchError(f"已打开店铺菜单，但未找到 {target_shop} 选项")

    def _click_first_switch_entry(self, page) -> bool:
        try:
            return bool(
                page.evaluate(
                    r"""
() => {
  const visible = el => {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
  };
  const candidates = Array.from(document.querySelectorAll('button, [role="button"], div')).filter(el => {
    const text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
    const rect = el.getBoundingClientRect();
    return visible(el) && text === '切换' && rect.y > 60;
  }).sort((a, b) => a.getBoundingClientRect().y - b.getBoundingClientRect().y);
  const target = candidates[0];
  if (!target) return false;
  target.click();
  return true;
}
"""
                )
            )
        except Exception:
            return False

    def _click_target_shop_switch(self, page, target_shop: str) -> bool:
        try:
            return bool(
                page.evaluate(
                    r"""
targetShop => {
  const wanted = String(targetShop || '').toUpperCase().replace(/[^A-Z0-9_-]+/g, '');
  const clean = value => String(value || '').toUpperCase().replace(/[^A-Z0-9_-]+/g, '');
  const visible = el => {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
  };
  const rows = Array.from(document.querySelectorAll('div, li')).filter(el => {
    if (!visible(el)) return false;
    const rawText = el.innerText || el.textContent;
    const text = clean(rawText);
    const rect = el.getBoundingClientRect();
    return rect.y > 120 && text.includes(wanted) && String(rawText || '').includes('切换');
  }).sort((a, b) => {
    const ar = a.getBoundingClientRect();
    const br = b.getBoundingClientRect();
    return (ar.width * ar.height) - (br.width * br.height);
  });
  for (const row of rows) {
    const buttons = Array.from(row.querySelectorAll('button, [role="button"], div')).filter(el => {
      if (!visible(el)) return false;
      const text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
      const disabled = el.disabled || el.getAttribute('aria-disabled') === 'true' || String(el.className || '').includes('disabled');
      return text === '切换' && !disabled;
    });
    const button = buttons[0];
    if (button) {
      button.click();
      return true;
    }
  }
  return false;
}
""",
                    target_shop,
                )
            )
        except Exception:
            return False

    def _shop_elements(self, page) -> list[dict[str, Any]]:
        try:
            return page.evaluate(
                r"""
() => Array.from(document.querySelectorAll('button,[role="button"],div,span,a')).map(el => {
  const text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
  const rect = el.getBoundingClientRect();
  return {text, x: rect.x, y: rect.y, w: rect.width, h: rect.height};
}).filter(item => item.text && item.w > 0 && item.h > 0)
"""
            )
        except Exception:
            return []

    def _click_shop_by_script(self, page, shop_name: str, header_only: bool) -> bool:
        return bool(
            page.evaluate(
                r"""
({shopName, headerOnly}) => {
  const wanted = String(shopName || '').toUpperCase().replace(/[^A-Z0-9_-]+/g, '');
  const clean = value => String(value || '').toUpperCase().replace(/[^A-Z0-9_-]+/g, '');
  const visible = el => {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
  };
  const clickable = el => {
    let node = el;
    for (let i = 0; node && node !== document.body && i < 6; i += 1, node = node.parentElement) {
      const rect = node.getBoundingClientRect();
      const style = getComputedStyle(node);
      const role = node.getAttribute('role') || '';
      if (rect.width <= 0 || rect.height <= 0) continue;
      if (node.tagName === 'BUTTON' || node.tagName === 'A' || role === 'button' || style.cursor === 'pointer' || typeof node.onclick === 'function') {
        return node;
      }
    }
    return el;
  };
  const matches = Array.from(document.querySelectorAll('button,[role="button"],div,span,a')).filter(el => {
    if (!visible(el)) return false;
    const rect = el.getBoundingClientRect();
    if (headerOnly && rect.y > 120) return false;
    const text = clean(el.innerText || el.textContent);
    return text && text.includes(wanted);
  }).sort((a, b) => {
    const ar = a.getBoundingClientRect();
    const br = b.getBoundingClientRect();
    return (Math.abs(ar.y - 24) + (ar.width * ar.height) / 10000 + clean(a.innerText || a.textContent).length / 20)
      - (Math.abs(br.y - 24) + (br.width * br.height) / 10000 + clean(b.innerText || b.textContent).length / 20);
  });
  const target = matches[0];
  if (!target) return false;
  const node = clickable(target);
  node.scrollIntoView({block: 'center', inline: 'center'});
  node.click();
  return true;
}
""",
                {"shopName": shop_name, "headerOnly": header_only},
            )
        )

    def _page_state(self, page, text: str) -> str:
        if is_business_page_text(text):
            return "business"
        plugin_state = self._plugin_state(page)
        if isinstance(plugin_state, dict):
            sample = str(plugin_state.get("textSample") or "")
            if is_business_page_text(sample):
                return "business"
            if plugin_state.get("isLoginLike"):
                return "login"
        if is_login_page_text(text):
            return "login"
        if is_auth_gateway_text(text):
            return "auth_gateway"
        return "unknown"

    def _plugin_state(self, page):
        try:
            return page.evaluate("() => window.__CONSOLEPLAT_MONITOR__ || null")
        except Exception:
            return None

    def _try_fill_login(self, page):
        page = self._wait_for_login_form_page(page, timeout_ms=15000)
        if page is None:
            raise LoginRequiredError("已进入登录页，但登录输入框尚未加载完成；请稍后重试或手动完成登录")
        password_selectors = [
            "input[type='password']",
            "input[name*='password']",
            "input[placeholder*='密码']",
        ]
        self._fill_first(page, phone_login_selectors(), self.account.phone)
        self._fill_first(page, password_selectors, self.account.password)
        self._check_authorization_box(page)
        self._click_login_submit(page)
        page.wait_for_timeout(2500)
        return page

    def _wait_until_business_or_login(self, page, timeout_ms: int):
        deadline = datetime.now().timestamp() + timeout_ms / 1000
        while datetime.now().timestamp() < deadline:
            page = self._preferred_page(page) or page
            text = self._body_text(page)
            state = self._page_state(page, text)
            if state == "business":
                return page
            if state == "auth_gateway":
                page = self._click_china_seller_center(page)
            if state == "login" and not self._has_login_form(page):
                self._click_auth_if_present(page)
            try:
                if "order-manage-urgency" not in page.url and "login" not in page.url.lower():
                    page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=10000)
            except Exception:
                pass
            page.wait_for_timeout(1500)
        return None

    def _preferred_page(self, fallback=None):
        if self._context is None:
            return fallback
        pages = list(self._context.pages)
        index = choose_preferred_page([page.url for page in pages])
        if index is None:
            return fallback
        page = pages[index]
        try:
            page.bring_to_front()
        except Exception:
            pass
        return page

    def _click_auth_if_present(self, page) -> None:
        for label in ("确认授权并前往", "授权登录"):
            try:
                page.get_by_text(label, exact=False).first.click(timeout=800)
                return
            except Exception:
                continue

    def _confirm_authorization(self, page) -> None:
        self._check_authorization_box(page)
        try:
            clicked = page.evaluate(
                r"""
() => {
  const buttons = Array.from(document.querySelectorAll('button, [role="button"]'));
  const target = buttons.find(el => {
    const text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
    const rect = el.getBoundingClientRect();
    return text === '确认授权并前往' && rect.width > 120 && rect.height > 30 && !el.disabled;
  });
  if (!target) return false;
  target.click();
  return true;
}
"""
            )
            if clicked:
                page.wait_for_timeout(2500)
                return
        except Exception:
            pass
        try:
            page.get_by_text("确认授权并前往", exact=True).first.click(timeout=2000)
            page.wait_for_timeout(2500)
        except Exception as exc:
            raise LoginRequiredError("已进入授权确认页，但未能点击确认授权并前往") from exc

    def _click_login_submit(self, page) -> None:
        try:
            clicked = page.evaluate(
                r"""
() => {
  const buttons = Array.from(document.querySelectorAll('button, [role="button"]'));
  const target = buttons.find(el => {
    const text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
    const rect = el.getBoundingClientRect();
    return text === '授权登录' && rect.width > 120 && rect.height > 30 && !el.disabled;
  });
  if (!target) return false;
  target.click();
  return true;
}
"""
            )
            if clicked:
                return
        except Exception:
            pass
        for label in login_submit_labels():
            selectors = (
                f"button:has-text('{label}')",
                f"[role='button']:has-text('{label}')",
            )
            for selector in selectors:
                try:
                    locator = page.locator(selector).first
                    if locator.count():
                        locator.click(timeout=2000)
                        return
                except Exception:
                    continue
        for label in login_submit_labels():
            try:
                page.get_by_text(label, exact=True).first.click(timeout=1500)
                return
            except Exception:
                continue
        raise LoginRequiredError("已填写登录信息，但未能点击登录按钮；请手动确认登录页")

    def _click_china_seller_center(self, page):
        before_pages = list(self._context.pages) if self._context is not None else []
        before_urls = [item.url for item in before_pages]
        try:
            clicked = page.evaluate(
                r"""
() => {
  const candidates = Array.from(document.querySelectorAll('*')).filter(el => {
    const text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return text === '商家中心'
      && rect.width > 0
      && rect.height > 0
      && (style.cursor === 'pointer' || typeof el.onclick === 'function');
  });
  const target = candidates[candidates.length - 1];
  if (!target) return false;
  target.scrollIntoView({block: 'center', inline: 'center'});
  target.click();
  return true;
}
"""
            )
            if clicked:
                page.wait_for_timeout(3000)
                return self._page_opened_after(before_urls) or self._preferred_page(page) or page
        except Exception:
            pass
        point = self._auth_gateway_click_point(page)
        if point:
            page.mouse.click(point[0], point[1])
            page.wait_for_timeout(2500)
            return self._page_opened_after(before_urls) or self._preferred_page(page) or page
        candidates = (
            "text=商家中心",
            "a:has-text('商家中心')",
            "button:has-text('商家中心')",
            "div:has-text('中国地区') >> text=商家中心",
        )
        for selector in candidates:
            try:
                page.locator(selector).first.click(timeout=2000)
                page.wait_for_timeout(2500)
                return self._page_opened_after(before_urls) or self._preferred_page(page) or page
            except Exception:
                continue
        raise LoginRequiredError("已进入地区选择页，但未能点击中国地区商家中心入口")

    def _page_opened_after(self, before_urls: list[str]):
        if self._context is None:
            return None
        pages = list(self._context.pages)
        index = choose_new_page(before_urls, [page.url for page in pages])
        if index is None:
            return None
        page = pages[index]
        try:
            page.bring_to_front()
        except Exception:
            pass
        return page

    def _auth_gateway_click_point(self, page) -> tuple[int, int] | None:
        try:
            elements = page.evaluate(
                """() => Array.from(document.querySelectorAll('*')).map(el => {
                  const text = (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
                  const rect = el.getBoundingClientRect();
                  return {text, x: rect.x, y: rect.y, w: rect.width, h: rect.height};
                }).filter(item => item.text.includes('商家中心'))"""
            )
        except Exception:
            return None
        return choose_auth_gateway_click_point(elements)

    def _fill_first(self, page, selectors: list[str], value: str) -> None:
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                locator.fill(value, timeout=1500)
                return
            except Exception:
                continue
        raise RuntimeError("登录页输入框定位失败，请检查页面结构")

    def _has_login_form(self, page) -> bool:
        try:
            return page.locator("input[type='password'], input[name='usernameId']").count() > 0
        except Exception:
            return False

    def _wait_for_login_form_page(self, current_page, timeout_ms: int):
        deadline = datetime.now().timestamp() + timeout_ms / 1000
        while datetime.now().timestamp() < deadline:
            pages = list(self._context.pages) if self._context is not None else [current_page]
            for page in reversed(pages):
                if self._has_login_form(page):
                    try:
                        page.bring_to_front()
                    except Exception:
                        pass
                    return page
            try:
                current_page.wait_for_timeout(500)
            except Exception:
                pass
        return None

    def _check_authorization_box(self, page) -> None:
        if self._is_policy_checked(page):
            return
        point = self._policy_click_point(page)
        if point:
            try:
                page.mouse.click(point[0], point[1])
                page.wait_for_timeout(300)
                if self._is_policy_checked(page):
                    return
            except Exception:
                pass
        try:
            checkbox = page.locator("input[type='checkbox']").first
            if checkbox.count() and not checkbox.is_checked(timeout=800):
                checkbox.check(timeout=1200, force=True)
                if self._is_policy_checked(page):
                    return
        except Exception:
            pass
        try:
            page.evaluate(
                r"""
() => {
  const input = document.querySelector("input[type='checkbox']");
  if (!input) return false;
  input.checked = true;
  input.dispatchEvent(new Event('input', {bubbles: true}));
  input.dispatchEvent(new Event('change', {bubbles: true}));
  return input.checked;
}
"""
            )
        except Exception:
            pass

    def _is_policy_checked(self, page) -> bool:
        try:
            return bool(page.locator("input[type='checkbox']").first.is_checked(timeout=500))
        except Exception:
            return False

    def _policy_click_point(self, page) -> tuple[int, int] | None:
        try:
            elements = page.evaluate(
                r"""
() => Array.from(document.querySelectorAll('label, span, div, a')).map(el => {
  const text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
  const rect = el.getBoundingClientRect();
  return {text, x: rect.x, y: rect.y, w: rect.width, h: rect.height};
}).filter(item => item.text.includes('授权您的账号ID') || item.text.includes('隐私政策'))
"""
            )
        except Exception:
            return None
        return choose_policy_click_point(elements)

    def _profile_dir(self):
        from consoleplat.paths import project_root

        path = project_root() / ".browser-profile"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _extension_dir(self) -> str:
        from consoleplat.paths import project_root

        return str(project_root() / "chrome-extension")
