from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "\u5370\u82b1\u56fe_\u900f\u660e\u5e95" / "\u624b\u7ed8\u53ef\u7231\u6781\u7b80\u5c0f\u52a8\u7269\u6587\u5b57_5\u6b3e_2026-06-10"
OVERVIEW = OUTPUT_DIR / "_overview.jpg"

CANVAS = 1024
INK = (28, 28, 26, 255)
CREAM = (250, 244, 220, 255)
PINK = (242, 151, 154, 255)
BLUE = (142, 183, 207, 255)
GREEN = (139, 180, 142, 255)
YELLOW = (246, 211, 109, 255)


def font(size: int) -> ImageFont.ImageFont:
    for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def label(draw: ImageDraw.ImageDraw, text: str, y: int, size: int = 68) -> None:
    fnt = font(size)
    bbox = draw.textbbox((0, 0), text, font=fnt, stroke_width=7)
    x = (CANVAS - (bbox[2] - bbox[0])) // 2
    draw.text((x, y), text, font=fnt, fill=INK, stroke_width=7, stroke_fill=CREAM)


def heart(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, fill=PINK) -> None:
    r = size // 4
    draw.ellipse((cx - 2 * r, cy - r, cx, cy + r), fill=fill, outline=INK, width=5)
    draw.ellipse((cx, cy - r, cx + 2 * r, cy + r), fill=fill, outline=INK, width=5)
    draw.polygon([(cx - 2 * r, cy), (cx + 2 * r, cy), (cx, cy + 3 * r)], fill=fill, outline=INK)


def sparkle(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int) -> None:
    draw.line((cx, cy - size, cx, cy + size), fill=INK, width=7)
    draw.line((cx - size, cy, cx + size, cy), fill=INK, width=7)


def bow(draw: ImageDraw.ImageDraw, cx: int, cy: int) -> None:
    draw.polygon([(cx, cy), (cx - 85, cy - 45), (cx - 85, cy + 45)], fill=PINK, outline=INK)
    draw.polygon([(cx, cy), (cx + 85, cy - 45), (cx + 85, cy + 45)], fill=PINK, outline=INK)
    draw.ellipse((cx - 24, cy - 24, cx + 24, cy + 24), fill=YELLOW, outline=INK, width=6)


def cat_in_box(draw: ImageDraw.ImageDraw) -> None:
    draw.rounded_rectangle((330, 480, 700, 675), radius=28, fill=BLUE, outline=INK, width=16)
    draw.ellipse((365, 250, 665, 545), fill=CREAM, outline=INK, width=18)
    draw.polygon([(395, 285), (445, 180), (485, 310)], fill=CREAM, outline=INK)
    draw.polygon([(545, 310), (585, 180), (635, 285)], fill=CREAM, outline=INK)
    draw.ellipse((455, 385, 485, 415), fill=INK)
    draw.ellipse((545, 385, 575, 415), fill=INK)
    draw.arc((492, 425, 538, 470), 25, 155, fill=INK, width=9)
    draw.line((515, 448, 515, 485), fill=INK, width=8)
    heart(draw, 700, 310, 58)
    sparkle(draw, 300, 365, 24)
    label(draw, "LAZY", 740)


def puppy_with_bone(draw: ImageDraw.ImageDraw) -> None:
    draw.ellipse((340, 300, 700, 640), fill=CREAM, outline=INK, width=18)
    draw.ellipse((285, 365, 400, 595), fill=YELLOW, outline=INK, width=16)
    draw.ellipse((635, 365, 750, 595), fill=YELLOW, outline=INK, width=16)
    draw.rounded_rectangle((420, 235, 615, 300), radius=34, fill=BLUE, outline=INK, width=12)
    draw.ellipse((445, 420, 475, 450), fill=INK)
    draw.ellipse((565, 420, 595, 450), fill=INK)
    draw.ellipse((505, 470, 545, 508), fill=INK)
    draw.arc((482, 500, 520, 545), 0, 85, fill=INK, width=9)
    draw.arc((520, 500, 560, 545), 95, 180, fill=INK, width=9)
    draw.line((665, 675, 780, 675), fill=INK, width=14)
    draw.ellipse((630, 642, 685, 697), fill=CREAM, outline=INK, width=10)
    draw.ellipse((760, 642, 815, 697), fill=CREAM, outline=INK, width=10)
    label(draw, "HEY", 740)


