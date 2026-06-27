from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Callable

from models import TemuSkuRecord


Logger = Callable[[str], None]

TARGET_URL = "https://agentseller.temu.com/stock/fully-mgt/order-manage-urgency"


EXTRACT_SCRIPT = r"""
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
  const table = Array.from(document.querySelectorAll('table')).find(t => {
    const text = norm(t.innerText || t.textContent);
    return text.includes('SKU 货号') && text.includes('备货母单号');
  });
  if (!table) return [];

  const rows = Array.from(table.querySelectorAll('tr')).map(tr => {
    return Array.from(tr.querySelectorAll('td')).map(td => ({
      text: norm(td.innerText || td.textContent),
      imgs: Array.from(td.querySelectorAll('img'))
        .map(img => img.currentSrc || img.src || img.getAttribute('src'))
        .filter(Boolean)
    }));
  });

  const out = [];
  let current = null;
  for (const cells of rows) {
    if (!cells.length) continue;
    const rowText = cells.map(c => c.text).join(' ');
    if (/^合计\b/.test(rowText)) continue;
    const hasProduct = rowText.includes('备货母单号:') || rowText.includes('备货母单号：');
    const hasSku = rowText.includes('SKU 货号');

    if (hasProduct) {
      const productCell = cells.find(c => c.text.includes('备货母单号')) || { text: '', imgs: [] };
      current = {
        beihuo_order: pick(rowText, /(WB\d+)/),
        parent_order: pick(productCell.text, /备货母单号[:：]\s*([^\s]+)/),
        product_sku: pick(productCell.text, /货号[:：]\s*([A-Za-z0-9-]+)/),
        image_url: (productCell.imgs[0] || '').split('?')[0]
      };
    }

    if (hasSku && current) {
      const skuCell = cells.find(c => c.text.includes('SKU 货号')) || cells[0] || { text: '' };
      const attr = pick(skuCell.text, /属性[:：]\s*(.*?)\s*SKU ID/);
      const parts = splitAttr(attr);
      let qty = 0;
      if (hasProduct) {
        qty = parseQty(cells[6] ? cells[6].text : '');
      } else {
        qty = parseQty(cells[2] ? cells[2].text : '');
      }
      out.push({
        ...current,
        sku_attr: attr,
        color: parts.color,
        size: parts.size,
        sku_id: pick(skuCell.text, /SKU ID[:：]\s*(\d+)/),
        sku_code: pick(skuCell.text, /SKU 货号[:：]\s*([A-Za-z0-9-]+)/),
        quantity: qty
      });
    }
  }
  return out;
}
"""


