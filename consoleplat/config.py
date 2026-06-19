from __future__ import annotations

import base64
import ctypes
import json
import os
from ctypes import wintypes
from dataclasses import dataclass, field
from pathlib import Path


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob_from_bytes(data: bytes) -> DATA_BLOB:
    buf = ctypes.create_string_buffer(data)
    return DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))


def _bytes_from_blob(blob: DATA_BLOB) -> bytes:
    if not blob.cbData:
        return b""
    return ctypes.string_at(blob.pbData, blob.cbData)


def encrypt_secret(plaintext: str) -> str:
    raw = (plaintext or "").encode("utf-8")
    if not raw:
        return ""
    in_blob = _blob_from_bytes(raw)
    out_blob = DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(in_blob), None, None, None, None, 0x1, ctypes.byref(out_blob)
    )
    if not ok:
        raise RuntimeError("无法加密配置密码")
    try:
        return base64.b64encode(_bytes_from_blob(out_blob)).decode("ascii")
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def decrypt_secret(cipher_b64: str) -> str:
    cipher_b64 = (cipher_b64 or "").strip()
    if not cipher_b64:
        return ""
    enc = base64.b64decode(cipher_b64)
    in_blob = _blob_from_bytes(enc)
    out_blob = DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(in_blob), None, None, None, None, 0x1, ctypes.byref(out_blob)
    )
    if not ok:
        return ""
    try:
        return _bytes_from_blob(out_blob).decode("utf-8", errors="ignore")
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


@dataclass
class ShopAccount:
    shop_name: str
    phone: str = ""
    password: str = ""


@dataclass
class AppSettings:
    active_shop: str = "YUHOOBO"
    cdp_endpoint: str = "http://127.0.0.1:9222"
    refresh_interval_seconds: int = 5
    purchase_export_dir: str = "E:/1PythonProject/SendGoods/outputs"
    startup_width: int = 1180
    startup_height: int = 760
    accounts: dict[str, ShopAccount] = field(default_factory=dict)


def default_settings_path() -> Path:
    base = Path(os.environ.get("APPDATA") or Path.home()) / "ConsolePlat"
    base.mkdir(parents=True, exist_ok=True)
    return base / "settings.json"


class SettingsStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else default_settings_path()

    def load(self) -> AppSettings:
        if not self.path.exists():
            return AppSettings()
        data = json.loads(self.path.read_text(encoding="utf-8") or "{}")
        accounts = {}
        for key, item in (data.get("accounts") or {}).items():
            if not isinstance(item, dict):
                continue
            shop_name = str(item.get("shop_name") or key)
            accounts[key] = ShopAccount(
                shop_name=shop_name,
                phone=str(item.get("phone") or ""),
                password=decrypt_secret(str(item.get("password_dpapi") or "")),
            )
        return AppSettings(
            active_shop=str(data.get("active_shop") or "YUHOOBO"),
            cdp_endpoint=str(data.get("cdp_endpoint") or "http://127.0.0.1:9222"),
            refresh_interval_seconds=int(data.get("refresh_interval_seconds") or 5),
            purchase_export_dir=str(data.get("purchase_export_dir") or "E:/1PythonProject/SendGoods/outputs"),
            startup_width=int(data.get("startup_width") or 1180),
            startup_height=int(data.get("startup_height") or 760),
            accounts=accounts,
        )

    def save(self, settings: AppSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "active_shop": settings.active_shop,
            "cdp_endpoint": settings.cdp_endpoint,
            "refresh_interval_seconds": int(settings.refresh_interval_seconds or 5),
            "purchase_export_dir": settings.purchase_export_dir or "E:/1PythonProject/SendGoods/outputs",
            "startup_width": int(settings.startup_width or 1180),
            "startup_height": int(settings.startup_height or 760),
            "accounts": {},
        }
        for key, account in settings.accounts.items():
            data["accounts"][key] = {
                "shop_name": account.shop_name,
                "phone": account.phone,
                "password_dpapi": encrypt_secret(account.password),
            }
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
