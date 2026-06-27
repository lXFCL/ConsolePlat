from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "\u5370\u82b1\u56fe_\u900f\u660e\u5e95" / "\u4e00\u7b14\u753b\u4e11\u840c\u5c0f\u52a8\u7269\u6587\u5b57_5\u6b3e_2026-06-10"
OVERVIEW = OUTPUT_DIR / "_overview.jpg"

CANVAS = 1024
SCALE = 3
SIZE = CANVAS * SCALE

INK = (29, 28, 25, 255)
CREAM = (252, 245, 218, 255)
PINK = (239, 128, 145, 255)
BLUE = (111, 160, 188, 255)
GREEN = (118, 164, 118, 255)


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


def sample_curve(points: list[tuple[int, int]], steps: int = 16) -> list[tuple[int, int]]:
    if len(points) < 4:
        return points
    sampled: list[tuple[int, int]] = []
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
            sampled.append((int(x), int(y)))
    sampled.append(points[-1])
    return sampled


def stroke(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], ink_width: int = 14) -> None:
    scaled = pts(points)
    under = ink_width + 17
    draw.line(scaled, fill=CREAM, width=p(under), joint="curve")
    for x, y in scaled:
        r = p(under // 2)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=CREAM)
    draw.line(scaled, fill=INK, width=p(ink_width), joint="curve")
    for x, y in scaled:
        r = p(ink_width // 2)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=INK)


def dot(draw: ImageDraw.ImageDraw, x: int, y: int, r: int = 11, color=INK) -> None:
    draw.ellipse((p(x - r), p(y - r), p(x + r), p(y + r)), fill=color)


def tiny_text(draw: ImageDraw.ImageDraw, text: str, y: int, size: int = 66) -> None:
    fnt = font(size)
    bbox = draw.textbbox((0, 0), text, font=fnt, stroke_width=p(8))
    x = (SIZE - (bbox[2] - bbox[0])) // 2
    draw.text((x, p(y)), text, font=fnt, fill=INK, stroke_width=p(8), stroke_fill=CREAM)


def cheek(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    dot(draw, x, y, 14, PINK)


def cat(draw: ImageDraw.ImageDraw) -> None:
    path = sample_curve(
        [
            (292, 555),
            (250, 455),
            (330, 345),
            (418, 386),
            (420, 386),
            (440, 245),
            (500, 386),
            (500, 386),
            (610, 250),
            (628, 405),
            (742, 445),
            (760, 630),
            (550, 675),
            (380, 650),
            (265, 610),
            (292, 555),
        ],
        steps=20,
    )
    stroke(draw, path)
    dot(draw, 452, 493)
    dot(draw, 585, 480)
    stroke(draw, [(518, 515), (510, 548), (548, 540)], ink_width=9)
    stroke(draw, [(330, 535), (238, 505)], ink_width=8)
    stroke(draw, [(680, 515), (775, 488)], ink_width=8)
    cheek(draw, 395, 555)
    dot(draw, 725, 330, 7, PINK)
    dot(draw, 755, 352, 5, PINK)
    tiny_text(draw, "not today", 735, 58)


def dog(draw: ImageDraw.ImageDraw) -> None:
    path = sample_curve(
        [
            (250, 465),
            (285, 310),
            (425, 330),
            (410, 500),
            (410, 500),
            (430, 325),
            (555, 310),
            (595, 435),
            (595, 435),
            (720, 300),
            (782, 485),
            (664, 610),
            (664, 610),
            (520, 720),
            (330, 660),
            (250, 465),
        ],
        steps=20,
    )
    stroke(draw, path)
    dot(draw, 438, 492)
    dot(draw, 575, 486)
    stroke(draw, [(495, 535), (528, 552), (505, 575)], ink_width=9)
    stroke(draw, [(690, 655), (775, 690), (820, 655)], ink_width=10)
    dot(draw, 325, 380, 10, BLUE)
    cheek(draw, 620, 545)
    tiny_text(draw, "oops", 740, 72)


def bear(draw: ImageDraw.ImageDraw) -> None:
    path = sample_curve(
        [
            (333, 528),
            (285, 405),
            (350, 300),
            (430, 350),
            (430, 350),
            (480, 260),
            (545, 348),
            (545, 348),
            (620, 260),
            (675, 370),
            (724, 450),
            (710, 650),
            (525, 682),
            (340, 640),
            (278, 565),
            (333, 528),
        ],
        steps=20,
    )
    stroke(draw, path)
    dot(draw, 448, 477)
    dot(draw, 574, 490)
    stroke(draw, [(510, 520), (495, 555), (535, 568), (555, 540)], ink_width=9)
    stroke(draw, [(700, 585), (788, 610), (820, 565)], ink_width=10)
    dot(draw, 815, 548, 9, GREEN)
    cheek(draw, 388, 545)
    tiny_text(draw, "hmm", 740, 72)


def bunny(draw: ImageDraw.ImageDraw) -> None:
    path = sample_curve(
        [
            (390, 610),
            (325, 490),
            (390, 365),
            (480, 395),
            (480, 395),
            (430, 120),
            (518, 355),
            (518, 355),
            (620, 115),
            (598, 405),
            (718, 468),
            (675, 660),
            (485, 690),
            (340, 665),
            (288, 590),
            (390, 610),
        ],
        steps=20,
    )
    stroke(draw, path)
    dot(draw, 455, 500)
    dot(draw, 570, 508)
    stroke(draw, [(515, 530), (520, 565), (480, 555)], ink_width=9)
    stroke(draw, [(668, 405), (740, 365), (788, 390), (755, 438)], ink_width=8)
    dot(draw, 765, 398, 11, BLUE)
    cheek(draw, 410, 555)
    tiny_text(draw, "almost", 742, 62)


def duck(draw: ImageDraw.ImageDraw) -> None:
    path = sample_curve(
        [
            (285, 560),
            (300, 405),
            (450, 355),
            (515, 438),
            (515, 438),
            (560, 345),
            (695, 410),
            (655, 520),
            (655, 520),
            (820, 542),
            (722, 605),
            (635, 582),
            (635, 582),
            (560, 735),
            (320, 705),
            (285, 560),
        ],
        steps=20,
    )
    stroke(draw, path)
    dot(draw, 465, 470)
    stroke(draw, [(585, 492), (682, 520), (588, 552)], ink_width=10)
    stroke(draw, [(300, 710), (440, 745), (650, 730), (755, 705)], ink_width=9)
    dot(draw, 750, 350, 8, PINK)
    dot(draw, 785, 382, 5, PINK)
    cheek(draw, 400, 535)
    tiny_text(draw, "tiny chaos", 750, 54)


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
        save_design("oneline_001_cat_not_today.png", cat),
        save_design("oneline_002_dog_oops.png", dog),
        save_design("oneline_003_bear_hmm.png", bear),
        save_design("oneline_004_bunny_almost.png", bunny),
        save_design("oneline_005_duck_tiny_chaos.png", duck),
    ]
    make_overview(files)
    print(f"Saved {len(files)} image(s) to {OUTPUT_DIR}")
    print(f"Overview: {OVERVIEW}")


if __name__ == "__main__":
    main()
