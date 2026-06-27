from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "印花图_透明底" / "混合拼贴街头风印花_5款_2026-06-15"
OVERVIEW = OUT_DIR / "_overview.jpg"
PROMPT_DIR = ROOT / "生成提示词"
PROMPT_FILE = PROMPT_DIR / "混合拼贴街头风印花_5款_2026-06-15.txt"
FONT_DIR = Path("C:/Windows/Fonts")


@dataclass(frozen=True)
class CollageDesign:
    filename: str
    title: str
    subtitle: str
    number: str
    palette: tuple[tuple[int, int, int, int], ...]
    motif: str
    seed: int
    rotation: float


DESIGNS = [
    CollageDesign(
        filename="01_city_noise.png",
        title="CITY",
        subtitle="NOISE",
        number="NO. 17",
        palette=((24, 24, 24, 255), (246, 240, 220, 255), (207, 55, 50, 255), (44, 105, 145, 255)),
        motif="burst",
        seed=301,
        rotation=-3.0,
    ),
    CollageDesign(
        filename="02_offline_club.png",
        title="OFFLINE",
        subtitle="CLUB",
        number="DROP 02",
        palette=((20, 22, 22, 255), (242, 237, 224, 255), (220, 153, 45, 255), (78, 128, 83, 255)),
        motif="tape",
        seed=302,
        rotation=2.5,
    ),
    CollageDesign(
        filename="03_after_hour.png",
        title="AFTER",
        subtitle="HOUR",
        number="24/7",
        palette=((28, 25, 31, 255), (247, 239, 229, 255), (168, 79, 132, 255), (88, 91, 166, 255)),
        motif="arrow",
        seed=303,
        rotation=-2.0,
    ),
    CollageDesign(
        filename="04_raw_mood.png",
        title="RAW",
        subtitle="MOOD",
        number="TYPE 09",
        palette=((18, 18, 18, 255), (245, 241, 232, 255), (62, 132, 90, 255), (193, 79, 54, 255)),
        motif="circle",
        seed=304,
        rotation=3.5,
    ),
    CollageDesign(
        filename="05_static_summer.png",
        title="STATIC",
        subtitle="SUMMER",
        number="VOL. 5",
        palette=((22, 23, 24, 255), (248, 242, 226, 255), (43, 118, 142, 255), (214, 118, 47, 255)),
        motif="wave",
        seed=305,
        rotation=-2.8,
    ),
]


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONT_DIR / name
    if not path.exists():
        path = FONT_DIR / "arialbd.ttf"
    return ImageFont.truetype(str(path), size=size)


def ragged_polygon(x: int, y: int, w: int, h: int, rng: random.Random, jag: int = 16) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    steps = 8
    for i in range(steps + 1):
        points.append((x + int(w * i / steps), y + rng.randint(-jag, jag)))
    for i in range(1, steps + 1):
        points.append((x + w + rng.randint(-jag, jag), y + int(h * i / steps)))
    for i in range(steps, -1, -1):
        points.append((x + int(w * i / steps), y + h + rng.randint(-jag, jag)))
    for i in range(steps, 0, -1):
        points.append((x + rng.randint(-jag, jag), y + int(h * i / steps)))
    return points


def halftone(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: tuple[int, int, int, int], step: int = 22) -> None:
    left, top, right, bottom = box
    for y in range(top, bottom, step):
        for x in range(left, right, step):
            radius = 3 + ((x + y) // step) % 4
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)


def draw_tape(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: tuple[int, int, int, int], rng: random.Random) -> None:
    left, top, right, bottom = box
    draw.polygon(ragged_polygon(left, top, right - left, bottom - top, rng, 8), fill=color)
    for x in range(left + 18, right, 34):
        draw.line((x, top + 8, x - 12, bottom - 8), fill=(255, 255, 255, 95), width=4)


def draw_starburst(draw: ImageDraw.ImageDraw, cx: int, cy: int, r1: int, r2: int, color: tuple[int, int, int, int]) -> None:
    points = []
    for i in range(18):
        r = r1 if i % 2 == 0 else r2
        angle = -math.pi / 2 + i * math.tau / 18
        points.append((cx + int(math.cos(angle) * r), cy + int(math.sin(angle) * r)))
    draw.polygon(points, fill=color)


