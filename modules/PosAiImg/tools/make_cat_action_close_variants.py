from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

from make_cat_text_reference_variants import DEFAULT_SOURCE  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "印花图_透明底" / "猫咪韩文动作贴近原图_5张_2026-06-15"
FONT = Path("C:/Windows/Fonts/malgunbd.ttf")


@dataclass(frozen=True)
class Spec:
    name: str
    text: str
    action: str
    body: tuple[int, int, int]
    glasses: tuple[int, int, int]


SPECS = [
    Spec("01_hold_fish_low", "\uc624\ub298\uc740 \uc26c\ub294 \ub0a0", "fish_low", (166, 165, 160), (198, 122, 72)),
    Spec("02_hold_coffee", "\ucee4\ud53c\ub294 \ud544\uc218", "coffee", (148, 158, 150), (32, 32, 32)),
    Spec("03_hold_sign", "\uad1c\ucc2e\uc544 \ucc9c\ucc9c\ud788", "sign", (162, 154, 143), (70, 142, 128)),
    Spec("04_small_wave", "\uc548\ub155 \ub098\ub294 \uc5ec\uae30", "wave", (158, 164, 150), (210, 126, 62)),
    Spec("05_arms_crossed", "\uc624\ub298 \uc880 \uc2dc\ud06c", "crossed", (150, 142, 132), (42, 42, 42)),
]


def draw_smooth(size: int = 900) -> tuple[Image.Image, ImageDraw.ImageDraw, float]:
    scale = 3
    img = Image.new("RGBA", (size * scale, size * scale), (255, 255, 255, 0))
    return img, ImageDraw.Draw(img), scale


def sc(points, s: float):
    if isinstance(points[0], tuple):
        return [(int(x * s), int(y * s)) for x, y in points]
    return tuple(int(v * s) for v in points)


def line(draw: ImageDraw.ImageDraw, pts: list[tuple[int, int]], fill, width: int, s: float) -> None:
    draw.line(sc(pts, s), fill=fill, width=int(width * s), joint="curve")
    r = int(width * s / 2)
    for x, y in sc(pts, s):
        draw.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def limb(draw: ImageDraw.ImageDraw, pts: list[tuple[int, int]], fill, width: int, s: float) -> None:
    outline = (18, 18, 18, 255)
    line(draw, pts, outline, width + 10, s)
    line(draw, pts, fill, width, s)


def polygon(draw: ImageDraw.ImageDraw, pts: list[tuple[int, int]], fill, width: int, s: float) -> None:
    outline = (18, 18, 18, 255)
    draw.polygon(sc(pts, s), fill=fill)
    draw.line(sc(pts + [pts[0]], s), fill=outline, width=int(width * s), joint="curve")


def ellipse(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill, width: int, s: float) -> None:
    draw.ellipse(sc(box, s), fill=fill, outline=(18, 18, 18, 255), width=int(width * s))


def rounded_rect(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, fill, width: int, s: float) -> None:
    draw.rounded_rectangle(sc(box, s), radius=int(radius * s), fill=fill, outline=(18, 18, 18, 255), width=int(width * s))


def draw_text(draw: ImageDraw.ImageDraw, text: str, s: float) -> None:
    font_size = 58
    font = ImageFont.truetype(str(FONT), int(font_size * s))
    while font_size > 38 and draw.textbbox((0, 0), text, font=font)[2] > 760 * s:
        font_size -= 2
        font = ImageFont.truetype(str(FONT), int(font_size * s))
    bbox = draw.textbbox((0, 0), text, font=font)
    x = int((900 * s - (bbox[2] - bbox[0])) / 2)
    y = int(74 * s)
    draw.text((x, y), text, font=font, fill=(14, 14, 14, 255), stroke_width=int(4 * s), stroke_fill=(255, 255, 255, 245))


def draw_base(draw: ImageDraw.ImageDraw, spec: Spec, s: float) -> None:
    body = spec.body + (255,)
    outline = (18, 18, 18, 255)
    # Torso close to the reference: narrow, slightly slouched, open bottom hidden by crop.
    polygon(draw, [(330, 520), (565, 520), (590, 790), (550, 820), (295, 818), (300, 625)], body, 9, s)
    # Wide flattened head.
    ellipse(draw, (262, 232, 650, 548), body, 9, s)
    polygon(draw, [(345, 258), (405, 210), (390, 292)], body, 7, s)
    polygon(draw, [(530, 292), (604, 230), (582, 334)], body, 7, s)
    line(draw, [(315, 365), (602, 360)], outline, 7, s)

    g = spec.glasses + (255,)
    rounded_rect(draw, (390, 328, 470, 363), 13, g, 5, s)
    rounded_rect(draw, (480, 326, 560, 361), 13, g, 5, s)
    line(draw, [(470, 345), (481, 344)], outline, 5, s)
    # Keep the deadpan mouth from the reference.
    line(draw, [(438, 415), (476, 413)], outline, 6, s)
    line(draw, [(426, 457), (488, 452)], outline, 7, s)
    line(draw, [(438, 480), (480, 476)], outline, 6, s)


