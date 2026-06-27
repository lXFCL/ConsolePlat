from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

import comfy_print_batch


ROOT = Path(__file__).resolve().parents[1]

OUTPUT_NAMES = [
    "00_reference_style_hand_print.png",
    "10_kangkang_gekokujo_style.png",
    "01_zi_rat_子.png",
    "02_chou_ox_丑.png",
    "03_yin_tiger_寅.png",
    "04_mao_rabbit_卯.png",
    "05_chen_dragon_辰.png",
    "06_si_snake_巳.png",
    "07_wu_horse_午.png",
    "08_wei_goat_未.png",
    "09_shen_monkey_申.png",
]


def make_overview(paths: list[Path], output: Path, columns: int = 4) -> None:
    tile = 360
    label_h = 54
    rows = (len(paths) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * tile, rows * (tile + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(paths):
        image = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
        background = Image.new("RGBA", image.size, "white")
        background.alpha_composite(image)
        preview = ImageOps.contain(background.convert("RGB"), (tile - 34, tile - 34), Image.Resampling.LANCZOS)
        x0 = (index % columns) * tile
        y0 = (index // columns) * (tile + label_h)
        sheet.paste(preview, (x0 + (tile - preview.width) // 2, y0 + (tile - preview.height) // 2))
        draw.text((x0 + 12, y0 + tile + 12), path.stem[:44], fill=(0, 0, 0))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=94)


def package_outputs(source_dir: Path, output_dir: Path) -> list[Path]:
    sources = sorted(source_dir.glob("*.png"), key=lambda path: path.stat().st_mtime)
    if len(sources) != len(OUTPUT_NAMES):
        raise RuntimeError(f"Expected {len(OUTPUT_NAMES)} PNG files in {source_dir}, found {len(sources)}")

    raw_dir = output_dir / "white_bg"
    transparent_dir = output_dir / "transparent"
    raw_dir.mkdir(parents=True, exist_ok=True)
    transparent_dir.mkdir(parents=True, exist_ok=True)

    transparent_paths: list[Path] = []
    for source, name in zip(sources, OUTPUT_NAMES, strict=True):
        raw_path = raw_dir / name
        transparent_path = transparent_dir / name
        shutil.copy2(source, raw_path)
        comfy_print_batch.remove_white_bg(raw_path, transparent_path, threshold=246, color_distance=36.0)
        comfy_print_batch.repad_transparent_png(transparent_path, padding_ratio=0.12)
        transparent_paths.append(transparent_path)

    make_overview(transparent_paths, output_dir / "_overview_all.jpg", columns=4)
    make_overview(transparent_paths[2:], output_dir / "_overview_9_zodiac.jpg", columns=3)
    return transparent_paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Copy, rename, and make transparent PNGs from GPT image-generation outputs.")
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "印花图_透明底" / "GPT写实黑白手势印花_2026-06-16")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = package_outputs(args.source_dir, args.output_dir)
    print(f"Output dir: {args.output_dir}")
    print(f"Transparent PNG count: {len(paths)}")
    print(f"Overview: {args.output_dir / '_overview_all.jpg'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
