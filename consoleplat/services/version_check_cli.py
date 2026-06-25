from __future__ import annotations

import json
import sys

from consoleplat.config import SettingsStore
from consoleplat.services.version_check_service import UpdateProxyConfig, check_for_update


def main(argv: list[str] | None = None) -> int:
    settings = SettingsStore().load()
    proxy = UpdateProxyConfig(
        enabled=settings.update_proxy_enabled,
        host=settings.update_proxy_host,
        port=settings.update_proxy_port,
    )
    result = check_for_update(proxy=proxy)
    sys.stdout.write(json.dumps(result, ensure_ascii=False))
    sys.stdout.flush()
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