def bear_cookie(draw: ImageDraw.ImageDraw) -> None:
    draw.ellipse((350, 285, 690, 630), fill=CREAM, outline=INK, width=18)
    draw.ellipse((325, 250, 430, 355), fill=CREAM, outline=INK, width=16)
    draw.ellipse((610, 250, 715, 355), fill=CREAM, outline=INK, width=16)
    bow(draw, 520, 245)
    draw.ellipse((440, 420, 470, 450), fill=INK)
    draw.ellipse((565, 420, 595, 450), fill=INK)
    draw.ellipse((490, 455, 545, 510), fill=CREAM, outline=INK, width=9)
    draw.arc((485, 500, 550, 545), 20, 160, fill=INK, width=8)
    draw.ellipse((645, 520, 755, 630), fill=YELLOW, outline=INK, width=10)
    for dot in [(680, 552), (722, 565), (700, 605)]:
        draw.ellipse((dot[0] - 8, dot[1] - 8, dot[0] + 8, dot[1] + 8), fill=INK)
    label(draw, "YUM", 735)


def bunny_balloon(draw: ImageDraw.ImageDraw) -> None:
    draw.ellipse((375, 345, 650, 650), fill=CREAM, outline=INK, width=18)
    draw.rounded_rectangle((395, 145, 465, 380), radius=38, fill=CREAM, outline=INK, width=16)
    draw.rounded_rectangle((550, 145, 620, 380), radius=38, fill=CREAM, outline=INK, width=16)
    draw.ellipse((442, 470, 472, 500), fill=INK)
    draw.ellipse((552, 470, 582, 500), fill=INK)
    draw.line((512, 510, 512, 550), fill=INK, width=8)
    draw.arc((470, 530, 512, 570), 0, 85, fill=INK, width=8)
    draw.arc((512, 530, 555, 570), 95, 180, fill=INK, width=8)
    draw.ellipse((705, 245, 810, 360), fill=PINK, outline=INK, width=10)
    draw.line((755, 360, 660, 585), fill=INK, width=6)
    draw.ellipse((300, 555, 385, 650), fill=GREEN, outline=INK, width=12)
    draw.line((325, 605, 368, 605), fill=INK, width=8)
    label(draw, "HOP", 730)


def hamster_cup(draw: ImageDraw.ImageDraw) -> None:
    draw.rounded_rectangle((345, 510, 690, 690), radius=45, fill=BLUE, outline=INK, width=16)
    draw.arc((675, 545, 810, 665), -80, 90, fill=INK, width=16)
    draw.ellipse((390, 280, 640, 550), fill=CREAM, outline=INK, width=18)
    draw.ellipse((375, 260, 450, 335), fill=CREAM, outline=INK, width=14)
    draw.ellipse((580, 260, 655, 335), fill=CREAM, outline=INK, width=14)
    draw.ellipse((455, 395, 485, 425), fill=INK)
    draw.ellipse((545, 395, 575, 425), fill=INK)
    draw.ellipse((425, 455, 460, 490), fill=PINK)
    draw.ellipse((570, 455, 605, 490), fill=PINK)
    draw.arc((485, 455, 545, 510), 20, 160, fill=INK, width=9)
    draw.arc((300, 320, 355, 375), 50, 310, fill=INK, width=8)
    draw.arc((680, 320, 735, 375), 230, 130, fill=INK, width=8)
    label(draw, "COZY", 740, size=64)


def save_design(name: str, draw_func) -> Path:
    image = Image.new("RGBA", (CANVAS, CANVAS), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    draw_func(draw)
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
        save_design("cute_001_cat_box_lazy.png", cat_in_box),
        save_design("cute_002_puppy_bone_hey.png", puppy_with_bone),
        save_design("cute_003_bear_cookie_yum.png", bear_cookie),
        save_design("cute_004_bunny_balloon_hop.png", bunny_balloon),
        save_design("cute_005_hamster_cup_cozy.png", hamster_cup),
    ]
    make_overview(files)
    print(f"Saved {len(files)} image(s) to {OUTPUT_DIR}")
    print(f"Overview: {OVERVIEW}")


if __name__ == "__main__":
    main()