def draw_fish(draw: ImageDraw.ImageDraw, x: int, y: int, angle: float, s: float) -> None:
    pts = [(0, 0), (238, -14), (270, 16), (238, 48), (0, 63), (32, 31)]
    rad = math.radians(angle)
    out = []
    for px, py in pts:
        out.append((x + int(px * math.cos(rad) - py * math.sin(rad)), y + int(px * math.sin(rad) + py * math.cos(rad))))
    polygon(draw, out, (246, 250, 248, 255), 7, s)
    eye_x = x + int(214 * math.cos(rad) - 7 * math.sin(rad))
    eye_y = y + int(214 * math.sin(rad) + 7 * math.cos(rad))
    draw.ellipse(sc((eye_x - 7, eye_y - 7, eye_x + 7, eye_y + 7), s), fill=(18, 18, 18, 255))
    line(draw, [(out[1][0] - 30, out[1][1] + 16), (out[1][0] - 5, out[1][1] + 28)], (110, 160, 170, 255), 4, s)


def draw_action(draw: ImageDraw.ImageDraw, spec: Spec, s: float) -> None:
    fill = spec.body + (255,)
    outline = (18, 18, 18, 255)
    if spec.action == "fish_low":
        limb(draw, [(350, 610), (440, 680), (540, 650)], fill, 36, s)
        limb(draw, [(575, 590), (635, 610), (690, 585)], fill, 34, s)
        draw_fish(draw, 430, 660, -31, s)
    elif spec.action == "coffee":
        limb(draw, [(350, 600), (310, 650), (275, 690)], fill, 34, s)
        rounded_rect(draw, (225, 625, 318, 720), 18, (248, 247, 240, 255), 7, s)
        draw.arc(sc((306, 648, 360, 704), s), -80, 88, fill=outline, width=int(6 * s))
        limb(draw, [(560, 590), (630, 640), (690, 680)], fill, 34, s)
    elif spec.action == "sign":
        limb(draw, [(350, 602), (312, 650)], fill, 32, s)
        limb(draw, [(565, 600), (612, 650)], fill, 32, s)
        rounded_rect(draw, (285, 555, 620, 665), 18, (255, 255, 255, 255), 7, s)
        font = ImageFont.truetype(str(FONT), int(33 * s))
        draw.text((int(365 * s), int(586 * s)), "\uad1c\ucc2e\uc544", font=font, fill=outline)
    elif spec.action == "wave":
        limb(draw, [(350, 600), (300, 530), (280, 455)], fill, 34, s)
        draw.ellipse(sc((258, 428, 304, 474), s), fill=fill, outline=outline, width=int(7 * s))
        for dx in (-24, -8, 10, 26):
            line(draw, [(280, 438), (280 + dx, 382)], outline, 6, s)
        limb(draw, [(560, 585), (630, 640), (690, 682)], fill, 34, s)
        draw_fish(draw, 410, 675, -28, s)
    elif spec.action == "crossed":
        limb(draw, [(315, 620), (430, 660), (560, 675)], fill, 34, s)
        limb(draw, [(585, 610), (462, 652), (330, 692)], fill, 34, s)
        line(draw, [(330, 692), (386, 710)], outline, 6, s)
        line(draw, [(560, 675), (615, 697)], outline, 6, s)


def make_image(spec: Spec, size: int) -> Image.Image:
    hi, draw, s = draw_smooth(size)
    draw_text(draw, spec.text, s)
    draw_base(draw, spec, s)
    draw_action(draw, spec, s)
    return hi.resize((size, size), Image.Resampling.LANCZOS)


def make_overview(paths: list[Path], output: Path) -> None:
    thumb = 330
    label_h = 44
    sheet = Image.new("RGB", (len(paths) * thumb, thumb + label_h), "white")
    draw = ImageDraw.Draw(sheet)
    for i, path in enumerate(paths):
        img = Image.open(path).convert("RGBA")
        bg = Image.new("RGBA", img.size, "white")
        bg.alpha_composite(img)
        prev = ImageOps.contain(bg.convert("RGB"), (thumb - 20, thumb - 20), Image.Resampling.LANCZOS)
        x = i * thumb + (thumb - prev.width) // 2
        y = (thumb - prev.height) // 2
        sheet.paste(prev, (x, y))
        draw.text((i * thumb + 10, thumb + 11), path.stem, fill=(20, 20, 20))
    sheet.save(output, quality=93)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Draw five action variants closer to the source cat style.")
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--size", type=int, default=900)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for spec in SPECS:
        path = args.output_dir / f"{spec.name}.png"
        make_image(spec, args.size).save(path)
        paths.append(path)
        print(f"saved {path}")
    make_overview(paths, args.output_dir / "_overview.jpg")
    print(f"Output dir: {args.output_dir}")
    print(f"Overview: {args.output_dir / '_overview.jpg'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
