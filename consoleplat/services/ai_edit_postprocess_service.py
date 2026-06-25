from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from consoleplat.services.ai_image_edit_cli import (
    convert_image_to_transparent_background,
    split_collage_image_with_guides,
)


@dataclass(frozen=True)
class PreparedPrintAsset:
    source_path: Path
    transparent_path: Path
    split_paths: list[Path]


def prepare_ai_edit_print_assets(
    *,
    source_paths: list[str | Path],
    final_transparent_dir: str | Path,
    prefix: str,
    start_number: int,
    split_collage: bool,
    split_count: int,
    x_guides: list[int] | None = None,
    y_guides: list[int] | None = None,
    drop_first_split: bool = False,
) -> list[PreparedPrintAsset]:
    final_dir = Path(final_transparent_dir)
    final_dir.mkdir(parents=True, exist_ok=True)
    prepared: list[PreparedPrintAsset] = []
    next_number = int(start_number)
    for source_text in source_paths:
        source = Path(source_text)
        if source.suffix.lower() != ".png" or not source.exists():
            continue
        transparent_path = (
            source
            if "transparent" in source.stem.lower()
            else Path(convert_image_to_transparent_background(source))
        )
        split_paths: list[Path]
        if split_collage:
            split_output_dir = transparent_path.parent / f"{transparent_path.stem}_split"
            raw_split_paths = [
                Path(path)
                for path in split_collage_image_with_guides(
                    transparent_path,
                    split_output_dir,
                    max(1, int(split_count or 1)),
                    list(x_guides or []),
                    list(y_guides or []),
                    drop_first=drop_first_split,
                )
            ]
        else:
            raw_split_paths = [transparent_path]

        renamed_paths: list[Path] = []
        for raw_path in raw_split_paths:
            target = final_dir / f"{prefix}-{next_number}.png"
            if raw_path.resolve() != target.resolve():
                target.unlink(missing_ok=True)
                target.write_bytes(raw_path.read_bytes())
            renamed_paths.append(target)
            next_number += 1
        prepared.append(
            PreparedPrintAsset(
                source_path=source,
                transparent_path=transparent_path,
                split_paths=renamed_paths,
            )
        )
    return prepared
