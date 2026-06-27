from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

from make_cat_text_reference_variants import extract_print  # noqa: E402
from make_cat_text_simple_local_variants import cat_fill_mask, recolor_fish, recolor_region  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "爆款印花知识库" / "爆款1" / "60321cc0525748ad9fb781ff5c03be04-goods.jpeg"
DEFAULT_OUTPUT = ROOT / "印花图_透明底" / "猫咪韩文参考明显改款_2026-06-15"
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
    # White stroke keeps the lettering readable on black or gray shirts after compositing.
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


def change_mouth(img: Image.Image, mode: str) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    arr = np.asarray(out)
    patch = arr[365:455, 380:535]
    opaque = patch[patch[..., 3] > 180]
    if opaque.size:
        fill_rgb = tuple(np.median(opaque[:, :3], axis=0).astype(np.uint8).tolist())
    else:
        fill_rgb = (166, 165, 160)
    d.rounded_rectangle((424, 383, 512, 472), radius=22, fill=(*fill_rgb, 255))
    if mode == "cool":
        d.line((440, 407, 490, 407), fill=(18, 18, 18, 255), width=7)
        d.line((454, 452, 494, 447), fill=(18, 18, 18, 255), width=7)
    elif mode == "smile":
        d.arc((426, 394, 503, 448), 20, 160, fill=(18, 18, 18, 255), width=7)
        d.line((452, 454, 490, 454), fill=(18, 18, 18, 255), width=7)
    elif mode == "sleepy":
        d.arc((430, 400, 475, 425), 15, 165, fill=(18, 18, 18, 255), width=6)
        d.arc((450, 445, 500, 468), 195, 345, fill=(18, 18, 18, 255), width=6)
    else:
        d.line((447, 405, 485, 405), fill=(18, 18, 18, 255), width=6)
        d.line((443, 451, 493, 446), fill=(18, 18, 18, 255), width=6)
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


def make_base(source: Path, size: int) -> Image.Image:
    return remove_top_text(extract_print(source, size))


def make_variants(base: Image.Image) -> list[tuple[str, Image.Image]]:
    specs: list[tuple[str, str, callable]] = []

    def v1(img: Image.Image) -> Image.Image:
        img = rounded_glasses(img, (18, 18, 18, 255), "wide")
        return img

    def v2(img: Image.Image) -> Image.Image:
        img = recolor_region(img, cat_fill_mask(img), (96, 124, 111), 0.88)
        img = rounded_glasses(img, (196, 72, 64, 255), "round")
        return img

    def v3(img: Image.Image) -> Image.Image:
        img = draw_cap(img, (42, 42, 42, 255))
        img = rounded_glasses(img, (237, 189, 70, 255), "default")
        return img

    def v4(img: Image.Image) -> Image.Image:
        img = recolor_region(img, cat_fill_mask(img), (125, 107, 146), 0.82)
        img = rounded_glasses(img, (58, 93, 188, 255), "star")
        return img

    def v5(img: Image.Image) -> Image.Image:
        img = recolor_region(img, cat_fill_mask(img), (151, 128, 101), 0.82)
        img = rounded_glasses(img, (50, 145, 133, 255), "wide")
        img = draw_tiny_chain(img)
        return img

    entries = [
        ("01_black_sunglasses_cool", "오늘은 쉬는 날", v1),
        ("02_red_round_smile", "괜찮아 천천히", v2),
        ("03_cap_gold_fish", "생각보다 귀여움", v3),
        ("04_blue_glasses_sleepy", "아무튼 행복해", v4),
        ("05_chain_green_glasses", "대충 멋진 하루", v5),
    ]
    out: list[tuple[str, Image.Image]] = []
    for name, text, fn in entries:
        img = draw_korean_text(fn(base.copy()), text)
        out.append((name, img))
    return out


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
    parser = argparse.ArgumentParser(description="Make five obvious controlled variants from the cat Korean-text print.")
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
