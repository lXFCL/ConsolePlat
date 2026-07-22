from __future__ import annotations

import argparse
import json
import random
import sys
from typing import Any
from urllib.parse import urljoin

from consoleplat.services.ai_selection_service import SelectionCandidate, parse_sales_count


TEMU_HOME_URL = "https://www.temu.com/us-zh-Hans"
MAX_PAGES = 3

EXTRACT_CARDS_SCRIPT = r"""
() => {
  const visible = element => {
    const rect = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    return rect.width > 80 && rect.height > 100 && style.display !== 'none' && style.visibility !== 'hidden';
  };
  const norm = value => String(value || '').replace(/\s+/g, ' ').trim();
  const anchors = Array.from(document.querySelectorAll('a[href]')).filter(visible);
  const items = [];
  const seen = new Set();
  for (const anchor of anchors) {
    const href = anchor.href || '';
    if (!/temu\.com/i.test(href) || !/goods/i.test(href)) continue;
    if (seen.has(href)) continue;
    const container = anchor.closest('article, [data-testid], li, div') || anchor;
    const text = norm(container.innerText || anchor.innerText || anchor.textContent);
    const image = container.querySelector('img') || anchor.querySelector('img');
    if (!text || !image) continue;
    const lines = text.split(/(?<=[.!?。！？])\s+|\n/).map(norm).filter(Boolean);
    const sales = lines.find(line => /(sold|销量|已售|售出)/i.test(line)) || '';
    const price = lines.find(line => /[$￥¥]|USD|US\$/i.test(line)) || '';
    const title = lines.find(line => line !== sales && line !== price && line.length > 4) || norm(anchor.getAttribute('aria-label')) || '未命名商品';
    seen.add(href);
    items.push({title, sales_text: sales, price, href, image_url: image.currentSrc || image.src || ''});
  }
  return items.slice(0, 200);
}
"""


def parse_search_cards(raw_cards: list[dict[str, Any]], keyword: str) -> tuple[list[SelectionCandidate], list[str]]:
    candidates: list[SelectionCandidate] = []
    failures: list[str] = []
    for raw in raw_cards:
        title = str(raw.get("title") or "未命名商品").strip()
        sales_text = str(raw.get("sales_text") or "").strip()
        sales_count = parse_sales_count(sales_text)
        if sales_count is None:
            failures.append(f"商品 {title} 未读取到销量")
            continue
        href = str(raw.get("href") or "").strip()
        if not href:
            failures.append(f"商品 {title} 未读取到链接")
            continue
        candidates.append(
            SelectionCandidate(
                title=title,
                sales_text=sales_text,
                sales_count=sales_count,
                price=str(raw.get("price") or "").strip(),
                product_url=urljoin(TEMU_HOME_URL, href),
                image_url=str(raw.get("image_url") or "").strip(),
                keyword=keyword,
            )
        )
    return candidates, failures


def should_stop_after_page(consecutive_empty_pages: int) -> bool:
    return consecutive_empty_pages >= 2


def collect_selection_payload(cdp_endpoint: str, keywords: list[str], max_pages: int = MAX_PAGES) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        return {"ok": False, "kind": "error", "message": f"缺少 Playwright：{exc}"}

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(cdp_endpoint)
            context = browser.contexts[0] if browser.contexts else None
            if context is None:
                return {"ok": False, "kind": "error", "message": "Chrome CDP 没有可用浏览器上下文"}
            page = context.pages[-1] if context.pages else context.new_page()
            all_candidates: list[SelectionCandidate] = []
            failures: list[str] = []
            logs: list[str] = []
            for keyword in [item.strip() for item in keywords if item.strip()]:
                page.goto(TEMU_HOME_URL, wait_until="domcontentloaded", timeout=30000)
                state = _blocked_state(page)
                if state:
                    return {"ok": False, "kind": state, "message": _blocked_message(state), "logs": logs}
                if not _search(page, keyword):
                    return {"ok": False, "kind": "error", "message": "未找到 Temu 搜索框，请检查页面是否已改版", "logs": logs}
                consecutive_empty_pages = 0
                for page_number in range(1, min(max(1, int(max_pages)), MAX_PAGES) + 1):
                    page.wait_for_timeout(1200)
                    state = _blocked_state(page)
                    if state:
                        return {"ok": False, "kind": state, "message": _blocked_message(state), "logs": logs}
                    raw_cards = page.evaluate(EXTRACT_CARDS_SCRIPT)
                    cards, page_failures = parse_search_cards(raw_cards or [], keyword)
                    all_candidates.extend(cards)
                    failures.extend(page_failures)
                    logs.append(f"{keyword} 第 {page_number} 页：读取 {len(raw_cards or [])} 条，销量有效 {len(cards)} 条")
                    consecutive_empty_pages = 0 if cards else consecutive_empty_pages + 1
                    if page_number >= max_pages or should_stop_after_page(consecutive_empty_pages):
                        break
                    if not _next_page(page):
                        logs.append(f"{keyword} 没有可用下一页，结束采集")
                        break
                    page.wait_for_timeout(random.randint(2, 4) * 1000)
            return {
                "ok": True,
                "candidates": [candidate.__dict__ for candidate in all_candidates],
                "failures": failures,
                "logs": logs,
            }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "kind": "error", "message": f"Temu 选品读取失败：{exc}"}


def _search(page, keyword: str) -> bool:
    selectors = (
        "input[type='search']",
        "input[placeholder*='Search']",
        "input[placeholder*='搜索']",
        "input[name*='search']",
    )
    for selector in selectors:
        try:
            field = page.locator(selector).first
            if field.count() and field.is_visible():
                field.fill(keyword, timeout=2500)
                field.press("Enter", timeout=2500)
                page.wait_for_load_state("domcontentloaded", timeout=15000)
                return True
        except Exception:
            continue
    return False


def _next_page(page) -> bool:
    for selector in ("button[aria-label*='Next']", "button[aria-label*='下一页']", "a[aria-label*='Next']"):
        try:
            control = page.locator(selector).first
            if control.count() and control.is_visible() and control.is_enabled():
                control.click(timeout=2500)
                return True
        except Exception:
            continue
    for label in ("Next", "下一页"):
        try:
            control = page.get_by_text(label, exact=True).first
            if control.count() and control.is_visible():
                control.click(timeout=2500)
                return True
        except Exception:
            continue
    return False


def _blocked_state(page) -> str:
    text = str(page.locator("body").inner_text(timeout=2000) or "").replace(" ", "")
    if any(marker in text for marker in ("验证码", "人机验证", "安全验证", "CAPTCHA")):
        return "captcha"
    if any(marker in text for marker in ("登录", "SignIn", "LogIn")) and "搜索" not in text:
        return "login"
    return ""


def _blocked_message(kind: str) -> str:
    return "Temu 页面需要人工完成验证码" if kind == "captcha" else "请先在已打开的 Chrome 中完成 Temu 登录"


def main() -> int:
    parser = argparse.ArgumentParser(description="ConsolePlat AI selection read-only collector")
    parser.add_argument("--cdp-endpoint", default="http://127.0.0.1:9222")
    parser.add_argument("--keywords", nargs="+", default=["黑白T恤"])
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES)
    args = parser.parse_args()
    payload = collect_selection_payload(args.cdp_endpoint, args.keywords, args.max_pages)
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
