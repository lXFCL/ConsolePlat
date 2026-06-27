from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "\u5370\u82b1\u56fe_\u900f\u660e\u5e95" / "\u4e00\u7b14\u753b\u5c0f\u52a8\u7269\u53d8\u4f53_5\u6b3e_2026-06-10"
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


def cat_sleepy(draw: ImageDraw.ImageDraw) -> None:
    outline = bezier(
        [
            (300, 570),
            (285, 430),
            (365, 360),
            (440, 395),
            (440, 395),
            (470, 282),
            (525, 400),
            (525, 400),
            (620, 300),
            (645, 410),
            (715, 475),
            (705, 640),
            (560, 678),
            (390, 650),
            (292, 600),
            (300, 570),
        ]
    )
    stroke(draw, outline)
    face(draw, (455, 500), (580, 498), (520, 540))
    stroke(draw, [(338, 545), (260, 535)], ink_width=8)
    stroke(draw, [(675, 540), (750, 528)], ink_width=8)
    dot(draw, 720, 365, 7, GREEN)
    label(draw, "sleepy", 735)


def bunny_round(draw: ImageDraw.ImageDraw) -> None:
    outline = bezier(
        [
            (368, 610),
            (318, 480),
            (405, 385),
            (500, 420),
            (500, 420),
            (455, 175),
            (535, 380),
            (535, 380),
            (620, 185),
            (625, 430),
            (720, 505),
            (665, 660),
            (520, 682),
            (370, 655),
            (305, 590),
            (368, 610),
        ]
    )
    stroke(draw, outline)
    face(draw, (460, 515), (575, 510), (520, 555))
    dot(draw, 690, 390, 7, BLUE)
    label(draw, "soft nope", 740, 52)


def bear_square(draw: ImageDraw.ImageDraw) -> None:
    outline = bezier(
        [
            (350, 540),
            (315, 430),
            (370, 335),
            (440, 370),
            (440, 370),
            (490, 298),
            (535, 370),
            (535, 370),
            (610, 295),
            (670, 380),
            (720, 470),
            (690, 640),
            (545, 680),
            (385, 640),
            (315, 585),
            (350, 540),
        ]
    )
    stroke(draw, outline)
    face(draw, (455, 500), (575, 500), (515, 542))
    dot(draw, 320, 390, 7, GREEN)
    label(draw, "tiny mood", 738, 52)


def dog_floppy(draw: ImageDraw.ImageDraw) -> None:
    outline = bezier(
        [
            (285, 505),
            (300, 360),
            (420, 345),
            (430, 485),
            (430, 485),
            (470, 350),
            (590, 350),
            (608, 470),
            (608, 470),
            (710, 360),
            (765, 500),
            (660, 625),
            (540, 682),
            (390, 650),
            (292, 575),
            (285, 505),
        ]
    )
    stroke(draw, outline)
    face(draw, (455, 505), (575, 503), (516, 548))
    dot(draw, 355, 370, 7, BLUE)
    label(draw, "ok fine", 740, 56)


def bear_long(draw: ImageDraw.ImageDraw) -> None:
    outline = bezier(
        [
            (365, 545),
            (330, 430),
            (390, 340),
            (455, 365),
            (455, 365),
            (500, 300),
            (542, 365),
            (542, 365),
            (615, 315),
            (675, 390),
            (710, 490),
            (675, 645),
            (535, 700),
            (385, 650),
            (320, 585),
            (365, 545),
        ]
    )
    stroke(draw, outline)
    face(draw, (470, 505), (585, 502), (528, 548))
    dot(draw, 700, 360, 7, PINK)
    label(draw, "meh", 742, 72)


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
        save_design("petv2_001_cat_sleepy.png", cat_sleepy),
        save_design("petv2_002_bunny_soft_nope.png", bunny_round),
        save_design("petv2_003_bear_tiny_mood.png", bear_square),
        save_design("petv2_004_dog_ok_fine.png", dog_floppy),
        save_design("petv2_005_bear_meh.png", bear_long),
    ]
    make_overview(files)
    print(f"Saved {len(files)} image(s) to {OUTPUT_DIR}")
    print(f"Overview: {OVERVIEW}")


if __name__ == "__main__":
    main()
