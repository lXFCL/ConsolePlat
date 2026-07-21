import base64
import ctypes
import json
import os
from decimal import Decimal, InvalidOperation
from ctypes import wintypes


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob_from_bytes(data: bytes) -> DATA_BLOB:
    buf = ctypes.create_string_buffer(data)
    return DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))


def _bytes_from_blob(blob: DATA_BLOB) -> bytes:
    if not blob.cbData:
        return b""
    return ctypes.string_at(blob.pbData, blob.cbData)


def dpapi_encrypt(plaintext: str) -> str:
    if plaintext is None:
        plaintext = ""
    raw = plaintext.encode("utf-8")
    in_blob = _blob_from_bytes(raw)
    out_blob = DATA_BLOB()
    CRYPTPROTECT_UI_FORBIDDEN = 0x1
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise RuntimeError("无法加密密码")
    try:
        enc = _bytes_from_blob(out_blob)
        return base64.b64encode(enc).decode("ascii")
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def dpapi_decrypt(cipher_b64: str) -> str:
    cipher_b64 = (cipher_b64 or "").strip()
    if not cipher_b64:
        return ""
    enc = base64.b64decode(cipher_b64)
    in_blob = _blob_from_bytes(enc)
    out_blob = DATA_BLOB()
    CRYPTPROTECT_UI_FORBIDDEN = 0x1
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise RuntimeError("无法解密密码")
    try:
        raw = _bytes_from_blob(out_blob)
        return raw.decode("utf-8", errors="ignore")
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def app_dir() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "PutawayAiRobot")
    os.makedirs(path, exist_ok=True)
    return path


def browser_profile_dir() -> str:
    path = os.path.join(app_dir(), "browser_profile")
    os.makedirs(path, exist_ok=True)
    return path


def config_path() -> str:
    return os.path.join(app_dir(), "config.json")


def product_data_path() -> str:
    return os.path.join(app_dir(), "product_data.json")


def runtime_settings_path() -> str:
    return os.path.join(app_dir(), "runtime_settings.json")


def load_credentials():
    profiles = load_account_profiles()
    return {
        "username": profiles.get("active_username") or "",
        "password": profiles.get("active_password") or "",
    }


def save_credentials(username: str, password: str):
    save_account_profiles([{"username": username, "password": password}], (username or "").strip())


def _read_config_data():
    path = config_path()
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f) or {}


def _decrypt_password(cipher_b64: str) -> str:
    try:
        return dpapi_decrypt(cipher_b64 or "")
    except Exception:
        return ""


def load_account_profiles():
    data = _read_config_data()
    raw_accounts = data.get("accounts")
    accounts = []
    if isinstance(raw_accounts, list):
        seen = set()
        for item in raw_accounts:
            if not isinstance(item, dict):
                continue
            username = (item.get("username") or "").strip()
            if not username or username in seen:
                continue
            seen.add(username)
            accounts.append(
                {
                    "username": username,
                    "password": _decrypt_password(item.get("password_dpapi") or ""),
                }
            )
    else:
        username = (data.get("username") or "").strip()
        if username:
            accounts.append(
                {
                    "username": username,
                    "password": _decrypt_password(data.get("password_dpapi") or ""),
                }
            )

    active_username = (data.get("active_username") or "").strip()
    if not active_username and accounts:
        active_username = accounts[0]["username"]
    active_password = ""
    for item in accounts:
        if item["username"] == active_username:
            active_password = item.get("password") or ""
            break
    return {
        "active_username": active_username,
        "active_password": active_password,
        "accounts": accounts,
    }


def save_account_profiles(accounts, active_username: str = ""):
    active_username = (active_username or "").strip()
    out_accounts = []
    seen = set()
    for item in accounts or []:
        if not isinstance(item, dict):
            continue
        username = (item.get("username") or "").strip()
        if not username or username in seen:
            continue
        seen.add(username)
        password = item.get("password") or ""
        out_accounts.append(
            {
                "username": username,
                "password_dpapi": dpapi_encrypt(password) if password else "",
            }
        )
    if active_username not in seen:
        active_username = out_accounts[0]["username"] if out_accounts else ""
    active_password_dpapi = ""
    for item in out_accounts:
        if item["username"] == active_username:
            active_password_dpapi = item.get("password_dpapi") or ""
            break
    data = {
        "active_username": active_username,
        "username": active_username,
        "password_dpapi": active_password_dpapi,
        "accounts": out_accounts,
    }
    with open(config_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_product_rows():
    path = product_data_path()
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f) or {}
    rows = data.get("rows") or []
    out = []
    for r in rows:
        out.append(
            {
                "shop_name": (r.get("shop_name") or "").strip(),
                "category": (r.get("category") or "").strip(),
                "title": (r.get("title") or "").strip(),
                "sku": (r.get("sku") or "").strip(),
                "color": (r.get("color") or "").strip(),
            }
        )
    return out


