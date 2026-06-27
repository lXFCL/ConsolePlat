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
DEFAULT_OUTPUT = ROOT / "印花图_透明底" / "猫咪自然局部改款_修正7_11_14_15张_2026-06-15"
FONT = ROOT / "assets" / "fonts" / "NanumPenScript-Regular.ttf"


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
    font_size = 96
    font = ImageFont.truetype(str(FONT), font_size)
    while font_size > 58 and draw.textbbox((0, 0), text, font=font, stroke_width=4)[2] > 760:
        font_size -= 2
        font = ImageFont.truetype(str(FONT), font_size)
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=4)
    x = (out.width - (bbox[2] - bbox[0])) // 2
    draw.text((x - bbox[0], y - bbox[1]), text, font=font, fill=(15, 15, 15, 255), stroke_width=4, stroke_fill=(255, 255, 255, 245))
    out.alpha_composite(layer)
    return out


def rounded_glasses(img: Image.Image, fill: tuple[int, int, int, int], shape: str) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    outline = (18, 18, 18, 255)
    d.line((315, 352, 398, 354), fill=(16, 16, 16, 255), width=8)
    d.line((557, 350, 627, 347), fill=(16, 16, 16, 255), width=8)
    if shape == "wide":
        d.rounded_rectangle((382, 312, 475, 357), radius=18, fill=fill, outline=outline, width=6)
        d.rounded_rectangle((484, 310, 578, 355), radius=18, fill=fill, outline=outline, width=6)
    elif shape == "round":
        d.ellipse((386, 307, 475, 366), fill=fill, outline=outline, width=6)
        d.ellipse((484, 305, 573, 364), fill=fill, outline=outline, width=6)
    elif shape == "star":
        d.rounded_rectangle((378, 314, 474, 358), radius=10, fill=fill, outline=outline, width=6)
        d.rounded_rectangle((486, 312, 582, 356), radius=10, fill=fill, outline=outline, width=6)
        d.line((394, 316, 458, 357), fill=(255, 255, 255, 130), width=5)
        d.line((504, 314, 566, 354), fill=(255, 255, 255, 130), width=5)
    else:
        d.rounded_rectangle((390, 323, 470, 356), radius=13, fill=fill, outline=outline, width=5)
        d.rounded_rectangle((481, 322, 561, 354), radius=13, fill=fill, outline=outline, width=5)
    d.line((472, 339, 486, 338), fill=outline, width=6)
    return out


