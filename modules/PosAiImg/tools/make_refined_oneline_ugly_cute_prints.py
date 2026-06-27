from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "\u5370\u82b1\u56fe_\u900f\u660e\u5e95" / "\u4e00\u7b14\u753b\u4e11\u840c\u5634\u5634\u5634_5\u6b3e_2026-06-10"
OVERVIEW = OUTPUT_DIR / "_overview.jpg"

CANVAS = 1024
SCALE = 3
SIZE = CANVAS * SCALE

INK = (28, 27, 24, 255)
CREAM = (252, 246, 220, 255)
PINK = (236, 125, 143, 255)
BLUE = (112, 159, 187, 255)
GREEN = (116, 160, 118, 255)


def p(value: int) -> int:
    return value * SCALE


def pts(values: list[tuple[int, int]]) -> list[tuple[int, int]]:
    return [(p(x), p(y)) for x, y in values]


def font(size: int) -> ImageFont.ImageFont:
    for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, p(size))
        except OSError:
            pass
    return ImageFont.load_default()


def bezier(points: list[tuple[int, int]], steps: int = 18) -> list[tuple[int, int]]:
    if len(points) < 4:
        return points
    out: list[tuple[int, int]] = []
    for i in range(0, len(points) - 3, 3):
        p0, p1, p2, p3 = points[i : i + 4]
        for step in range(steps):
            t = step / steps
            x = (
                (1 - t) ** 3 * p0[0]
                + 3 * (1 - t) ** 2 * t * p1[0]
                + 3 * (1 - t) * t**2 * p2[0]
                + t**3 * p3[0]
            )
            y = (
                (1 - t) ** 3 * p0[1]
                + 3 * (1 - t) ** 2 * t * p1[1]
                + 3 * (1 - t) * t**2 * p2[1]
                + t**3 * p3[1]
            )
            out.append((int(x), int(y)))
    out.append(points[-1])
    return out


