from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

from consoleplat import APP_VERSION

GITHUB_OWNER = "lXFCL"
GITHUB_REPO = "ConsolePlat"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
USER_AGENT = f"ConsolePlat/{APP_VERSION} (auto-update-check)"
HTTP_TIMEOUT = 8


@dataclass
class ReleaseInfo:
    version: str
    tag_name: str
    name: str
    body: str
    html_url: str
    download_url: str
    asset_name: str
    published_at: str


@dataclass
class UpdateProxyConfig:
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 7890

    @property
    def address(self) -> str:
        host = (self.host or "").strip()
        if "://" in host:
            parsed = urlsplit(host)
            host = parsed.hostname or host
            if parsed.port:
                return f"{host}:{parsed.port}"
        host = host.rsplit(":", 1)[0] if host.count(":") == 1 and host.rsplit(":", 1)[1].isdigit() else host
        return f"{host or '127.0.0.1'}:{self.port}"

    @property
    def url(self) -> str:
        return f"http://{self.address}"

    @property
    def hint(self) -> str:
        return f"{self.address}（HTTP 代理地址，不要填 https://）"


def parse_version(text: str) -> tuple[int, ...]:
    cleaned = (text or "").strip().lstrip("vV")
    match = re.match(r"(\d+(?:\.\d+)*)", cleaned)
    if not match:
        return (0,)
    return tuple(int(part) for part in match.group(1).split("."))


def is_newer(latest: str, current: str) -> bool:
    latest_parts = parse_version(latest)
    current_parts = parse_version(current)
    length = max(len(latest_parts), len(current_parts))
    latest_parts += (0,) * (length - len(latest_parts))
    current_parts += (0,) * (length - len(current_parts))
    return latest_parts > current_parts


def _pick_asset(assets: list[dict]) -> tuple[str, str]:
    for suffix in (".exe", ".zip", ".msi"):
        for asset in assets:
            name = str(asset.get("name") or "")
            url = str(asset.get("browser_download_url") or "")
            if name.lower().endswith(suffix) and url:
                return url, name
    return "", ""


def _build_opener(proxy: UpdateProxyConfig | None = None):
    if not proxy or not proxy.enabled:
        return urllib.request.build_opener()
    return urllib.request.build_opener(
        urllib.request.ProxyHandler(
            {
                "http": proxy.url,
                "https": proxy.url,
            }
        )
    )


def fetch_latest_release(timeout: int = HTTP_TIMEOUT, proxy: UpdateProxyConfig | None = None) -> ReleaseInfo:
    request = urllib.request.Request(
        RELEASES_API,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
        },
    )
    opener = _build_opener(proxy)
    with opener.open(request, timeout=timeout) as response:  # noqa: S310 - 固定官方 HTTPS API
        payload = json.loads(response.read().decode("utf-8"))

    tag = str(payload.get("tag_name") or "")
    raw_assets = payload.get("assets") or []
    assets = raw_assets if isinstance(raw_assets, list) else []
    download_url, asset_name = _pick_asset(assets)
    html_url = str(payload.get("html_url") or RELEASES_PAGE)
    return ReleaseInfo(
        version=".".join(str(part) for part in parse_version(tag)),
        tag_name=tag,
        name=str(payload.get("name") or tag),
        body=str(payload.get("body") or ""),
        html_url=html_url,
        download_url=download_url or html_url,
        asset_name=asset_name,
        published_at=str(payload.get("published_at") or ""),
    )


def check_for_update(
    current: str = APP_VERSION,
    timeout: int = HTTP_TIMEOUT,
    proxy: UpdateProxyConfig | None = None,
) -> dict:
    try:
        release = fetch_latest_release(timeout=timeout, proxy=proxy)
    except urllib.error.HTTPError as exc:
        kind = "rate_limited" if exc.code in (403, 429) else "error"
        return {"ok": False, "kind": kind, "message": f"GitHub 返回 {exc.code}"}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        if proxy and proxy.enabled:
            return {"ok": False, "kind": "proxy_error", "message": f"代理连接失败，请检查 {proxy.hint}：{exc}"}
        return {"ok": False, "kind": "offline", "message": f"无法连接 GitHub：{exc}"}
    except (ValueError, KeyError, TypeError) as exc:
        return {"ok": False, "kind": "error", "message": f"解析 release 失败：{exc}"}

    return {
        "ok": True,
        "current_version": current,
        "has_update": is_newer(release.version, current),
        "release": {
            "version": release.version,
            "tag_name": release.tag_name,
            "name": release.name,
            "body": release.body,
            "html_url": release.html_url,
            "download_url": release.download_url,
            "asset_name": release.asset_name,
            "published_at": release.published_at,
        },
    }


def download_asset(
    url: str,
    dest_path: str | Path,
    timeout: int = 60,
    progress_cb: Callable[[int, int], None] | None = None,
    proxy: UpdateProxyConfig | None = None,
) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    dest = Path(dest_path)
    opener = _build_opener(proxy)
    with opener.open(request, timeout=timeout) as response:  # noqa: S310 - URL 来自官方 GitHub release
        total = int(response.headers.get("Content-Length") or 0)
        received = 0
        with dest.open("wb") as handle:
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                received += len(chunk)
                if progress_cb:
                    progress_cb(received, total)
    return str(dest)
