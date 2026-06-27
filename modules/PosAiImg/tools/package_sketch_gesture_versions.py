from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "印花图_透明底"
WHITE_SOURCE = BASE / "黑白灰素描手势印花_2026-06-13-v1"
BLACK_SOURCE = BASE / "黑白灰素描手势印花_2026-06-13-v2"
PACKAGE = BASE / "黑白灰素描手势印花_深浅双版本_2026-06-13"


def copy_set(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.glob("*.png")):
        shutil.copy2(path, target / path.name)
    for name in ("_overview_on_white.jpg", "_overview_on_black.jpg", "_prompts.txt"):
        path = source / name
        if path.exists():
            shutil.copy2(path, target / name)


def main() -> int:
    copy_set(WHITE_SOURCE, PACKAGE / "白衣用_深线素描")
    copy_set(BLACK_SOURCE, PACKAGE / "黑衣用_浅线素描")
    print(f"Packaged: {PACKAGE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
