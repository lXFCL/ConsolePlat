from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "\u5370\u82b1\u56fe_\u900f\u660e\u5e95" / "\u624b\u7ed8\u6781\u7b80\u5c0f\u52a8\u7269\u6587\u5b57_5\u6b3e_2026-06-10"
OVERVIEW = OUTPUT_DIR / "_overview.jpg"

CANVAS = 1024
BLACK = (28, 28, 26, 255)
CREAM = (250, 244, 220, 255)
PINK = (241, 150, 145, 255)
BLUE = (141, 178, 200, 255)
GREEN = (139, 171, 132, 255)


def font(size: int) -> ImageFont.ImageFont:
    for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def draw_text_center(draw: ImageDraw.ImageDraw, text: str, y: int, size: int = 72) -> None:
    fnt = font(size)
    bbox = draw.textbbox((0, 0), text, font=fnt, stroke_width=8)
    x = (CANVAS - (bbox[2] - bbox[0])) // 2
    draw.text((x, y), text, font=fnt, fill=BLACK, stroke_width=8, stroke_fill=CREAM)


def cat(draw: ImageDraw.ImageDraw) -> None:
    draw.polygon([(365, 310), (430, 205), (470, 335)], fill=CREAM, outline=BLACK)
    draw.polygon([(555, 335), (595, 205), (660, 310)], fill=CREAM, outline=BLACK)
    draw.ellipse((320, 275, 705, 635), fill=CREAM, outline=BLACK, width=18)
    draw.ellipse((420, 420, 455, 455), fill=BLACK)
    draw.ellipse((570, 420, 605, 455), fill=BLACK)
    draw.arc((480, 455, 545, 520), 20, 160, fill=BLACK, width=12)
    draw.line((510, 480, 510, 525), fill=BLACK, width=10)
    draw.arc((460, 505, 510, 555), 0, 90, fill=BLACK, width=10)
    draw.arc((510, 505, 560, 555), 90, 180, fill=BLACK, width=10)
    draw.line((350, 490, 270, 470), fill=BLACK, width=8)
    draw.line((350, 530, 270, 535), fill=BLACK, width=8)
    draw.line((675, 490, 755, 470), fill=BLACK, width=8)
    draw.line((675, 530, 755, 535), fill=BLACK, width=8)
    draw_text_center(draw, "SLOW", 700)


def puppy(draw: ImageDraw.ImageDraw) -> None:
    draw.ellipse((315, 285, 710, 640), fill=CREAM, outline=BLACK, width=18)
    draw.ellipse((265, 325, 390, 570), fill=BLUE, outline=BLACK, width=16)
    draw.ellipse((635, 325, 760, 570), fill=BLUE, outline=BLACK, width=16)
    draw.ellipse((425, 420, 460, 455), fill=BLACK)
    draw.ellipse((565, 420, 600, 455), fill=BLACK)
    draw.ellipse((485, 470, 540, 515), fill=BLACK)
    draw.arc((465, 505, 512, 555), 0, 85, fill=BLACK, width=10)
    draw.arc((512, 505, 560, 555), 95, 180, fill=BLACK, width=10)
    draw.arc((610, 555, 705, 680), 180, 350, fill=BLACK, width=14)
    draw_text_center(draw, "HI", 700)


def bear(draw: ImageDraw.ImageDraw) -> None:
    draw.ellipse((330, 280, 695, 640), fill=CREAM, outline=BLACK, width=18)
    draw.ellipse((315, 235, 425, 345), fill=CREAM, outline=BLACK, width=16)
    draw.ellipse((600, 235, 710, 345), fill=CREAM, outline=BLACK, width=16)
    draw.ellipse((430, 415, 465, 450), fill=BLACK)
    draw.ellipse((560, 415, 595, 450), fill=BLACK)
    draw.ellipse((485, 470, 540, 515), fill=BLACK)
    draw.arc((460, 500, 515, 555), 0, 80, fill=BLACK, width=10)
    draw.arc((512, 500, 568, 555), 100, 180, fill=BLACK, width=10)
    draw.ellipse((710, 520, 745, 555), fill=GREEN, outline=BLACK, width=6)
    draw.ellipse((745, 520, 780, 555), fill=GREEN, outline=BLACK, width=6)
    draw.ellipse((727, 490, 762, 525), fill=GREEN, outline=BLACK, width=6)
    draw.ellipse((727, 548, 762, 583), fill=GREEN, outline=BLACK, width=6)
    draw.ellipse((735, 528, 755, 548), fill=PINK)
    draw_text_center(draw, "OK", 700)


def bunny(draw: ImageDraw.ImageDraw) -> None:
    draw.ellipse((365, 335, 660, 660), fill=CREAM, outline=BLACK, width=18)
    draw.ellipse((390, 150, 475, 380), fill=CREAM, outline=BLACK, width=16)
    draw.ellipse((550, 150, 635, 380), fill=CREAM, outline=BLACK, width=16)
    draw.ellipse((440, 460, 475, 495), fill=BLACK)
    draw.ellipse((550, 460, 585, 495), fill=BLACK)
    draw.line((510, 500, 510, 545), fill=BLACK, width=9)
    draw.arc((465, 525, 510, 570), 0, 90, fill=BLACK, width=9)
    draw.arc((510, 525, 555, 570), 90, 180, fill=BLACK, width=9)
    draw.arc((295, 560, 390, 660), 0, 180, fill=BLACK, width=12)
    draw.line((310, 610, 375, 610), fill=BLACK, width=12)
    draw_text_center(draw, "YES", 710)


def hamster(draw: ImageDraw.ImageDraw) -> None:
    draw.ellipse((330, 285, 695, 655), fill=CREAM, outline=BLACK, width=18)
    draw.ellipse((325, 270, 420, 365), fill=CREAM, outline=BLACK, width=16)
    draw.ellipse((605, 270, 700, 365), fill=CREAM, outline=BLACK, width=16)
    draw.ellipse((435, 430, 470, 465), fill=BLACK)
    draw.ellipse((555, 430, 590, 465), fill=BLACK)
    draw.ellipse((385, 505, 425, 545), fill=PINK)
    draw.ellipse((600, 505, 640, 545), fill=PINK)
    draw.arc((475, 500, 550, 560), 20, 160, fill=BLACK, width=10)
    draw.arc((380, 610, 645, 760), 200, 340, fill=BLUE, width=22)
    draw_text_center(draw, "SMILE", 720, size=64)


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
        save_design("simple_001_cat_slow.png", cat),
        save_design("simple_002_puppy_hi.png", puppy),
        save_design("simple_003_bear_ok.png", bear),
        save_design("simple_004_bunny_yes.png", bunny),
        save_design("simple_005_hamster_smile.png", hamster),
    ]
    make_overview(files)
    print(f"Saved {len(files)} image(s) to {OUTPUT_DIR}")
    print(f"Overview: {OVERVIEW}")


if __name__ == "__main__":
    main()
