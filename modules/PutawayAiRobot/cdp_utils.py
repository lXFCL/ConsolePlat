import json
import urllib.error
import urllib.parse
import urllib.request


def _fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "PutawayAiRobot/1.0"})
    with urllib.request.urlopen(req, timeout=2) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def _request_json(url: str, method: str):
    req = urllib.request.Request(url, headers={"User-Agent": "PutawayAiRobot/1.0"}, method=method)
    with urllib.request.urlopen(req, timeout=2) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def list_cdp_pages(cdp_base_url: str):
    cdp_base_url = (cdp_base_url or "").strip().rstrip("/")
    if not cdp_base_url:
        raise RuntimeError("CDP地址为空")
    pages = _fetch_json(f"{cdp_base_url}/json")
    results = []
    for p in pages or []:
        if p.get("type") != "page":
            continue
        results.append(
            {
                "title": p.get("title") or "",
                "url": p.get("url") or "",
                "webSocketDebuggerUrl": p.get("webSocketDebuggerUrl") or "",
            }
        )
    return results


def open_cdp_page(cdp_base_url: str, page_url: str):
    cdp_base_url = (cdp_base_url or "").strip().rstrip("/")
    if not cdp_base_url:
        raise RuntimeError("CDP地址为空")
    page_url = (page_url or "").strip()
    if not page_url:
        raise RuntimeError("页面地址为空")
    q = urllib.parse.quote(page_url, safe=":/?&=#%")
    url = f"{cdp_base_url}/json/new?{q}"
    last = None
    for method in ["PUT", "GET"]:
        try:
            return _request_json(url, method)
        except urllib.error.HTTPError as e:
            last = e
            if int(getattr(e, "code", 0) or 0) in {404, 405}:
                continue
            raise
        except Exception as e:
            last = e
            continue
    raise RuntimeError(f"创建新标签页失败：{last}")


def close_cdp_page(cdp_base_url: str, page_ws: str = "", page_target_id: str = ""):
    cdp_base_url = (cdp_base_url or "").strip().rstrip("/")
    if not cdp_base_url:
        return False
    target_id = (page_target_id or "").strip()
    if not target_id:
        ws = (page_ws or "").strip()
        if "/devtools/page/" in ws:
            target_id = ws.rsplit("/devtools/page/", 1)[-1].strip()
    if not target_id:
        return False
    url = f"{cdp_base_url}/json/close/{urllib.parse.quote(target_id, safe='')}"
    for method in ["GET", "PUT"]:
        try:
            _request_json(url, method)
            return True
        except Exception:
            continue
    return False
