from __future__ import annotations

import json
import urllib.error

import pytest

from consoleplat.services.version_check_service import (
    UpdateProxyConfig,
    _build_opener,
    _pick_asset,
    check_for_update,
    is_newer,
    parse_version,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("v1.4.1", (1, 4, 1)),
        ("1.10", (1, 10)),
        ("1.5.0-beta", (1, 5, 0)),
        ("garbage", (0,)),
        ("", (0,)),
    ],
)
def test_parse_version(text, expected):
    assert parse_version(text) == expected


@pytest.mark.parametrize(
    "latest,current,expected",
    [
        ("1.5.0", "1.4.1", True),
        ("1.10.0", "1.9.0", True),
        ("1.4.1", "1.4.1", False),
        ("1.4.0", "1.4.1", False),
        ("2.0", "1.99.99", True),
    ],
)
def test_is_newer(latest, current, expected):
    assert is_newer(latest, current) == expected


def test_pick_asset_prefers_windows_exe_then_zip_then_msi():
    assets = [
        {"name": "ConsolePlat-v1.5.msi", "browser_download_url": "https://example.invalid/app.msi"},
        {"name": "ConsolePlat-v1.5.zip", "browser_download_url": "https://example.invalid/app.zip"},
        {"name": "ConsolePlat-v1.5.exe", "browser_download_url": "https://example.invalid/app.exe"},
    ]

    assert _pick_asset(assets) == ("https://example.invalid/app.exe", "ConsolePlat-v1.5.exe")


def test_check_for_update_returns_release_payload(monkeypatch):
    class FakeRelease:
        version = "1.5.0"
        tag_name = "v1.5.0"
        name = "ConsolePlat 1.5"
        body = "更新日志"
        html_url = "https://github.com/lXFCL/ConsolePlat/releases/tag/v1.5.0"
        download_url = "https://github.com/lXFCL/ConsolePlat/releases/download/v1.5.0/app.zip"
        asset_name = "app.zip"
        published_at = "2026-06-25T00:00:00Z"

    monkeypatch.setattr(
        "consoleplat.services.version_check_service.fetch_latest_release",
        lambda timeout=8, proxy=None: FakeRelease(),
    )

    result = check_for_update(current="1.4.1")

    assert result["ok"] is True
    assert result["has_update"] is True
    assert result["release"]["version"] == "1.5.0"
    assert json.dumps(result, ensure_ascii=False)


def test_build_opener_uses_proxy_for_http_and_https(monkeypatch):
    captured = {}

    class FakeProxyHandler:
        def __init__(self, proxies):
            captured["proxies"] = proxies

    class FakeOpener:
        pass

    monkeypatch.setattr("consoleplat.services.version_check_service.urllib.request.ProxyHandler", FakeProxyHandler)
    monkeypatch.setattr("consoleplat.services.version_check_service.urllib.request.build_opener", lambda handler: FakeOpener())

    opener = _build_opener(UpdateProxyConfig(enabled=True, host="127.0.0.1", port=7890))

    assert isinstance(opener, FakeOpener)
    assert captured["proxies"] == {
        "http": "http://127.0.0.1:7890",
        "https": "http://127.0.0.1:7890",
    }


def test_proxy_config_normalizes_user_entered_proxy_url():
    proxy = UpdateProxyConfig(enabled=True, host="http://127.0.0.1", port=7890)

    assert proxy.address == "127.0.0.1:7890"
    assert proxy.url == "http://127.0.0.1:7890"


def test_proxy_config_normalizes_user_entered_https_proxy_url():
    proxy = UpdateProxyConfig(enabled=True, host="https://127.0.0.1", port=7890)

    assert proxy.address == "127.0.0.1:7890"
    assert proxy.url == "http://127.0.0.1:7890"


def test_check_for_update_reports_missing_release_as_reachable_repo(monkeypatch):
    def fake_fetch(timeout=8, proxy=None):
        raise urllib.error.HTTPError(
            url="https://api.github.com/repos/lXFCL/ConsolePlat/releases/latest",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr("consoleplat.services.version_check_service.fetch_latest_release", fake_fetch)

    result = check_for_update(current="1.4.1", proxy=UpdateProxyConfig(enabled=True, host="https://127.0.0.1", port=7890))

    assert result["ok"] is False
    assert result["kind"] == "no_release"
    assert "GitHub 已连通" in result["message"]


def test_check_for_update_reports_proxy_connection_failure(monkeypatch):
    def fake_fetch(timeout=8, proxy=None):
        raise OSError("[some other error] proxy down")

    monkeypatch.setattr("consoleplat.services.version_check_service.fetch_latest_release", fake_fetch)

    result = check_for_update(current="1.4.1", proxy=UpdateProxyConfig(enabled=True, host="127.0.0.1", port=7890))

    assert result["ok"] is False
    assert result["kind"] == "proxy_error"
    assert "127.0.0.1:7890" in result["message"]
    assert "HTTP 代理" in result["message"]


def test_check_for_update_retries_without_proxy_after_tls_proxy_handshake_error(monkeypatch):
    calls = []

    class FakeRelease:
        version = "1.5.2"
        tag_name = "v1.5.2"
        name = "ConsolePlat 1.5.2"
        body = "fix proxy fallback"
        html_url = "https://github.com/lXFCL/ConsolePlat/releases/tag/v1.5.2"
        download_url = "https://github.com/lXFCL/ConsolePlat/releases/download/v1.5.2/app.zip"
        asset_name = "app.zip"
        published_at = "2026-06-25T12:00:00Z"

    def fake_fetch(timeout=8, proxy=None):
        calls.append(proxy.url if proxy else None)
        raise OSError("[ASN1: NOT_ENOUGH_DATA] not enough data (ssl.c:4178)")

    def fake_fetch_without_proxy(timeout=8):
        calls.append("DIRECT")
        return FakeRelease()

    monkeypatch.setattr("consoleplat.services.version_check_service.fetch_latest_release", fake_fetch)
    monkeypatch.setattr("consoleplat.services.version_check_service.fetch_latest_release_without_proxy", fake_fetch_without_proxy)

    result = check_for_update(
        current="1.5.0",
        proxy=UpdateProxyConfig(enabled=True, host="127.0.0.1", port=7890),
    )

    assert result["ok"] is True
    assert result["has_update"] is True
    assert result["release"]["version"] == "1.5.2"
    assert calls == ["http://127.0.0.1:7890", "DIRECT"]


def test_build_opener_without_proxy_bypasses_environment_proxy(monkeypatch):
    captured = []

    class FakeProxyHandler:
        def __init__(self, proxies):
            captured.append(proxies)

    class FakeOpener:
        pass

    monkeypatch.setattr("consoleplat.services.version_check_service.urllib.request.ProxyHandler", FakeProxyHandler)
    monkeypatch.setattr(
        "consoleplat.services.version_check_service.urllib.request.build_opener",
        lambda *handlers: FakeOpener(),
    )

    opener = _build_opener(UpdateProxyConfig(enabled=False), disable_env_proxy=True)

    assert isinstance(opener, FakeOpener)
    assert captured == [{}]
