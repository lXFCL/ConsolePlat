from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

from make_cat_text_reference_variants import extract_print  # noqa: E402
from make_cat_text_simple_local_variants import cat_fill_mask, recolor_fish, recolor_region  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "爆款印花知识库" / "爆款1" / "60321cc0525748ad9fb781ff5c03be04-goods.jpeg"
DEFAULT_OUTPUT = ROOT / "印花图_透明底" / "猫咪韩文参考明显改款_10张_2026-06-15"
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


def draw_tie(img: Image.Image, tie_color: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    outline = (18, 18, 18, 255)
    collar = (246, 246, 244, 255)
    d.polygon([(356, 522), (421, 522), (400, 560), (336, 555)], fill=collar, outline=outline)
    d.polygon([(492, 521), (562, 521), (584, 555), (520, 560)], fill=collar, outline=outline)
    d.polygon([(446, 540), (469, 559), (446, 584), (423, 559)], fill=tie_color, outline=outline)
    d.polygon([(446, 581), (472, 684), (440, 709), (416, 592)], fill=tie_color, outline=outline)
    d.line((447, 584, 455, 673), fill=(255, 255, 255, 90), width=4)
    return out


def draw_scarf(img: Image.Image, scarf_color: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    outline = (18, 18, 18, 255)
    d.rounded_rectangle((360, 518, 514, 586), radius=30, fill=scarf_color, outline=outline, width=6)
    d.polygon([(501, 551), (602, 590), (572, 639), (474, 600)], fill=scarf_color, outline=outline)
    d.polygon([(363, 553), (298, 606), (326, 655), (389, 598)], fill=scarf_color, outline=outline)
    d.line((386, 543, 496, 544), fill=(255, 255, 255, 85), width=4)
    return out


def draw_beret(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    d.pieslice((301, 205, 592, 356), 180, 360, fill=fill, outline=(18, 18, 18, 255), width=6)
    d.ellipse((476, 222, 526, 262), fill=fill, outline=(18, 18, 18, 255), width=5)
    d.arc((328, 230, 568, 340), 186, 350, fill=(255, 255, 255, 95), width=4)
    return out


def draw_flowing_hair(img: Image.Image, color: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    outline = (18, 18, 18, 255)
    d.line([(330, 220), (300, 246), (290, 280), (302, 319)], fill=outline, width=16)
    d.line([(330, 220), (304, 242), (296, 272), (309, 306)], fill=color, width=12)
    d.line([(560, 228), (606, 250), (633, 285), (638, 323)], fill=outline, width=16)
    d.line([(560, 228), (602, 249), (625, 282), (629, 315)], fill=color, width=12)
    d.arc((304, 206, 632, 368), 200, 340, fill=color, width=8)
    return out


def draw_headband(img: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    d.line((318, 260, 450, 238), fill=fill, width=12)
    d.line((447, 238, 592, 262), fill=fill, width=12)
    d.line((444, 236, 468, 202), fill=fill, width=10)
    return out


def make_base(source: Path, size: int) -> Image.Image:
    return remove_top_text(extract_print(source, size))


def make_variants(base: Image.Image) -> list[tuple[str, Image.Image]]:
    variants: list[tuple[str, Image.Image]] = []
    body_a = recolor_region(base, cat_fill_mask(base), (96, 124, 111), 0.86)
    body_b = recolor_region(base, cat_fill_mask(base), (125, 107, 146), 0.82)
    body_c = recolor_region(base, cat_fill_mask(base), (151, 128, 101), 0.82)
    body_d = recolor_region(base, cat_fill_mask(base), (146, 137, 126), 0.76)
    body_e = recolor_region(base, cat_fill_mask(base), (139, 126, 116), 0.76)
    body_f = recolor_region(base, cat_fill_mask(base), (109, 123, 132), 0.80)

    variants.append(("01_black_sunglasses_cool", draw_korean_text(rounded_glasses(base, (18, 18, 18, 255), "wide"), "오늘은 쉬는 날")))
    variants.append(("02_red_round_smile", draw_korean_text(rounded_glasses(body_a, (196, 72, 64, 255), "round"), "천천히 가자")))
    variants.append(("03_cap_gold_fish", draw_korean_text(draw_cap(base, (42, 42, 42, 255)), "좋은 하루")))
    variants.append(("04_blue_glasses_sleepy", draw_korean_text(rounded_glasses(body_b, (58, 93, 188, 255), "star"), "생각보다 귀여움")))
    variants.append(("05_chain_green_glasses", draw_korean_text(draw_tiny_chain(rounded_glasses(body_c, (50, 145, 133, 255), "wide")), "대충 멋진 하루")))
    variants.append(("06_tie_formal_gray", draw_korean_text(draw_tie(body_d, (55, 78, 122, 255)), "넥타이 했어")))
    variants.append(("07_flowing_hair_scarf", draw_korean_text(draw_scarf(draw_flowing_hair(body_e, (214, 201, 170, 255)), (198, 95, 108, 255)), "바람처럼 흘러")))
    variants.append(("08_beret_relaxed", draw_korean_text(draw_beret(rounded_glasses(recolor_region(base, cat_fill_mask(base), (140, 132, 120), 0.74), (71, 142, 132, 255), "round"), (62, 62, 62, 255)), "살짝 꾸민 날")))
    variants.append(("09_tie_necklace_clean", draw_korean_text(draw_necklace(draw_tie(body_c, (204, 84, 92, 255)), (238, 214, 130, 255)), "조금 더 포멀")))
    variants.append(("10_headband_fresh", draw_korean_text(draw_headband(rounded_glasses(body_f, (49, 101, 188, 255), "default"), (73, 139, 125, 255)), "오늘도 괜찮아")))
    return variants


def draw_necklace(img: Image.Image, bead_color: tuple[int, int, int, int]) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    outline = (18, 18, 18, 255)
    for i in range(10):
        x = 344 + i * 24
        y = 552 + int(math.sin(i / 2.2) * 4)
        d.ellipse((x, y, x + 12, y + 12), fill=bead_color, outline=outline, width=2)
    return out


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
    parser = argparse.ArgumentParser(description="Make ten controlled local variants from the cat Korean-text print.")
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
