from __future__ import annotations

import argparse
import json
import sys

from consoleplat.config import SettingsStore, ShopAccount
from consoleplat.services.monitor_service import EmptyMonitorSource
from consoleplat.services.temu_monitor_source import LoginRequiredError, TemuMonitorSource


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ConsolePlat Temu monitor worker")
    parser.add_argument("--close-monitor-pages", action="store_true", help="Close open Temu urgency monitor pages.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    settings = SettingsStore().load()
    account = _monitor_account(settings)
    if args.close_monitor_pages and account is None:
        account = ShopAccount(shop_name=settings.active_shop or "YUHOOBO")
    if account and account.phone and account.password:
        source = TemuMonitorSource(account, settings.cdp_endpoint, settings.refresh_interval_seconds)
    elif args.close_monitor_pages and account is not None:
        source = TemuMonitorSource(account, settings.cdp_endpoint, settings.refresh_interval_seconds)
    else:
        source = EmptyMonitorSource(settings.refresh_interval_seconds, settings.active_shop)

    try:
        if args.close_monitor_pages:
            close_pages = getattr(source, "close_monitor_pages", None)
            closed_count = close_pages() if callable(close_pages) else 0
            _write({"ok": True, "closed_count": closed_count})
            return 0
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