def stroke(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], ink_width: int = 15) -> None:
    scaled = pts(points)
    halo_width = ink_width + 18
    draw.line(scaled, fill=CREAM, width=p(halo_width), joint="curve")
    for x, y in scaled:
        r = p(halo_width // 2)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=CREAM)
    draw.line(scaled, fill=INK, width=p(ink_width), joint="curve")
    for x, y in scaled:
        r = p(ink_width // 2)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=INK)


def dot(draw: ImageDraw.ImageDraw, x: int, y: int, r: int = 11, color=INK) -> None:
    draw.ellipse((p(x - r), p(y - r), p(x + r), p(y + r)), fill=color)


def face(draw: ImageDraw.ImageDraw, left_eye: tuple[int, int], right_eye: tuple[int, int], nose: tuple[int, int]) -> None:
    dot(draw, *left_eye, r=12)
    dot(draw, *right_eye, r=12)
    x, y = nose
    stroke(draw, bezier([(x - 6, y + 16), (x - 38, y - 2), (x - 38, y + 44), (x - 5, y + 31)]), ink_width=7)
    stroke(draw, bezier([(x + 6, y + 16), (x + 38, y - 2), (x + 38, y + 44), (x + 5, y + 31)]), ink_width=7)


def label(draw: ImageDraw.ImageDraw, text: str, y: int, size: int = 62) -> None:
    fnt = font(size)
    bbox = draw.textbbox((0, 0), text, font=fnt, stroke_width=p(7))
    x = (SIZE - (bbox[2] - bbox[0])) // 2
    draw.text((x, p(y)), text, font=fnt, fill=INK, stroke_width=p(7), stroke_fill=CREAM)


def cheek(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    dot(draw, x, y, 13, PINK)


def cat(draw: ImageDraw.ImageDraw) -> None:
    outline = bezier(
        [
            (300, 555),
            (280, 430),
            (360, 350),
            (430, 385),
            (430, 385),
            (448, 270),
            (506, 388),
            (506, 388),
            (610, 278),
            (632, 398),
            (730, 440),
            (744, 618),
            (585, 674),
            (420, 662),
            (296, 606),
            (300, 555),
        ]
    )
    stroke(draw, outline)
    face(draw, (455, 490), (585, 490), (520, 530))
    stroke(draw, [(340, 535), (255, 515)], ink_width=8)
    stroke(draw, [(690, 535), (775, 515)], ink_width=8)
    cheek(draw, 402, 555)
    dot(draw, 720, 330, 7, PINK)
    label(draw, "not today", 735, 56)


def bear(draw: ImageDraw.ImageDraw) -> None:
    outline = bezier(
        [
            (335, 535),
            (300, 420),
            (360, 330),
            (430, 355),
            (430, 355),
            (480, 275),
            (535, 354),
            (535, 354),
            (610, 270),
            (676, 365),
            (725, 450),
            (710, 635),
            (555, 688),
            (390, 655),
            (300, 585),
            (335, 535),
        ]
    )
    stroke(draw, outline)
    face(draw, (455, 488), (575, 492), (516, 535))
    cheek(draw, 400, 550)
    stroke(draw, [(690, 582), (775, 610), (810, 570)], ink_width=9)
    dot(draw, 815, 555, 8, GREEN)
    label(draw, "hmm", 738, 70)


def dog(draw: ImageDraw.ImageDraw) -> None:
    outline = bezier(
        [
            (300, 485),
            (315, 365),
            (420, 330),
            (442, 430),
            (442, 430),
            (470, 345),
            (575, 345),
            (600, 430),
            (600, 430),
            (700, 335),
            (745, 470),
            (670, 598),
            (590, 680),
            (410, 660),
            (300, 560),
            (300, 485),
        ]
    )
    stroke(draw, outline)
    face(draw, (455, 492), (575, 492), (517, 536))
    cheek(draw, 625, 545)
    stroke(draw, [(675, 654), (760, 690), (805, 655)], ink_width=9)
    dot(draw, 350, 382, 8, BLUE)
    label(draw, "oops", 738, 72)


def bunny(draw: ImageDraw.ImageDraw) -> None:
    outline = bezier(
        [
            (392, 610),
            (335, 485),
            (398, 374),
            (480, 405),
            (480, 405),
            (445, 155),
            (520, 365),
            (520, 365),
            (620, 160),
            (602, 410),
            (705, 475),
            (670, 650),
            (520, 690),
            (370, 660),
            (305, 590),
            (392, 610),
        ]
    )
    stroke(draw, outline)
    face(draw, (455, 510), (570, 514), (515, 552))
    cheek(draw, 410, 562)
    stroke(draw, [(672, 408), (742, 365), (790, 392), (756, 438)], ink_width=8)
    dot(draw, 764, 398, 10, BLUE)
    label(draw, "almost", 742, 58)


def duck(draw: ImageDraw.ImageDraw) -> None:
    outline = bezier(
        [
            (300, 560),
            (318, 415),
            (450, 370),
            (520, 450),
            (520, 450),
            (560, 370),
            (675, 420),
            (650, 520),
            (650, 520),
            (810, 548),
            (710, 608),
            (630, 580),
            (630, 580),
            (560, 715),
            (330, 690),
            (300, 560),
        ]
    )
    stroke(draw, outline)
    dot(draw, 462, 474, r=12)
    stroke(draw, [(575, 500), (680, 530), (575, 560)], ink_width=10)
    stroke(draw, [(330, 710), (455, 738), (650, 725), (760, 700)], ink_width=8)
    cheek(draw, 405, 535)
    dot(draw, 750, 350, 7, PINK)
    label(draw, "tiny chaos", 750, 52)


def save_design(name: str, draw_func) -> Path:
    image = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    draw_func(draw)
    image = image.resize((CANVAS, CANVAS), Image.Resampling.LANCZOS)
    path = OUTPUT_DIR / name
    image.save(path)
    return path


def make_overview(files: list[Path]) -> None:
    thumb = 260
    pad = 24
    label_h = 34
    canvas = Image.new("RGB", (len(files) * (thumb + pad) + pad, thumb + label_h + pad * 2), "white")
    draw = ImageDraw.Draw(canvas)
    for i, path in enumerate(files):
        img = Image.open(path).convert("RGBA")
        bg = Image.new("RGBA", img.size, (245, 245, 245, 255))
        bg.paste(img, (0, 0), img)
        bg.thumbnail((thumb, thumb), Image.Resampling.LANCZOS)
        x0 = pad + i * (thumb + pad)
        x = x0 + (thumb - bg.width) // 2
        y = pad + (thumb - bg.height) // 2
        canvas.paste(bg.convert("RGB"), (x, y))
        draw.text((x0, pad + thumb + 8), f"{i + 1}. {path.stem}", fill=(20, 20, 20))
    canvas.save(OVERVIEW, quality=92)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files = [
        save_design("refined_001_cat_not_today.png", cat),
        save_design("refined_002_bear_hmm.png", bear),
        save_design("refined_003_dog_oops.png", dog),
        save_design("refined_004_bunny_almost.png", bunny),
        save_design("refined_005_duck_tiny_chaos.png", duck),
    ]
    make_overview(files)
    print(f"Saved {len(files)} image(s) to {OUTPUT_DIR}")
    print(f"Overview: {OVERVIEW}")


if __name__ == "__main__":
    main()
