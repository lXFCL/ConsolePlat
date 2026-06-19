from __future__ import annotations

import json
import sys

from consoleplat.config import SettingsStore, ShopAccount
from consoleplat.services.monitor_service import EmptyMonitorSource
from consoleplat.services.temu_monitor_source import LoginRequiredError, TemuMonitorSource


def main() -> int:
    settings = SettingsStore().load()
    account = _monitor_account(settings)
    if account and account.phone and account.password:
        source = TemuMonitorSource(account, settings.cdp_endpoint, settings.refresh_interval_seconds)
    else:
        source = EmptyMonitorSource(settings.refresh_interval_seconds, settings.active_shop)

    try:
        snapshot = source.fetch()
        _write({"ok": True, "snapshot": snapshot.to_dict()})
        return 0
    except LoginRequiredError as exc:
        _write({"ok": False, "kind": "login", "message": str(exc)})
        return 2
    except Exception as exc:  # noqa: BLE001 - serialize readable worker failure for UI.
        _write({"ok": False, "kind": "error", "message": f"{type(exc).__name__}: {exc}"})
        return 1
    finally:
        close = getattr(source, "close", None)
        if callable(close):
            close()


def _write(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.flush()


def _monitor_account(settings) -> ShopAccount | None:
    account = settings.accounts.get(settings.active_shop)
    if account and account.phone and account.password:
        return account
    for item in settings.accounts.values():
        if item.phone and item.password:
            return ShopAccount(shop_name=settings.active_shop, phone=item.phone, password=item.password)
    return None


if __name__ == "__main__":
    raise SystemExit(main())