def save_product_rows(rows):
    data = {"rows": rows or []}
    with open(product_data_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


DEFAULT_DECLARE_PRICE = "14"
DEFAULT_WEIGHTS = (142, 147, 152, 157, 162)


def normalize_declare_price(value, default: str = DEFAULT_DECLARE_PRICE) -> str:
    text = str(value or "").strip()
    try:
        price = Decimal(text)
    except (InvalidOperation, ValueError):
        return default
    if not price.is_finite() or price <= 0:
        return default
    normalized = price.normalize()
    if normalized.as_tuple().exponent < -2:
        return default
    return format(normalized, "f")


def normalize_weights(value, default=DEFAULT_WEIGHTS) -> list:
    try:
        weights = list(value)
    except (TypeError, ValueError):
        return list(default)
    if len(weights) != len(DEFAULT_WEIGHTS):
        return list(default)
    if any(type(weight) is not int or weight <= 0 for weight in weights):
        return list(default)
    return weights


def load_runtime_settings():
    defaults = {
        "parallel_count": 1,
        "cleanup_every": 50,
        "cleanup_max_rounds": 40,
        "upload_fail_stop_threshold": 3,
        "browser_preference": "auto",
        "latest_excel_dir": "",
        "declare_price": DEFAULT_DECLARE_PRICE,
        "weights": list(DEFAULT_WEIGHTS),
    }
    path = runtime_settings_path()
    if not os.path.exists(path):
        return dict(defaults)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f) or {}
    out = dict(defaults)
    try:
        out["parallel_count"] = max(1, int(data.get("parallel_count") or defaults["parallel_count"]))
    except Exception:
        pass
    try:
        out["cleanup_every"] = max(1, int(data.get("cleanup_every") or defaults["cleanup_every"]))
    except Exception:
        pass
    try:
        out["cleanup_max_rounds"] = max(1, int(data.get("cleanup_max_rounds") or defaults["cleanup_max_rounds"]))
    except Exception:
        pass
    try:
        out["upload_fail_stop_threshold"] = max(
            0,
            int(data.get("upload_fail_stop_threshold", defaults["upload_fail_stop_threshold"])),
        )
    except Exception:
        pass
    bp = (data.get("browser_preference") or "").strip().lower()
    if bp in {"auto", "msedge", "chrome"}:
        out["browser_preference"] = bp
    out["latest_excel_dir"] = (data.get("latest_excel_dir") or "").strip()
    out["declare_price"] = normalize_declare_price(data.get("declare_price"))
    out["weights"] = normalize_weights(data.get("weights"))
    return out


def save_runtime_settings(
    parallel_count: int,
    cleanup_every: int,
    cleanup_max_rounds: int,
    browser_preference: str = "auto",
    upload_fail_stop_threshold: int = 3,
    latest_excel_dir: str = "",
    declare_price: str = DEFAULT_DECLARE_PRICE,
    weights=DEFAULT_WEIGHTS,
):
    bp = (browser_preference or "auto").strip().lower()
    if bp not in {"auto", "msedge", "chrome"}:
        bp = "auto"
    data = {
        "parallel_count": max(1, int(parallel_count or 1)),
        "cleanup_every": max(1, int(cleanup_every or 1)),
        "cleanup_max_rounds": max(1, int(cleanup_max_rounds or 1)),
        "upload_fail_stop_threshold": max(0, int(upload_fail_stop_threshold if upload_fail_stop_threshold is not None else 3)),
        "browser_preference": bp,
        "latest_excel_dir": (latest_excel_dir or "").strip(),
        "declare_price": normalize_declare_price(declare_price),
        "weights": normalize_weights(weights),
    }
    with open(runtime_settings_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
