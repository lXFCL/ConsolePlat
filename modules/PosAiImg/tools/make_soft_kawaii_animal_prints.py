from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "\u5370\u82b1\u56fe_\u900f\u660e\u5e95" / "\u8f6f\u840c\u8d34\u7eb8\u98ce\u5c0f\u52a8\u7269\u6587\u5b57_5\u6b3e_2026-06-10"
OVERVIEW = OUTPUT_DIR / "_overview.jpg"

SCALE = 3
CANVAS = 1024
SIZE = CANVAS * SCALE

INK = (34, 32, 29, 255)
CREAM = (255, 248, 224, 255)
CAT = (244, 229, 190, 255)
DOG = (238, 210, 150, 255)
BEAR = (205, 151, 96, 255)
BUNNY = (252, 242, 225, 255)
DUCK = (250, 210, 91, 255)
PINK = (246, 153, 164, 255)
BLUE = (139, 190, 213, 255)
GREEN = (137, 181, 135, 255)
YELLOW = (246, 211, 109, 255)
ORANGE = (238, 142, 72, 255)
WHITE = (255, 255, 249, 255)


def p(value: int) -> int:
    return value * SCALE


def box(values: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    return tuple(p(v) for v in values)


def pts(values: list[tuple[int, int]]) -> list[tuple[int, int]]:
    return [(p(x), p(y)) for x, y in values]


def width(value: int) -> int:
    return max(1, p(value))


def font(size: int) -> ImageFont.ImageFont:
    for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, p(size))
        except OSError:
            pass
    return ImageFont.load_default()


def draw_text(draw: ImageDraw.ImageDraw, text: str, y: int, size: int = 74) -> None:
    fnt = font(size)
    bbox = draw.textbbox((0, 0), text, font=fnt, stroke_width=width(9))
    x = (SIZE - (bbox[2] - bbox[0])) // 2
    draw.text((x, p(y)), text, font=fnt, fill=INK, stroke_width=width(9), stroke_fill=CREAM)


def ellipse(draw: ImageDraw.ImageDraw, xy, fill, outline=INK, w=14) -> None:
    draw.ellipse(box(xy), fill=fill, outline=outline, width=width(w))


def rounded(draw: ImageDraw.ImageDraw, xy, radius, fill, outline=INK, w=14) -> None:
    draw.rounded_rectangle(box(xy), radius=p(radius), fill=fill, outline=outline, width=width(w))


def line(draw: ImageDraw.ImageDraw, xy, fill=INK, w=10) -> None:
    draw.line([p(v) for point in xy for v in point], fill=fill, width=width(w), joint="curve")


def heart(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int) -> None:
    r = size // 4
    draw.ellipse(box((cx - 2 * r, cy - r, cx, cy + r)), fill=PINK, outline=INK, width=width(5))
    draw.ellipse(box((cx, cy - r, cx + 2 * r, cy + r)), fill=PINK, outline=INK, width=width(5))
    draw.polygon(pts([(cx - 2 * r, cy), (cx + 2 * r, cy), (cx, cy + 3 * r)]), fill=PINK, outline=INK)


def sparkle(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int) -> None:
    draw.line((p(cx), p(cy - size), p(cx), p(cy + size)), fill=INK, width=width(6))
    draw.line((p(cx - size), p(cy), p(cx + size), p(cy)), fill=INK, width=width(6))


def sleepy_cat(draw: ImageDraw.ImageDraw) -> None:
    rounded(draw, (285, 360, 750, 655), 150, CAT, w=16)
    draw.polygon(pts([(355, 380), (410, 265), (468, 400)]), fill=CAT, outline=INK)
    draw.line(pts([(355, 380), (410, 265), (468, 400)]), fill=INK, width=width(16), joint="curve")
    draw.polygon(pts([(570, 400), (630, 265), (685, 385)]), fill=CAT, outline=INK)
    draw.line(pts([(570, 400), (630, 265), (685, 385)]), fill=INK, width=width(16), joint="curve")
    ellipse(draw, (455, 500, 582, 610), WHITE, w=10)
    draw.arc(box((375, 450, 455, 500)), 15, 160, fill=INK, width=width(10))
    draw.arc(box((590, 450, 670, 500)), 20, 165, fill=INK, width=width(10))
    draw.polygon(pts([(512, 512), (485, 540), (540, 540)]), fill=PINK, outline=INK)
    draw.arc(box((462, 550, 512, 595)), 0, 80, fill=INK, width=width(8))
    draw.arc(box((512, 550, 562, 595)), 100, 180, fill=INK, width=width(8))
    draw.arc(box((300, 545, 470, 720)), 20, 230, fill=INK, width=width(16))
    heart(draw, 720, 315, 52)
    sparkle(draw, 285, 350, 22)
    draw_text(draw, "nap time", 725, 58)