def draw_waves(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = box
    for row in range(4):
        y = top + row * 28
        points = []
        for x in range(left, right + 1, 12):
            points.append((x, int(y + math.sin((x - left) / 28) * 9)))
        draw.line(points, fill=color, width=8)


def add_grain(alpha_img: Image.Image, seed: int) -> Image.Image:
    rng = random.Random(seed)
    arr = alpha_img.load()
    width, height = alpha_img.size
    for _ in range(4500):
        x = rng.randrange(width)
        y = rng.randrange(height)
        value = arr[x, y]
        if value > 0 and rng.random() < 0.44:
            arr[x, y] = max(0, value - rng.randint(25, 90))
    return alpha_img


def render_design(design: CollageDesign) -> Path:
    rng = random.Random(design.seed)
    ink, paper, accent, second = design.palette
    canvas = Image.new("RGBA", (1600, 1600), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    main_box = (365 + rng.randint(-15, 10), 480 + rng.randint(-20, 20), 1235 + rng.randint(-10, 15), 905 + rng.randint(-14, 20))
    draw.polygon(ragged_polygon(main_box[0], main_box[1], main_box[2] - main_box[0], main_box[3] - main_box[1], rng, 22), fill=paper)
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.polygon(ragged_polygon(main_box[0] + 18, main_box[1] + 18, main_box[2] - main_box[0], main_box[3] - main_box[1], rng, 18), fill=(0, 0, 0, 50))
    shadow = shadow.filter(ImageFilter.GaussianBlur(3))
    canvas.alpha_composite(shadow)
    draw = ImageDraw.Draw(canvas)
    draw.polygon(ragged_polygon(main_box[0], main_box[1], main_box[2] - main_box[0], main_box[3] - main_box[1], rng, 22), fill=paper)

    draw_tape(draw, (310, 410, 610, 492), accent, rng)
    draw_tape(draw, (990, 900, 1290, 978), second, rng)
    draw.rectangle((430, 938, 900, 992), fill=ink)
    halftone(draw, (1020, 455, 1260, 710), (*ink[:3], 110), 20)

    if design.motif == "burst":
        draw_starburst(draw, 1130, 426, 78, 34, accent)
        draw.line((340, 1020, 1250, 420), fill=(*ink[:3], 220), width=10)
    elif design.motif == "tape":
        draw_tape(draw, (1040, 420, 1285, 505), accent, rng)
        draw.rectangle((310, 945, 610, 1015), fill=second)
    elif design.motif == "arrow":
        draw.line((335, 995, 1250, 995), fill=accent, width=18)
        draw.polygon([(1250, 995), (1190, 955), (1190, 1035)], fill=accent)
    elif design.motif == "circle":
        draw.ellipse((360, 430, 565, 635), outline=accent, width=20)
        draw.ellipse((1010, 845, 1265, 1100), outline=second, width=18)
    elif design.motif == "wave":
        draw_waves(draw, (330, 955, 760, 1050), accent)
        draw_starburst(draw, 1210, 455, 64, 26, second)

    title_font = font("impact.ttf", 252 if len(design.title) <= 5 else 206)
    sub_font = font("arialbd.ttf", 148 if len(design.subtitle) <= 6 else 122)
    small_font = font("consolab.ttf", 52)
    title_bbox = draw.textbbox((0, 0), design.title, font=title_font, stroke_width=2)
    title_x = (canvas.width - (title_bbox[2] - title_bbox[0])) // 2 + rng.randint(-20, 20)
    draw.text((title_x, 525), design.title, font=title_font, fill=ink, stroke_width=2, stroke_fill=paper)
    sub_bbox = draw.textbbox((0, 0), design.subtitle, font=sub_font, stroke_width=3)
    sub_x = (canvas.width - (sub_bbox[2] - sub_bbox[0])) // 2 + rng.randint(-25, 25)
    draw.text((sub_x, 785), design.subtitle, font=sub_font, fill=accent, stroke_width=5, stroke_fill=paper)
    draw.text((455, 948), design.number, font=small_font, fill=paper)
    draw.text((1010, 372), "CUT / PASTE", font=small_font, fill=ink)
    draw.text((340, 1090), "NO BRAND - STREET COLLAGE", font=small_font, fill=(*ink[:3], 230))

    alpha = canvas.getchannel("A")
    alpha = add_grain(alpha, design.seed)
    canvas.putalpha(alpha)
    bbox = canvas.getchannel("A").getbbox()
    if not bbox:
        raise RuntimeError(f"Empty design: {design.filename}")
    cropped = canvas.crop(bbox)
    padded = ImageOps.expand(cropped, border=90, fill=(0, 0, 0, 0))
    rotated = padded.rotate(design.rotation, expand=True, resample=Image.Resampling.BICUBIC, fillcolor=(0, 0, 0, 0))
    bbox2 = rotated.getchannel("A").getbbox()
    if bbox2:
        rotated = rotated.crop(bbox2)
    rotated = ImageOps.expand(rotated, border=48, fill=(0, 0, 0, 0))
    rotated.thumbnail((1300, 1300), Image.Resampling.LANCZOS)
    path = OUT_DIR / design.filename
    rotated.save(path)
    return path


def make_overview(paths: list[Path]) -> None:
    thumbs = []
    for path in paths:
        image = Image.open(path).convert("RGBA")
        preview = Image.new("RGBA", (560, 560), (246, 246, 240, 255))
        image.thumbnail((500, 500), Image.Resampling.LANCZOS)
        preview.alpha_composite(image, ((preview.width - image.width) // 2, (preview.height - image.height) // 2))
        thumbs.append(preview.convert("RGB"))

    overview = Image.new("RGB", (560 * len(paths), 620), (232, 232, 226))
    draw = ImageDraw.Draw(overview)
    label_font = font("segoeui.ttf", 28)
    for index, thumb in enumerate(thumbs):
        x = index * 560
        overview.paste(thumb, (x, 0))
        draw.text((x + 22, 572), paths[index].stem, fill=(40, 40, 40), font=label_font)
    overview.save(OVERVIEW, quality=92)


def write_prompt_file(paths: list[Path]) -> None:
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "混合拼贴街头风印花 5 款预览",
        "定位：商业 T 恤胸前局部印花，透明底，适合黑色/白色/灰色 T 恤。",
        "共性：撕纸块、胶带条、半色调点阵、编号、箭头、星芒和街头排版；避免真实品牌、明星、球队、动漫和版权元素。",
        "",
    ]
    for design, path in zip(DESIGNS, paths):
        lines.append(f"{path.name}: {design.title} {design.subtitle}; {design.number}; motif={design.motif}")
    PROMPT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = [render_design(design) for design in DESIGNS]
    make_overview(paths)
    write_prompt_file(paths)
    print(f"Saved {len(paths)} PNG files to: {OUT_DIR}")
    print(f"Overview: {OVERVIEW}")
    print(f"Prompt notes: {PROMPT_FILE}")


if __name__ == "__main__":
    main()
