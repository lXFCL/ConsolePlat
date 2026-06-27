from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "印花图_透明底" / "猫咪韩文动作测试_2026-06-15"
FONT = Path("C:/Windows/Fonts/malgunbd.ttf")


@dataclass(frozen=True)
class ActionSpec:
    name: str
    text: str
    action: str
    body: tuple[int, int, int]
    glasses: tuple[int, int, int]


SPECS = [
    ActionSpec("01_wave", "\uc548\ub155 \ub098\ub294 \uc5ec\uae30", "wave", (164, 164, 158), (30, 30, 30)),
    ActionSpec("02_thumbs_up", "\uadf8\ub0e5 \uad1c\ucc2e\uc544", "thumbs_up", (102, 130, 116), (196, 72, 64)),
    ActionSpec("03_arms_crossed", "\uc624\ub298 \uc880 \uc2dc\ud06c", "arms_crossed", (150, 132, 108), (50, 145, 133)),
    ActionSpec("04_hold_coffee", "\ucee4\ud53c\ub294 \ud544\uc218", "coffee", (121, 132, 154), (237, 189, 70)),
    ActionSpec("05_read_book", "\uc870\uc6a9\ud788 \ubcf4\ub294 \uc911", "book", (132, 118, 150), (58, 93, 188)),
    ActionSpec("06_peace", "\uc791\uc740 \ud3c9\ud654", "peace", (140, 144, 116), (231, 129, 63)),
    ActionSpec("07_phone", "\uc5f0\ub77d \uc548\ubc1b\uc74c", "phone", (108, 129, 154), (45, 105, 82)),
    ActionSpec("08_sleepy", "\uc7a0\uae50 \uc26c\uc5b4\uac00", "sleepy", (152, 130, 130), (90, 90, 90)),
    ActionSpec("09_sign", "\uc624\ub298\uc740 \ub0b4 \ud398\uc774\uc2a4", "sign", (115, 138, 120), (18, 18, 18)),
    ActionSpec("10_dance", "\ub290\ub9ac\uac8c \uc990\uae30\uc790", "dance", (156, 140, 102), (196, 72, 64)),
]


def line(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], fill=(18, 18, 18, 255), width: int = 8) -> None:
    draw.line(points, fill=fill, width=width, joint="curve")
    r = max(3, width // 2)
    for x, y in points:
        draw.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def rounded_line(draw: ImageDraw.ImageDraw, p1: tuple[int, int], p2: tuple[int, int], color, width: int) -> None:
    line(draw, [p1, p2], color, width)


def outlined_line(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], fill, width: int, outline=(18, 18, 18, 255), outline_width: int = 10) -> None:
    line(draw, points, outline, width + outline_width)
    line(draw, points, fill, width)


def outlined_ellipse(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill, outline=(18, 18, 18, 255), width: int = 8) -> None:
    draw.ellipse(box, fill=fill, outline=outline, width=width)


def outlined_polygon(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], fill, outline=(18, 18, 18, 255), width: int = 7) -> None:
    draw.polygon(points, fill=fill)
    draw.line(points + [points[0]], fill=outline, width=width, joint="curve")