class TemuReader:
    def __init__(
        self,
        user_data_dir: str | Path = ".browser-profile",
        cdp_endpoint: str = "http://127.0.0.1:9222",
        logger: Logger | None = None,
    ) -> None:
        self.user_data_dir = Path(user_data_dir)
        self.cdp_endpoint = cdp_endpoint
        self.logger = logger or (lambda _message: None)
        self._playwright = None
        self._browser = None
        self._context = None

    def log(self, message: str) -> None:
        self.logger(message)

    def start(self) -> None:
        if self._playwright is not None:
            return
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()

    def connect_or_launch(self) -> None:
        self.start()
        if self._context is not None:
            return

        try:
            self.log(f"尝试连接 Chrome 调试端口：{self.cdp_endpoint}")
            self._browser = self._playwright.chromium.connect_over_cdp(self.cdp_endpoint)
            self._context = self._browser.contexts[0] if self._browser.contexts else self._browser.new_context()
            self.log("已连接到现有 Chrome。")
            return
        except Exception as exc:  # noqa: BLE001 - fallback is expected.
            self.log(f"未连接到调试端口，将打开独立浏览器：{exc}")

        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        launch_kwargs = {
            "user_data_dir": str(self.user_data_dir),
            "headless": False,
            "args": ["--disable-blink-features=AutomationControlled"],
        }
        try:
            self._context = self._playwright.chromium.launch_persistent_context(
                **launch_kwargs,
                channel="chrome",
            )
        except Exception as exc:  # noqa: BLE001 - Chromium fallback is intentional.
            self.log(f"标准 Chrome 启动失败，改用 Playwright 浏览器：{exc}")
            self._context = self._playwright.chromium.launch_persistent_context(**launch_kwargs)
        page = self._context.pages[0] if self._context.pages else self._context.new_page()
        page.goto(TARGET_URL, wait_until="domcontentloaded")
        self.log("已打开独立 Chrome 窗口，请登录并进入紧急备货建议页面。")

    def open_target_page(self) -> None:
        self.connect_or_launch()
        page = self._get_page(create=True)
        page.goto(TARGET_URL, wait_until="domcontentloaded")

    def collect(self, max_scrolls: int = 80, idle_rounds: int = 5) -> list[TemuSkuRecord]:
        self.connect_or_launch()
        page = self._get_page(create=False)
        if page is None:
            raise RuntimeError("没有可读取的浏览器页面，请先打开 Temu 页面。")

        page.wait_for_load_state("domcontentloaded", timeout=15000)
        if "agentseller.temu.com" not in page.url:
            self.log(f"当前页面不是 Temu 备货页：{page.url}")

        records_by_key: dict[tuple[str, str, str, str], TemuSkuRecord] = {}
        no_new_rounds = 0

        for step in range(max_scrolls):
            batch = self._extract_visible(page)
            before = len(records_by_key)
            for record in batch:
                if record.sku_code and record.quantity > 0:
                    records_by_key[record.key] = record

            added = len(records_by_key) - before
            self.log(f"第 {step + 1} 次读取：新增 {added} 条，累计 {len(records_by_key)} 条。")
            if added == 0:
                no_new_rounds += 1
            else:
                no_new_rounds = 0

            if no_new_rounds >= idle_rounds:
                break
            moved = self._scroll_table(page)
            if not moved:
                no_new_rounds += 1
            time.sleep(0.25)

        return list(records_by_key.values())

    def close(self) -> None:
        try:
            if self._context is not None:
                self._context.close()
        finally:
            self._context = None
            self._browser = None
            if self._playwright is not None:
                self._playwright.stop()
                self._playwright = None

    def _get_page(self, create: bool):
        if self._context is None:
            return None
        pages = list(self._context.pages)
        for page in pages:
            if "agentseller.temu.com/stock/fully-mgt/order-manage-urgency" in page.url:
                return page
        for page in pages:
            if "agentseller.temu.com" in page.url:
                return page
        if pages:
            return pages[-1]
        return self._context.new_page() if create else None

    def _extract_visible(self, page) -> list[TemuSkuRecord]:
        raw_records = page.evaluate(EXTRACT_SCRIPT)
        records: list[TemuSkuRecord] = []
        for item in raw_records:
            sku_code = str(item.get("sku_code") or "")
            product_sku = str(item.get("product_sku") or "")
            size = str(item.get("size") or "")
            if not product_sku and sku_code:
                product_sku, size_from_sku = split_sku_code(sku_code)
                size = size or size_from_sku
            records.append(
                TemuSkuRecord(
                    beihuo_order=str(item.get("beihuo_order") or ""),
                    parent_order=str(item.get("parent_order") or ""),
                    product_sku=product_sku,
                    sku_code=sku_code,
                    sku_id=str(item.get("sku_id") or ""),
                    color=str(item.get("color") or ""),
                    size=size,
                    quantity=int(item.get("quantity") or 0),
                    image_url=str(item.get("image_url") or ""),
                    sku_attr=str(item.get("sku_attr") or ""),
                )
            )
        return records

    def _scroll_table(self, page) -> bool:
        return bool(
            page.evaluate(
                r"""
                () => {
                  const table = Array.from(document.querySelectorAll('table')).find(t => {
                    const text = (t.innerText || t.textContent || '');
                    return text.includes('SKU 货号') && text.includes('备货母单号');
                  });
                  const candidates = [];
                  let node = table;
                  while (node) {
                    if (node.scrollHeight && node.clientHeight && node.scrollHeight > node.clientHeight + 20) {
                      candidates.push(node);
                    }
                    node = node.parentElement;
                  }
                  candidates.push(document.scrollingElement || document.documentElement);
                  let target = candidates.find(el => el.scrollHeight > el.clientHeight + 20);
                  if (!target) return false;
                  const before = target.scrollTop;
                  target.scrollTop = Math.min(target.scrollTop + Math.max(500, target.clientHeight * 0.8), target.scrollHeight);
                  window.dispatchEvent(new Event('scroll'));
                  return target.scrollTop !== before;
                }
                """
            )
        )


def split_sku_code(sku_code: str) -> tuple[str, str]:
    match = re.match(r"^(.+)-(S|M|L|XL|XXL)$", sku_code.strip(), re.IGNORECASE)
    if not match:
        return sku_code, ""
    return match.group(1), match.group(2).upper()
