from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


@dataclass(frozen=True)
class PutawaySyncSummary:
    ok: bool
    copied_images: int = 0
    copied_xlsx: bool = False
    images_target_dir: str = ""
    xlsx_target_path: str = ""
    message: str = ""


def _iter_images(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(
        [path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES],
        key=lambda path: path.name.lower(),
    )


def sync_putaway_assets(
    *,
    source_images_dir: str | Path,
    source_xlsx_path: str | Path,
    target_data_dir: str | Path,
    replace_image_names: set[str] | None = None,
) -> PutawaySyncSummary:
    source_images_dir = Path(source_images_dir)
    source_xlsx_path = Path(source_xlsx_path)
    target_data_dir = Path(target_data_dir)

    if not source_images_dir.exists():
        return PutawaySyncSummary(ok=False, message=f"图片目录不存在：{source_images_dir}")
    if not source_xlsx_path.exists():
        return PutawaySyncSummary(ok=False, message=f"XLSX 不存在：{source_xlsx_path}")

    images = _iter_images(source_images_dir)
    if not images:
        return PutawaySyncSummary(ok=False, message=f"图片目录为空：{source_images_dir}")

    images_target_dir = target_data_dir / "pic" / "1"
    images_target_dir.mkdir(parents=True, exist_ok=True)
    copied_images = 0
    replace_image_names = replace_image_names or set()

    for image in images:
        target = images_target_dir / image.name
        if target.exists() and replace_image_names and image.name not in replace_image_names:
            continue
        shutil.copy2(image, target)
        copied_images += 1

    xlsx_target_path = target_data_dir / source_xlsx_path.name
    xlsx_target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_xlsx_path, xlsx_target_path)

    return PutawaySyncSummary(
        ok=True,
        copied_images=copied_images,
        copied_xlsx=True,
        images_target_dir=str(images_target_dir),
        xlsx_target_path=str(xlsx_target_path),
        message=f"已同步 {copied_images} 张图片和 {source_xlsx_path.name}",
    )
