from __future__ import annotations

import shutil
from pathlib import Path

from generate_bo_painterly_master_batch import ROOT, batch_name, batch_paths, project_paths


def copy_files(source_dir: Path, target_dir: Path, pattern: str = "*") -> int:
    if not source_dir.exists():
        raise FileNotFoundError(source_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for source in source_dir.glob(pattern):
        if source.is_file():
            shutil.copy2(source, target_dir / source.name)
            count += 1
    return count


def main() -> int:
    prefix, start, count, stamp = "BO", 1421, 50, "2026-06-17"
    name = batch_name(prefix, start, count, stamp)
    paths = project_paths(batch_paths(prefix, start, count, stamp))

    old_print_dir = ROOT / "印花图_透明底" / "BO" / name
    old_raw_dir = ROOT / "印花图" / "BO" / name
    old_mockup_dir = ROOT / "批量贴图结果" / f"{name}_随机主图{count}"

    raw_count = copy_files(old_raw_dir, paths.raw_dir)
    print_count = copy_files(old_print_dir, paths.print_dir, "BO-*.png")
    product_count = copy_files(old_mockup_dir, paths.mockup_dir, "BO-*.png")
    overview_count = copy_files(old_mockup_dir, paths.mockup_test_dir, "_overview.jpg")

    print(
        {
            "raw_count": raw_count,
            "print_count": print_count,
            "product_count": product_count,
            "overview_count": overview_count,
            "gallery_dir": str(paths.print_dir.parent),
            "mockup_dir": str(paths.mockup_dir.parent),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
