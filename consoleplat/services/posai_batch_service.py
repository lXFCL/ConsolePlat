from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


SKU_PATTERN = re.compile(r"^(BO|SZW)-(\d+)\.png$", re.IGNORECASE)


@dataclass(frozen=True)
class BatchPaths:
    batch_name: str
    gallery_batch_dir: Path
    gallery_test_dir: Path
    gallery_final_dir: Path
    mockup_batch_dir: Path
    mockup_test_dir: Path
    mockup_final_dir: Path
    xlsx_path: Path


def suggest_next_start(prefix: str, gallery_root: str | Path, fallback: int) -> int:
    prefix = (prefix or "").upper()
    root = Path(gallery_root)
    if not root.exists():
        return fallback

    highest = 0
    for path in root.rglob(f"{prefix}-*.png"):
        match = SKU_PATTERN.match(path.name)
        if not match or match.group(1).upper() != prefix:
            continue
        highest = max(highest, int(match.group(2)))
    return highest + 1 if highest else fallback


def build_batch_paths(
    *,
    prefix: str,
    start_number: int,
    count: int,
    style_name: str,
    gallery_root: str | Path,
    mockup_root: str | Path,
    xlsx_root: str | Path,
    stamp: str | None = None,
) -> BatchPaths:
    stamp = stamp or date.today().isoformat()
    stamp_digits = "".join(ch for ch in stamp if ch.isdigit())
    if len(stamp_digits) >= 6:
        year = stamp_digits[:4]
        month_value = max(1, min(12, int(stamp_digits[4:6])))
    else:
        today = date.today()
        year = str(today.year)
        month_value = today.month
    end_number = start_number + max(1, count) - 1
    month = f"{month_value}月"
    batch_name = f"{style_name}_{prefix}-{start_number}-{prefix}-{end_number}_{stamp}"
    gallery_batch_dir = Path(gallery_root) / prefix / year / month / batch_name
    mockup_batch_dir = Path(mockup_root) / prefix / year / month / batch_name
    return BatchPaths(
        batch_name=batch_name,
        gallery_batch_dir=gallery_batch_dir,
        gallery_test_dir=gallery_batch_dir / "测试",
        gallery_final_dir=gallery_batch_dir / "最终透明底",
        mockup_batch_dir=mockup_batch_dir,
        mockup_test_dir=mockup_batch_dir / "测试",
        mockup_final_dir=mockup_batch_dir / "最终产品图",
        xlsx_path=Path(xlsx_root) / prefix / f"{batch_name}.xlsx",
    )


def find_existing_batch_dir(image_path: str | Path, gallery_root: str | Path, prefix: str) -> Path | None:
    image_path = Path(image_path)
    gallery_root = Path(gallery_root)
    prefix = (prefix or "").upper()
    try:
        relative = image_path.resolve().relative_to(gallery_root.resolve())
    except (OSError, ValueError):
        return None
    if len(relative.parts) < 4:
        return None
    if relative.parts[0].upper() != prefix:
        return None
    return gallery_root / relative.parts[0] / relative.parts[1] / relative.parts[2] / relative.parts[3]
