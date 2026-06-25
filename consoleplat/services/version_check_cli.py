from __future__ import annotations

import json
import sys

from consoleplat.services.version_check_service import check_for_update


def main(argv: list[str] | None = None) -> int:
    result = check_for_update()
    sys.stdout.write(json.dumps(result, ensure_ascii=False))
    sys.stdout.flush()
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
