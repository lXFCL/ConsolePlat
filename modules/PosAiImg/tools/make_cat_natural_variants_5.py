from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

from make_cat_text_obvious_variants import draw_korean_text, remove_top_text, rounded_glasses  # noqa: E402
from make_cat_text_reference_variants import extract_print  # noqa: E402
from make_cat_text_simple_local_variants import cat_fill_mask, recolor_region  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "爆款印花知识库" / "爆款1" / "60321cc0525748ad9fb781ff5c03be04-goods.jpeg"
DEFAULT_OUTPUT = ROOT / "印花图_透明底" / "猫咪自然局部改款_5张_2026-06-15"
FONT = Path("C:/Windows/Fonts/malgunbd.ttf")


def draw_beanie(img: Image.Image, fill: tuple[int, int, int, int], trim: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    outline = (18, 18, 18, 255)
    d.pieslice((314, 214, 596, 356), 180, 360, fill=fill, outline=outline, width=6)
    d.rounded_rectangle((333, 289, 579, 326), radius=14, fill=trim, outline=outline, width=5)
    for x in range(360, 560, 42):
        d.arc((x, 230, x + 60, 320), 205, 330, fill=(255, 255, 255, 82), width=3)
    return out


def draw_small_chain(img: Image.Image, color: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    outline = (18, 18, 18, 255)
    for i in range(8):
        x = 354 + i * 28
        y = 552 + int(math.sin(i / 2.0) * 5)
        d.ellipse((x, y, x + 13, y + 13), fill=color, outline=outline, width=2)
    return out


def draw_fish_stripe(img: Image.Image, color: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    # Small details only on the fish body, away from the paw edge.
    d.line((548, 545, 620, 493), fill=color, width=6)
    d.line((588, 518, 650, 475), fill=color, width=5)
    d.ellipse((663, 453, 674, 464), fill=color)
    return out


def draw_side_sparkles(img: Image.Image) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    fill = (18, 18, 18, 255)
    for cx, cy, r in [(613, 278, 16), (644, 316, 10), (290, 302, 9)]:
        d.line((cx - r, cy, cx + r, cy), fill=fill, width=4)
        d.line((cx, cy - r, cx, cy + r), fill=fill, width=4)
    return out


def draw_tiny_cap_pin(img: Image.Image, color: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    outline = (18, 18, 18, 255)
    d.ellipse((543, 289, 570, 316), fill=color, outline=outline, width=3)
    d.line((551, 302, 563, 302), fill=(255, 255, 255, 140), width=3)
    return out


def make_base(source: Path, size: int) -> Image.Image:
    return remove_top_text(extract_print(source, size))


def make_variants(base: Image.Image) -> list[tuple[str, Image.Image]]:
    green = recolor_region(base, cat_fill_mask(base), (101, 125, 113), 0.84)
    blue = recolor_region(base, cat_fill_mask(base), (112, 124, 135), 0.80)
    brown = recolor_region(base, cat_fill_mask(base), (148, 130, 108), 0.80)
    violet = recolor_region(base, cat_fill_mask(base), (132, 115, 148), 0.78)

    variants: list[tuple[str, Image.Image]] = []
    variants.append((
        "01_clear_glasses_sparkle",
        draw_korean_text(draw_side_sparkles(rounded_glasses(base, (230, 236, 232, 190), "default")), "오늘도 천천히"),
    ))
    variants.append((
        "02_green_round_fishstripe",
        draw_korean_text(draw_fish_stripe(rounded_glasses(green, (190, 72, 68, 255), "round"), (90, 150, 132, 255)), "그냥 괜찮아"),
    ))
    variants.append((
        "03_blue_beanie_cool",
        draw_korean_text(rounded_glasses(draw_beanie(blue, (40, 48, 62, 255), (225, 225, 216, 255)), (229, 172, 72, 255), "default"), "조용한 하루"),
    ))
    variants.append((
        "04_brown_chain_black",
        draw_korean_text(draw_small_chain(rounded_glasses(brown, (24, 24, 24, 255), "wide"), (232, 202, 92, 255)), "대충 멋있음"),
    ))
    variants.append((
        "05_violet_cap_pin",
        draw_korean_text(draw_tiny_cap_pin(rounded_glasses(draw_beanie(violet, (54, 54, 54, 255), (236, 236, 228, 255)), (68, 112, 196, 255), "star"), (214, 78, 84, 255)), "생각보다 편함"),
    ))
    return variants


def make_overview(paths: list[Path], output: Path) -> None:
    tile = 340
    label_h = 44
    sheet = Image.new("RGB", (len(paths) * tile, tile + label_h), "white")
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(paths):
        img = Image.open(path).convert("RGBA")
        bg = Image.new("RGBA", img.size, "white")
        bg.alpha_composite(img)
        preview = ImageOps.contain(bg.convert("RGB"), (tile - 26, tile - 26), Image.Resampling.LANCZOS)
        x = index * tile + (tile - preview.width) // 2
        y = (tile - preview.height) // 2
        sheet.paste(preview, (x, y))
        draw.text((index * tile + 10, tile + 11), path.stem[:36], fill=(25, 25, 25))
    sheet.save(output, quality=93)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Make five natural local variants from the cat print.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--size", type=int, default=900)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    base = make_base(args.source, args.size)
    base.save(args.output_dir / "_base_without_old_text.png")
    paths: list[Path] = []
    for name, image in make_variants(base):
        path = args.output_dir / f"{name}.png"
        image.save(path)
        paths.append(path)
        print(f"saved {path}")
    make_overview(paths, args.output_dir / "_overview.jpg")
    print(f"Output dir: {args.output_dir}")
    print(f"Overview: {args.output_dir / '_overview.jpg'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