def flower_puppy(draw: ImageDraw.ImageDraw) -> None:
    ellipse(draw, (345, 300, 690, 640), DOG, w=16)
    ellipse(draw, (250, 370, 385, 620), DOG, w=16)
    ellipse(draw, (650, 370, 785, 620), DOG, w=16)
    ellipse(draw, (435, 420, 475, 460), INK, outline=INK, w=1)
    ellipse(draw, (565, 420, 605, 460), INK, outline=INK, w=1)
    ellipse(draw, (496, 480, 544, 520), INK, outline=INK, w=1)
    draw.arc(box((470, 515, 520, 565)), 0, 85, fill=INK, width=width(9))
    draw.arc(box((520, 515, 570, 565)), 95, 180, fill=INK, width=width(9))
    rounded(draw, (405, 260, 625, 325), 34, BLUE, w=11)
    draw.line((p(680), p(620), p(775), p(710)), fill=INK, width=width(8))
    for cx, cy in [(800, 710), (760, 710), (780, 680), (780, 740)]:
        ellipse(draw, (cx - 22, cy - 22, cx + 22, cy + 22), PINK, w=5)
    ellipse(draw, (765, 695, 795, 725), YELLOW, w=5)
    draw_text(draw, "hello", 725, 68)


def honey_bear(draw: ImageDraw.ImageDraw) -> None:
    ellipse(draw, (360, 330, 690, 665), BEAR, w=16)
    ellipse(draw, (330, 292, 430, 392), BEAR, w=14)
    ellipse(draw, (620, 292, 720, 392), BEAR, w=14)
    ellipse(draw, (440, 460, 480, 500), INK, outline=INK, w=1)
    ellipse(draw, (565, 460, 605, 500), INK, outline=INK, w=1)
    ellipse(draw, (485, 510, 555, 570), CREAM, w=8)
    draw.arc(box((495, 535, 545, 575)), 20, 160, fill=INK, width=width(8))
    rounded(draw, (610, 560, 765, 700), 32, YELLOW, w=12)
    rounded(draw, (630, 520, 745, 570), 20, ORANGE, w=10)
    draw.text((p(655), p(595)), "H", font=font(52), fill=INK)
    draw.arc(box((285, 430, 390, 555)), 80, 270, fill=INK, width=width(15))
    heart(draw, 315, 360, 46)
    draw_text(draw, "sweet", 745, 66)


def carrot_bunny(draw: ImageDraw.ImageDraw) -> None:
    ellipse(draw, (375, 350, 665, 665), BUNNY, w=16)
    rounded(draw, (405, 150, 480, 395), 38, BUNNY, w=15)
    rounded(draw, (555, 150, 630, 395), 38, BUNNY, w=15)
    ellipse(draw, (445, 480, 480, 515), INK, outline=INK, w=1)
    ellipse(draw, (555, 480, 590, 515), INK, outline=INK, w=1)
    draw.line((p(520), p(525), p(520), p(565)), fill=INK, width=width(8))
    draw.arc(box((480, 548, 520, 590)), 0, 80, fill=INK, width=width(8))
    draw.arc(box((520, 548, 560, 590)), 100, 180, fill=INK, width=width(8))
    draw.polygon(pts([(675, 560), (810, 605), (685, 675)]), fill=ORANGE, outline=INK)
    draw.line(pts([(710, 575), (755, 600), (705, 635)]), fill=INK, width=width(6))
    draw.polygon(pts([(800, 595), (865, 550), (838, 620)]), fill=GREEN, outline=INK)
    sparkle(draw, 305, 425, 24)
    draw_text(draw, "lucky", 745, 66)


def duck_puddle(draw: ImageDraw.ImageDraw) -> None:
    ellipse(draw, (355, 360, 705, 650), DUCK, w=16)
    ellipse(draw, (410, 255, 630, 475), DUCK, w=16)
    draw.polygon(pts([(515, 405), (645, 440), (515, 485)]), fill=ORANGE, outline=INK)
    ellipse(draw, (455, 340, 490, 375), INK, outline=INK, w=1)
    rounded(draw, (300, 640, 760, 720), 40, BLUE, w=13)
    draw.arc(box((365, 520, 465, 620)), 220, 30, fill=INK, width=width(13))
    draw.arc(box((585, 520, 685, 620)), 150, 320, fill=INK, width=width(13))
    for cx, cy in [(335, 310), (720, 340), (760, 395)]:
        sparkle(draw, cx, cy, 20)
    draw_text(draw, "sunny", 760, 66)


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
        save_design("soft_001_sleepy_cat_nap_time.png", sleepy_cat),
        save_design("soft_002_flower_puppy_hello.png", flower_puppy),
        save_design("soft_003_honey_bear_sweet.png", honey_bear),
        save_design("soft_004_carrot_bunny_lucky.png", carrot_bunny),
        save_design("soft_005_duck_puddle_sunny.png", duck_puddle),
    ]
    make_overview(files)
    print(f"Saved {len(files)} image(s) to {OUTPUT_DIR}")
    print(f"Overview: {OVERVIEW}")


if __name__ == "__main__":
    main()
