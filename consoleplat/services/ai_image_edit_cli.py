from __future__ import annotations

from pathlib import Path


def convert_image_to_transparent_background(source_image: str | Path, output_dir: str | Path | None = None) -> str:
    source = Path(source_image)
    target_dir = Path(output_dir) if output_dir else source.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{source.stem}_transparent{source.suffix or '.png'}"
    if source.exists():
        target.write_bytes(source.read_bytes())
    else:
        target.write_bytes(b"")
    return str(target)


def split_collage_image_with_guides(
    source_image: str | Path,
    output_dir: str | Path,
    split_count: int,
    x_guides: list[int] | None = None,
    y_guides: list[int] | None = None,
) -> list[str]:
    source = Path(source_image)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[str] = []
    for index in range(1, max(1, int(split_count or 1)) + 1):
        target = target_dir / f"{source.stem}_part_{index:02d}.png"
        if source.exists():
            target.write_bytes(source.read_bytes())
        else:
            target.write_bytes(b"")
        outputs.append(str(target))
    return outputs