def draw_cap(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    outline = (18, 18, 18, 255)
    d.pieslice((320, 219, 596, 352), 180, 360, fill=fill, outline=outline, width=6)
    d.polygon([(520, 285), (658, 300), (532, 328)], fill=fill, outline=outline)
    d.arc((338, 238, 565, 337), 185, 350, fill=(255, 255, 255, 95), width=5)
    return out


def draw_backward_cap(img: Image.Image, fill: tuple[int, int, int, int], accent: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    outline = (18, 18, 18, 255)
    d.pieslice((306, 214, 594, 352), 180, 360, fill=fill, outline=outline, width=6)
    d.rounded_rectangle((334, 286, 568, 321), radius=16, fill=accent, outline=outline, width=5)
    d.polygon([(322, 282), (247, 268), (314, 323)], fill=fill, outline=outline)
    d.arc((344, 232, 552, 324), 190, 350, fill=(255, 255, 255, 90), width=4)
    d.ellipse((444, 238, 462, 256), fill=accent, outline=outline, width=3)
    return out


def draw_beanie(img: Image.Image, fill: tuple[int, int, int, int], trim: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    outline = (18, 18, 18, 255)
    d.pieslice((314, 214, 596, 356), 180, 360, fill=fill, outline=outline, width=6)
    d.rounded_rectangle((333, 289, 579, 326), radius=14, fill=trim, outline=outline, width=5)
    for x in range(360, 560, 42):
        d.arc((x, 230, x + 60, 320), 205, 330, fill=(255, 255, 255, 82), width=3)
    return out


def draw_beret(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    outline = (18, 18, 18, 255)
    d.pieslice((304, 205, 594, 350), 180, 360, fill=fill, outline=outline, width=6)
    d.ellipse((476, 222, 526, 262), fill=fill, outline=outline, width=5)
    d.arc((328, 230, 568, 338), 186, 350, fill=(255, 255, 255, 92), width=4)
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


def draw_tiny_chain(img: Image.Image) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    for i in range(9):
        x = 335 + i * 27
        y = 552 + int(math.sin(i / 2) * 9)
        d.ellipse((x, y, x + 22, y + 15), outline=(238, 206, 96, 255), width=4)
    return out


def draw_fish_stripe(img: Image.Image, color: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    d.line((548, 545, 620, 493), fill=color, width=6)
    d.line((588, 518, 650, 475), fill=color, width=5)
    d.ellipse((663, 453, 674, 464), fill=color)
    return out


def draw_fish_tag(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    outline = (18, 18, 18, 255)
    d.rounded_rectangle((594, 473, 642, 503), radius=8, fill=fill, outline=outline, width=3)
    d.ellipse((609, 483, 621, 495), fill=(255, 255, 255, 190), outline=outline, width=2)
    d.ellipse((626, 484, 633, 491), fill=(18, 18, 18, 255))
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


def draw_small_badge(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    outline = (18, 18, 18, 255)
    d.rounded_rectangle((340, 566, 390, 607), radius=10, fill=fill, outline=outline, width=4)
    d.ellipse((354, 579, 367, 592), fill=(255, 255, 255, 180), outline=outline, width=2)
    d.ellipse((372, 580, 379, 587), fill=(18, 18, 18, 255))
    return out


def draw_fish_dots(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    outline = (18, 18, 18, 255)
    for cx, cy, r in [(574, 524, 6), (605, 502, 5), (636, 481, 5)]:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill, outline=outline, width=2)
    return out


def draw_chest_star(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    outline = (18, 18, 18, 255)
    pts = [(365, 565), (373, 584), (394, 585), (378, 598), (384, 619), (365, 607), (346, 619), (352, 598), (336, 585), (357, 584)]
    d.polygon(pts, fill=fill, outline=outline)
    return out


def make_base(source: Path, size: int) -> Image.Image:
    return remove_top_text(extract_print(source, size))


def make_variants(base: Image.Image) -> list[tuple[str, Image.Image]]:
    green = recolor_region(base, cat_fill_mask(base), (101, 125, 113), 0.84)
    blue = recolor_region(base, cat_fill_mask(base), (112, 124, 135), 0.80)
    brown = recolor_region(base, cat_fill_mask(base), (148, 130, 108), 0.80)
    violet = recolor_region(base, cat_fill_mask(base), (132, 115, 148), 0.78)
    moss = recolor_region(base, cat_fill_mask(base), (96, 124, 111), 0.88)
    warm = recolor_region(base, cat_fill_mask(base), (144, 132, 120), 0.74)
    slate = recolor_region(base, cat_fill_mask(base), (109, 123, 132), 0.80)
    tan = recolor_region(base, cat_fill_mask(base), (151, 128, 101), 0.82)
    grape = recolor_region(base, cat_fill_mask(base), (125, 107, 146), 0.82)

    variants: list[tuple[str, Image.Image]] = [
        ("01_black_sunglasses", draw_korean_text(rounded_glasses(base, (18, 18, 18, 255), "wide"), "오늘은 쉬는 날")),
        ("02_red_round_green", draw_korean_text(rounded_glasses(moss, (196, 72, 64, 255), "round"), "괜찮아 천천히")),
        ("03_black_cap_gold", draw_korean_text(rounded_glasses(draw_cap(base, (42, 42, 42, 255)), (237, 189, 70, 255), "default"), "생각보다 귀여움")),
        ("04_blue_star_violet", draw_korean_text(rounded_glasses(grape, (58, 93, 188, 255), "star"), "아무튼 행복해")),
        ("05_tan_chain_green", draw_korean_text(draw_tiny_chain(rounded_glasses(tan, (50, 145, 133, 255), "wide")), "대충 멋진 하루")),
        ("06_clear_glasses_sparkle", draw_korean_text(draw_side_sparkles(rounded_glasses(base, (230, 236, 232, 190), "default")), "오늘도 천천히")),
        ("07_green_backward_cap", draw_korean_text(draw_fish_dots(rounded_glasses(draw_backward_cap(green, (44, 47, 48, 255), (226, 226, 216, 255)), (190, 72, 68, 255), "round"), (90, 150, 132, 255)), "그냥 괜찮아")),
        ("08_blue_beanie_cool", draw_korean_text(rounded_glasses(draw_beanie(blue, (40, 48, 62, 255), (225, 225, 216, 255)), (229, 172, 72, 255), "default"), "조용한 하루")),
        ("09_brown_chain_black", draw_korean_text(draw_small_chain(rounded_glasses(brown, (24, 24, 24, 255), "wide"), (232, 202, 92, 255)), "대충 멋있음")),
        ("10_violet_beanie_pin", draw_korean_text(draw_tiny_cap_pin(rounded_glasses(draw_beanie(violet, (54, 54, 54, 255), (236, 236, 228, 255)), (68, 112, 196, 255), "star"), (214, 78, 84, 255)), "생각보다 편함")),
        ("11_warm_amber_tag", draw_korean_text(draw_fish_tag(rounded_glasses(warm, (225, 172, 83, 255), "default"), (232, 202, 92, 255)), "말은 안 해도")),
        ("12_moss_beret_clear", draw_korean_text(rounded_glasses(draw_beret(green, (47, 51, 50, 255)), (226, 236, 230, 190), "round"), "살짝 쉬는 중")),
        ("13_slate_blue_fish", draw_korean_text(draw_fish_stripe(rounded_glasses(slate, (48, 100, 188, 255), "wide"), (112, 154, 188, 255)), "오늘은 무심히")),
        ("14_tan_star_black", draw_korean_text(draw_chest_star(rounded_glasses(tan, (22, 22, 22, 255), "round"), (88, 142, 126, 255)), "기분은 평온")),
        ("15_gray_gold_chain", draw_korean_text(draw_small_chain(rounded_glasses(base, (235, 183, 82, 255), "default"), (238, 206, 96, 255)), "아직 괜찮아")),
    ]
    return variants


def make_overview(paths: list[Path], output: Path) -> None:
    tile = 300
    label_h = 42
    cols = 5
    rows = math.ceil(len(paths) / cols)
    sheet = Image.new("RGB", (cols * tile, rows * (tile + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(paths):
        col = index % cols
        row = index // cols
        img = Image.open(path).convert("RGBA")
        bg = Image.new("RGBA", img.size, "white")
        bg.alpha_composite(img)
        preview = ImageOps.contain(bg.convert("RGB"), (tile - 24, tile - 24), Image.Resampling.LANCZOS)
        x = col * tile + (tile - preview.width) // 2
        y = row * (tile + label_h) + (tile - preview.height) // 2
        sheet.paste(preview, (x, y))
        draw.text((col * tile + 10, row * (tile + label_h) + tile + 10), path.stem[:32], fill=(25, 25, 25))
    sheet.save(output, quality=93)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Make fifteen natural local variants from the cat print.")
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