def draw_text(img: Image.Image, text: str) -> None:
    draw = ImageDraw.Draw(img)
    font_size = 56
    font = ImageFont.truetype(str(FONT), font_size)
    while font_size > 38 and draw.textbbox((0, 0), text, font=font)[2] > 760:
        font_size -= 2
        font = ImageFont.truetype(str(FONT), font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (img.width - (bbox[2] - bbox[0])) // 2
    draw.text((x, 82), text, font=font, fill=(14, 14, 14, 255), stroke_width=4, stroke_fill=(255, 255, 255, 245))


def draw_cat_base(img: Image.Image, spec: ActionSpec) -> None:
    draw = ImageDraw.Draw(img)
    body = spec.body + (255,)
    outline = (18, 18, 18, 255)

    # The source print is not a cute animal shape; it is a squat blob-like cat.
    # Keep the head wide, the ears as tiny bumps, and the body narrow.
    draw.rounded_rectangle((330, 500, 575, 810), radius=78, fill=body, outline=outline, width=9)
    draw.rectangle((345, 710, 565, 818), fill=body)
    draw.line((345, 710, 345, 818), fill=outline, width=9)
    draw.line((565, 710, 565, 818), fill=outline, width=9)
    draw.line((345, 818, 565, 818), fill=outline, width=9)

    outlined_ellipse(draw, (260, 242, 646, 570), body, outline, 9)
    outlined_polygon(draw, [(336, 270), (402, 216), (386, 305)], body, outline, 7)
    outlined_polygon(draw, [(525, 300), (610, 235), (584, 340)], body, outline, 7)
    draw.line((312, 374, 600, 365), fill=outline, width=8)

    g = spec.glasses + (255,)
    draw.rounded_rectangle((386, 340, 466, 374), radius=13, fill=g, outline=outline, width=5)
    draw.rounded_rectangle((480, 338, 560, 372), radius=13, fill=g, outline=outline, width=5)
    draw.line((466, 356, 480, 355), fill=outline, width=5)
    draw.arc((405, 346, 448, 365), 15, 168, fill=outline, width=4)
    draw.arc((500, 344, 543, 363), 15, 168, fill=outline, width=4)
    draw.line((438, 428, 480, 426), fill=outline, width=7)
    draw.line((428, 470, 492, 464), fill=outline, width=7)


def draw_fish(draw: ImageDraw.ImageDraw, x: int, y: int, angle: float = -35) -> None:
    pts = [(0, 0), (205, -15), (240, 15), (205, 45), (0, 60), (35, 30)]
    rad = math.radians(angle)
    out = []
    for px, py in pts:
        out.append((x + int(px * math.cos(rad) - py * math.sin(rad)), y + int(px * math.sin(rad) + py * math.cos(rad))))
    outlined_polygon(draw, out, (245, 248, 246, 255), (18, 18, 18, 255), 7)
    eye = (x + int(185 * math.cos(rad) - 2 * math.sin(rad)), y + int(185 * math.sin(rad) + 2 * math.cos(rad)))
    draw.ellipse((eye[0] - 7, eye[1] - 7, eye[0] + 7, eye[1] + 7), fill=(18, 18, 18, 255))


def draw_action(img: Image.Image, spec: ActionSpec) -> None:
    draw = ImageDraw.Draw(img)
    outline = (18, 18, 18, 255)
    fill = spec.body + (255,)

    if spec.action == "wave":
        outlined_line(draw, [(358, 560), (292, 492), (258, 405)], fill, 38)
        draw.ellipse((235, 374, 286, 424), fill=fill, outline=outline, width=7)
        for dx in (-28, -8, 12, 30):
            line(draw, [(258, 388), (258 + dx, 330)], outline, 6)
        outlined_line(draw, [(535, 572), (626, 636), (690, 696)], fill, 38)
    elif spec.action == "thumbs_up":
        outlined_line(draw, [(354, 585), (280, 610), (230, 608)], fill, 38)
        draw.rounded_rectangle((205, 570, 270, 628), radius=18, fill=fill, outline=outline, width=7)
        line(draw, [(238, 574), (226, 516)], outline, 9)
        outlined_line(draw, [(540, 580), (620, 645), (674, 696)], fill, 38)
    elif spec.action == "arms_crossed":
        outlined_line(draw, [(324, 610), (425, 665), (560, 688)], fill, 38)
        outlined_line(draw, [(570, 610), (465, 660), (320, 690)], fill, 38)
        line(draw, [(320, 690), (380, 710)], outline, 7)
        line(draw, [(560, 688), (612, 710)], outline, 7)
    elif spec.action == "coffee":
        outlined_line(draw, [(352, 585), (306, 646), (284, 690)], fill, 38)
        draw.rounded_rectangle((230, 610, 330, 712), radius=20, fill=(245, 245, 238, 255), outline=outline, width=7)
        draw.arc((318, 635, 366, 690), -85, 90, fill=outline, width=6)
        outlined_line(draw, [(545, 575), (626, 642), (684, 700)], fill, 38)
    elif spec.action == "book":
        outlined_polygon(draw, [(292, 610), (446, 570), (446, 710), (292, 746)], (236, 230, 210, 255), outline, 6)
        outlined_polygon(draw, [(448, 570), (616, 612), (616, 746), (448, 710)], (226, 232, 245, 255), outline, 6)
        line(draw, [(448, 580), (448, 705)], outline, 5)
        outlined_line(draw, [(340, 565), (318, 660)], fill, 32)
        outlined_line(draw, [(560, 565), (590, 665)], fill, 32)
    elif spec.action == "peace":
        outlined_line(draw, [(352, 560), (286, 506), (248, 456)], fill, 38)
        line(draw, [(248, 456), (220, 376)], outline, 8)
        line(draw, [(248, 456), (286, 382)], outline, 8)
        outlined_line(draw, [(545, 575), (626, 642), (684, 700)], fill, 38)
    elif spec.action == "phone":
        outlined_line(draw, [(350, 572), (300, 630), (275, 678)], fill, 38)
        draw.rounded_rectangle((228, 545, 314, 686), radius=18, fill=(35, 38, 40, 255), outline=outline, width=7)
        draw.rounded_rectangle((244, 566, 298, 652), radius=8, fill=(205, 225, 230, 255))
        outlined_line(draw, [(540, 575), (622, 646), (680, 704)], fill, 38)
    elif spec.action == "sleepy":
        outlined_line(draw, [(320, 595), (438, 610), (555, 595)], fill, 38)
        draw.arc((590, 245, 650, 300), 40, 300, fill=outline, width=6)
        draw.arc((635, 210, 705, 280), 40, 300, fill=outline, width=6)
    elif spec.action == "sign":
        outlined_line(draw, [(338, 585), (292, 648)], fill, 34)
        outlined_line(draw, [(555, 585), (610, 648)], fill, 34)
        draw.rounded_rectangle((286, 544, 614, 660), radius=18, fill=(255, 255, 255, 255), outline=outline, width=7)
        font = ImageFont.truetype(str(FONT), 32)
        draw.text((360, 578), "\uad1c\ucc2e\uc544", font=font, fill=outline)
    elif spec.action == "dance":
        outlined_line(draw, [(350, 570), (270, 515), (232, 470)], fill, 38)
        outlined_line(draw, [(540, 565), (630, 510), (680, 462)], fill, 38)
        line(draw, [(235, 485), (205, 455), (190, 425)], outline, 7)
        line(draw, [(675, 465), (710, 430), (730, 398)], outline, 7)
        line(draw, [(365, 790), (325, 850)], outline, 10)
        line(draw, [(525, 790), (575, 850)], outline, 10)
    else:
        outlined_line(draw, [(350, 580), (450, 660)], fill, 38)
        outlined_line(draw, [(540, 575), (650, 650)], fill, 38)
        draw_fish(draw, 430, 645)

    if spec.action not in {"book", "sign", "sleepy"}:
        # Add a small hand outline at limb ends, keeping the crude cartoon language.
        pass


def make_image(spec: ActionSpec, size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw_text(img, spec.text)
    draw_cat_base(img, spec)
    draw_action(img, spec)
    return img


def make_overview(paths: list[Path], output: Path, columns: int = 5) -> None:
    thumb = 310
    label_h = 42
    rows = (len(paths) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * thumb, rows * (thumb + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(paths):
        img = Image.open(path).convert("RGBA")
        bg = Image.new("RGBA", img.size, "white")
        bg.alpha_composite(img)
        prev = ImageOps.contain(bg.convert("RGB"), (thumb - 18, thumb - 18), Image.Resampling.LANCZOS)
        x0 = (index % columns) * thumb
        y0 = (index // columns) * (thumb + label_h)
        sheet.paste(prev, (x0 + (thumb - prev.width) // 2, y0 + (thumb - prev.height) // 2))
        draw.text((x0 + 10, y0 + thumb + 10), path.stem, fill=(20, 20, 20))
    sheet.save(output, quality=93)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Draw same-style Korean cat action variants.")
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
