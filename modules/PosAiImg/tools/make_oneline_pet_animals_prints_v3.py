from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "\u5370\u82b1\u56fe_\u900f\u660e\u5e95" / "\u4e00\u7b14\u753b\u5c0f\u52a8\u7269\u65b0\u8f6e\u5ed3_5\u6b3e_2026-06-10"
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


def face(draw: ImageDraw.ImageDraw, left_eye: tuple[int, int], right_eye: tuple[int, int], mouth: tuple[int, int]) -> None:
    dot(draw, *left_eye, r=12)
    dot(draw, *right_eye, r=12)
    x, y = mouth
    stroke(draw, bezier([(x - 6, y), (x - 38, y - 18), (x - 38, y + 28), (x - 5, y + 15)]), ink_width=7)
    stroke(draw, bezier([(x + 6, y), (x + 38, y - 18), (x + 38, y + 28), (x + 5, y + 15)]), ink_width=7)
    cheek_y = max(left_eye[1], right_eye[1]) + 62
    dot(draw, left_eye[0] - 42, cheek_y, 13, PINK)
    dot(draw, right_eye[0] + 42, cheek_y, 13, PINK)


def label(draw: ImageDraw.ImageDraw, text: str, y: int, size: int = 58) -> None:
    fnt = font(size)
    bbox = draw.textbbox((0, 0), text, font=fnt, stroke_width=p(7))
    x = (SIZE - (bbox[2] - bbox[0])) // 2
    draw.text((x, p(y)), text, font=fnt, fill=INK, stroke_width=p(7), stroke_fill=CREAM)


def cat_loaf(draw: ImageDraw.ImageDraw) -> None:
    outline = bezier(
        [
            (250, 590),
            (270, 420),
            (405, 365),
            (470, 425),
            (470, 425),
            (500, 290),
            (555, 430),
            (555, 430),
            (660, 330),
            (720, 455),
            (785, 560),
            (710, 690),
            (495, 702),
            (310, 665),
            (245, 610),
            (250, 590),
        ]
    )
    stroke(draw, outline)
    face(draw, (455, 525), (590, 520), (525, 565))
    stroke(draw, [(345, 560), (250, 548)], ink_width=8)
    stroke(draw, [(685, 552), (775, 535)], ink_width=8)
    dot(draw, 735, 375, 7, GREEN)
    label(draw, "lazy mode", 748, 52)


def bunny_bean(draw: ImageDraw.ImageDraw) -> None:
    outline = bezier(
        [
            (280, 610),
            (300, 455),
            (455, 410),
            (525, 475),
            (525, 475),
            (515, 185),
            (590, 405),
            (590, 405),
            (700, 220),
            (670, 500),
            (735, 570),
            (680, 690),
            (470, 690),
            (310, 660),
            (275, 620),
            (280, 610),
        ]
    )
    stroke(draw, outline)
    face(draw, (465, 535), (590, 532), (528, 575))
    dot(draw, 330, 430, 7, BLUE)
    label(draw, "no hurry", 748, 52)


def bear_drop(draw: ImageDraw.ImageDraw) -> None:
    outline = bezier(
        [
            (375, 595),
            (285, 470),
            (350, 335),
            (450, 365),
            (450, 365),
            (465, 265),
            (540, 350),
            (540, 350),
            (635, 278),
            (700, 405),
            (760, 540),
            (660, 705),
            (500, 705),
            (350, 660),
            (300, 585),
            (375, 595),
        ]
    )
    stroke(draw, outline)
    face(draw, (470, 510), (590, 518), (532, 560))
    dot(draw, 730, 360, 7, PINK)
    label(draw, "small mood", 750, 52)


def dog_long_ear(draw: ImageDraw.ImageDraw) -> None:
    outline = bezier(
        [
            (300, 510),
            (305, 355),
            (430, 325),
            (455, 500),
            (455, 500),
            (505, 358),
            (610, 360),
            (628, 505),
            (628, 505),
            (725, 330),
            (790, 520),
            (660, 662),
            (510, 695),
            (350, 635),
            (295, 555),
            (300, 510),
        ]
    )
    stroke(draw, outline)
    face(draw, (470, 525), (585, 522), (528, 568))
    dot(draw, 370, 335, 7, BLUE)
    label(draw, "just ok", 748, 58)


def cat_triangle(draw: ImageDraw.ImageDraw) -> None:
    outline = bezier(
        [
            (355, 625),
            (300, 500),
            (372, 390),
            (455, 412),
            (455, 412),
            (405, 285),
            (520, 390),
            (520, 390),
            (675, 300),
            (650, 438),
            (725, 525),
            (690, 675),
            (520, 705),
            (365, 665),
            (300, 610),
            (355, 625),
        ]
    )
    stroke(draw, outline)
    face(draw, (455, 525), (580, 510), (520, 558))
    stroke(draw, [(360, 560), (275, 565)], ink_width=8)
    stroke(draw, [(655, 548), (740, 565)], ink_width=8)
    dot(draw, 318, 390, 7, GREEN)
    label(draw, "weird day", 748, 54)


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
        save_design("petv3_001_cat_loaf_lazy_mode.png", cat_loaf),
        save_design("petv3_002_bunny_bean_no_hurry.png", bunny_bean),
        save_design("petv3_003_bear_drop_small_mood.png", bear_drop),
        save_design("petv3_004_dog_long_ear_just_ok.png", dog_long_ear),
        save_design("petv3_005_cat_triangle_weird_day.png", cat_triangle),
    ]
    make_overview(files)
    print(f"Saved {len(files)} image(s) to {OUTPUT_DIR}")
    print(f"Overview: {OVERVIEW}")


if __name__ == "__main__":
    main()
