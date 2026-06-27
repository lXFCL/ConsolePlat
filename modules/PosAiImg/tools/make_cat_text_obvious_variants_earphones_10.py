from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

from make_cat_text_reference_variants import extract_print  # noqa: E402
from make_cat_text_simple_local_variants import cat_fill_mask, recolor_region  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "爆款印花知识库" / "爆款1" / "60321cc0525748ad9fb781ff5c03be04-goods.jpeg"
DEFAULT_OUTPUT = ROOT / "印花图_透明底" / "猫咪韩文参考明显改款_耳机10张_2026-06-15"
FONT = Path("C:/Windows/Fonts/malgunbd.ttf")


def remove_top_text(base: Image.Image) -> Image.Image:
    img = base.copy().convert("RGBA")
    arr = np.asarray(img).copy()
    yy = np.indices(arr.shape[:2])[0]
    text_band = yy < 235
    alpha = arr[..., 3] > 0
    arr[..., 3] = np.where(text_band & alpha, 0, arr[..., 3]).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def draw_korean_text(img: Image.Image, text: str, y: int = 86) -> Image.Image:
    out = img.copy().convert("RGBA")
    layer = Image.new("RGBA", out.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(layer)
    font = ImageFont.truetype(str(FONT), 58)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (out.width - (bbox[2] - bbox[0])) // 2
    draw.text((x, y), text, font=font, fill=(15, 15, 15, 255), stroke_width=4, stroke_fill=(255, 255, 255, 245))
    out.alpha_composite(layer)
    return out


def rounded_glasses(img: Image.Image, fill: tuple[int, int, int, int], shape: str) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    d.line((315, 352, 398, 354), fill=(16, 16, 16, 255), width=8)
    d.line((557, 350, 627, 347), fill=(16, 16, 16, 255), width=8)
    if shape == "wide":
        d.rounded_rectangle((382, 312, 475, 357), radius=18, fill=fill, outline=(18, 18, 18, 255), width=6)
        d.rounded_rectangle((484, 310, 578, 355), radius=18, fill=fill, outline=(18, 18, 18, 255), width=6)
    elif shape == "round":
        d.ellipse((386, 307, 475, 366), fill=fill, outline=(18, 18, 18, 255), width=6)
        d.ellipse((484, 305, 573, 364), fill=fill, outline=(18, 18, 18, 255), width=6)
    elif shape == "star":
        d.rounded_rectangle((378, 314, 474, 358), radius=10, fill=fill, outline=(18, 18, 18, 255), width=6)
        d.rounded_rectangle((486, 312, 582, 356), radius=10, fill=fill, outline=(18, 18, 18, 255), width=6)
        d.line((394, 316, 458, 357), fill=(255, 255, 255, 130), width=5)
        d.line((504, 314, 566, 354), fill=(255, 255, 255, 130), width=5)
    else:
        d.rounded_rectangle((390, 323, 470, 356), radius=13, fill=fill, outline=(18, 18, 18, 255), width=5)
        d.rounded_rectangle((481, 322, 561, 354), radius=13, fill=fill, outline=(18, 18, 18, 255), width=5)
    d.line((472, 339, 486, 338), fill=(18, 18, 18, 255), width=6)
    return out


def draw_cap(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    d.pieslice((320, 219, 596, 352), 180, 360, fill=fill, outline=(18, 18, 18, 255), width=6)
    d.polygon([(520, 285), (658, 300), (532, 328)], fill=fill, outline=(18, 18, 18, 255))
    d.arc((338, 238, 565, 337), 185, 350, fill=(255, 255, 255, 95), width=5)
    return out


def draw_tiny_chain(img: Image.Image) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    for i in range(9):
        x = 335 + i * 27
        y = 552 + int(math.sin(i / 2) * 9)
        d.ellipse((x, y, x + 22, y + 15), outline=(238, 206, 96, 255), width=4)
    return out


def draw_earphones(img: Image.Image, wire_color: tuple[int, int, int, int], bud_color: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    outline = (18, 18, 18, 255)
    d.line((310, 255, 292, 298), fill=wire_color, width=4)
    d.line((610, 258, 628, 298), fill=wire_color, width=4)
    d.line((292, 298, 322, 371), fill=wire_color, width=4)
    d.line((628, 298, 598, 371), fill=wire_color, width=4)
    d.ellipse((282, 287, 320, 324), fill=bud_color, outline=outline, width=4)
    d.ellipse((600, 287, 638, 324), fill=bud_color, outline=outline, width=4)
    d.ellipse((291, 297, 309, 315), fill=(255, 255, 255, 140))
    d.ellipse((609, 297, 627, 315), fill=(255, 255, 255, 140))
    return out


def draw_headphones(img: Image.Image, band_color: tuple[int, int, int, int], cup_color: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    outline = (18, 18, 18, 255)
    d.arc((275, 188, 625, 370), 205, 335, fill=band_color, width=12)
    d.arc((289, 194, 611, 360), 205, 335, fill=(255, 255, 255, 85), width=4)
    d.rounded_rectangle((282, 290, 332, 372), radius=20, fill=cup_color, outline=outline, width=5)
    d.rounded_rectangle((590, 290, 640, 372), radius=20, fill=cup_color, outline=outline, width=5)
    d.rectangle((312, 330, 338, 350), fill=cup_color, outline=outline, width=4)
    d.rectangle((582, 330, 608, 350), fill=cup_color, outline=outline, width=4)
    return out


def draw_single_earbud(img: Image.Image, side: str, wire_color: tuple[int, int, int, int], bud_color: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    outline = (18, 18, 18, 255)
    if side == "left":
        d.line((304, 253, 286, 300), fill=wire_color, width=4)
        d.ellipse((274, 289, 313, 327), fill=bud_color, outline=outline, width=4)
    else:
        d.line((621, 255, 641, 302), fill=wire_color, width=4)
        d.ellipse((607, 291, 646, 329), fill=bud_color, outline=outline, width=4)
    return out


def draw_neckband(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    outline = (18, 18, 18, 255)
    d.arc((320, 400, 570, 640), 200, 340, fill=fill, width=14)
    d.rounded_rectangle((298, 523, 332, 572), radius=16, fill=fill, outline=outline, width=4)
    d.rounded_rectangle((598, 523, 632, 572), radius=16, fill=fill, outline=outline, width=4)
    return out


def make_base(source: Path, size: int) -> Image.Image:
    return remove_top_text(extract_print(source, size))


def make_variants(base: Image.Image) -> list[tuple[str, Image.Image]]:
    body_a = recolor_region(base, cat_fill_mask(base), (96, 124, 111), 0.86)
    body_b = recolor_region(base, cat_fill_mask(base), (125, 107, 146), 0.82)
    body_c = recolor_region(base, cat_fill_mask(base), (151, 128, 101), 0.82)
    body_d = recolor_region(base, cat_fill_mask(base), (146, 137, 126), 0.76)
    body_e = recolor_region(base, cat_fill_mask(base), (139, 126, 116), 0.76)
    body_f = recolor_region(base, cat_fill_mask(base), (109, 123, 132), 0.80)

    variants: list[tuple[str, Image.Image]] = [
        ("01_black_sunglasses_cool", draw_korean_text(rounded_glasses(base, (18, 18, 18, 255), "wide"), "오늘은 쉬는 날")),
        ("02_red_round_smile", draw_korean_text(rounded_glasses(body_a, (196, 72, 64, 255), "round"), "천천히 가자")),
        ("03_cap_gold_fish", draw_korean_text(draw_cap(base, (42, 42, 42, 255)), "좋은 하루")),
        ("04_blue_glasses_sleepy", draw_korean_text(rounded_glasses(body_b, (58, 93, 188, 255), "star"), "생각보다 귀여움")),
        ("05_chain_green_glasses", draw_korean_text(draw_tiny_chain(rounded_glasses(body_c, (50, 145, 133, 255), "wide")), "대충 멋진 하루")),
        ("06_headphones_gray", draw_korean_text(draw_headphones(body_d, (52, 52, 52, 255), (86, 92, 100, 255)), "넌 편해 보여")),
        ("07_earbuds_pale", draw_korean_text(draw_earphones(body_e, (194, 194, 194, 255), (240, 240, 240, 255)), "음악 듣는 중")),
        ("08_headphones_green", draw_korean_text(draw_headphones(body_f, (74, 140, 125, 255), (51, 94, 89, 255)), "조금 더 포근")),
        ("09_single_earbud_clean", draw_korean_text(draw_single_earbud(body_c, "left", (230, 230, 230, 255), (248, 248, 248, 255)), "한쪽만 꽂음")),
        ("10_neckband_headset", draw_korean_text(draw_neckband(body_b, (58, 101, 188, 255)), "오늘도 괜찮아")),
    ]
    return variants


def make_overview(paths: list[Path], output: Path) -> None:
    tile = 330
    label_h = 44
    sheet = Image.new("RGB", (len(paths) * tile, tile + label_h), "white")
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(paths):
        img = Image.open(path).convert("RGBA")
        bg = Image.new("RGBA", img.size, "white")
        bg.alpha_composite(img)
        preview = ImageOps.contain(bg.convert("RGB"), (tile - 28, tile - 28), Image.Resampling.LANCZOS)
        x = index * tile + (tile - preview.width) // 2
        y = (tile - preview.height) // 2
        sheet.paste(preview, (x, y))
        draw.text((index * tile + 12, tile + 11), path.stem[:34], fill=(25, 25, 25))
    sheet.save(output, quality=93)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Make ten cat print variants with earphone-style accessories.")
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
