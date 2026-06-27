from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

from make_cat_text_reference_variants import DEFAULT_SOURCE, extract_print  # noqa: E402
from make_cat_text_obvious_variants import remove_top_text  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "印花图_透明底" / "猫咪原图基础小动作_更贴近原图_5张_2026-06-15"
FONT = Path("C:/Windows/Fonts/malgunbd.ttf")


@dataclass(frozen=True)
class Spec:
    name: str
    text: str
    action: str


SPECS = [
    Spec("01_original_pose_new_text", "\uc624\ub298\uc740 \uc26c\ub294 \ub0a0", "original"),
    Spec("02_hold_coffee_small", "\ucee4\ud53c\ub294 \ud544\uc218", "coffee"),
    Spec("03_hold_phone_small", "\uc5f0\ub77d \uc548\ubc1b\uc74c", "phone"),
    Spec("04_hold_sign_small", "\uad1c\ucc2e\uc544 \ucc9c\ucc9c\ud788", "sign"),
    Spec("05_small_wave_keep_body", "\uc548\ub155 \ub098\ub294 \uc5ec\uae30", "wave"),
]


def draw_text(img: Image.Image, text: str) -> Image.Image:
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    font_size = 58
    font = ImageFont.truetype(str(FONT), font_size)
    while font_size > 38 and d.textbbox((0, 0), text, font=font)[2] > 760:
        font_size -= 2
        font = ImageFont.truetype(str(FONT), font_size)
    bbox = d.textbbox((0, 0), text, font=font)
    x = (out.width - (bbox[2] - bbox[0])) // 2
    d.text((x, 78), text, font=font, fill=(14, 14, 14, 255), stroke_width=4, stroke_fill=(255, 255, 255, 245))
    return out


def draw_prop_layer(img: Image.Image) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    out = img.copy().convert("RGBA")
    return out, ImageDraw.Draw(out)


def color_sample(base: Image.Image) -> tuple[int, int, int, int]:
    arr = np.asarray(base.convert("RGBA"))
    patch = arr[610:720, 290:430]
    opaque = patch[patch[..., 3] > 180]
    if opaque.size == 0:
        return (166, 165, 160, 255)
    return tuple(np.median(opaque[:, :3], axis=0).astype(np.uint8).tolist()) + (255,)


def line(draw: ImageDraw.ImageDraw, pts: list[tuple[int, int]], fill, width: int) -> None:
    draw.line(pts, fill=fill, width=width, joint="curve")
    r = max(3, width // 2)
    for x, y in pts:
        draw.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def limb(draw: ImageDraw.ImageDraw, pts: list[tuple[int, int]], fill, width: int) -> None:
    outline = (18, 18, 18, 255)
    line(draw, pts, outline, width + 10)
    line(draw, pts, fill, width)


def draw_fish(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    pts = [(x, y), (x + 250, y - 90), (x + 294, y - 65), (x + 270, y - 30), (x + 20, y + 38), (x + 45, y)]
    draw.polygon(pts, fill=(248, 250, 248, 255))
    draw.line(pts + [pts[0]], fill=(18, 18, 18, 255), width=8, joint="curve")
    draw.ellipse((x + 238, y - 80, x + 252, y - 66), fill=(18, 18, 18, 255))
    draw.line((x + 205, y - 58, x + 225, y - 50), fill=(105, 158, 168, 255), width=5)


def draw_action(base: Image.Image, spec: Spec) -> Image.Image:
    if spec.action == "original":
        return base.copy().convert("RGBA")

    img, d = draw_prop_layer(base)
    fill = color_sample(base)
    outline = (18, 18, 18, 255)

    if spec.action == "coffee":
        d.rounded_rectangle((410, 592, 492, 705), radius=18, fill=(247, 244, 236, 255), outline=outline, width=6)
        d.rectangle((424, 571, 478, 599), fill=(236, 214, 176, 255), outline=outline, width=5)
        d.arc((478, 617, 526, 670), -86, 96, fill=outline, width=5)
        d.line((493, 654, 542, 652), fill=(56, 38, 28, 255), width=4)
    elif spec.action == "phone":
        d.rounded_rectangle((404, 563, 487, 702), radius=16, fill=(35, 38, 40, 255), outline=outline, width=6)
        d.rounded_rectangle((417, 584, 474, 651), radius=8, fill=(196, 222, 230, 255))
        d.line((486, 593, 529, 633), fill=outline, width=5)
    elif spec.action == "sign":
        d.rounded_rectangle((383, 547, 615, 653), radius=18, fill=(255, 255, 255, 255), outline=outline, width=6)
        font = ImageFont.truetype(str(FONT), 32)
        d.text((432, 579), "\uad1c\ucc2e\uc544", font=font, fill=outline)
        d.line((487, 653, 500, 709), fill=outline, width=5)
    elif spec.action == "wave":
        d.ellipse((248, 414, 306, 473), fill=fill, outline=outline, width=6)
        for dx in (-25, -8, 10, 28):
            line(d, [(280, 438), (282 + dx, 383)], outline, 5)
        d.line((286, 438, 308, 406), fill=fill, width=10)
        d.line((300, 430, 321, 414), fill=outline, width=4)
    return img


def make_overview(paths: list[Path], output: Path) -> None:
    thumb = 330
    label_h = 44
    sheet = Image.new("RGB", (len(paths) * thumb, thumb + label_h), "white")
    d = ImageDraw.Draw(sheet)
    for i, path in enumerate(paths):
        img = Image.open(path).convert("RGBA")
        bg = Image.new("RGBA", img.size, "white")
        bg.alpha_composite(img)
        prev = ImageOps.contain(bg.convert("RGB"), (thumb - 20, thumb - 20), Image.Resampling.LANCZOS)
        x = i * thumb + (thumb - prev.width) // 2
        y = (thumb - prev.height) // 2
        sheet.paste(prev, (x, y))
        d.text((i * thumb + 10, thumb + 11), path.stem, fill=(20, 20, 20))
    sheet.save(output, quality=93)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Make small action variants while preserving extracted source cat pixels.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--size", type=int, default=900)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    base = remove_top_text(extract_print(args.source, args.size))
    paths: list[Path] = []
    for spec in SPECS:
        image = draw_text(draw_action(base, spec), spec.text)
        path = args.output_dir / f"{spec.name}.png"
        image.save(path)
        paths.append(path)
        print(f"saved {path}")
    make_overview(paths, args.output_dir / "_overview.jpg")
    print(f"Output dir: {args.output_dir}")
    print(f"Overview: {args.output_dir / '_overview.jpg'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
