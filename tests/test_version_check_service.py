from __future__ import annotations

import json

import pytest

from consoleplat.services.version_check_service import (
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

    monkeypatch.setattr("consoleplat.services.version_check_service.fetch_latest_release", lambda timeout=8: FakeRelease())

    result = check_for_update(current="1.4.1")

    assert result["ok"] is True
    assert result["has_update"] is True
    assert result["release"]["version"] == "1.5.0"
    assert json.dumps(result, ensure_ascii=False)
