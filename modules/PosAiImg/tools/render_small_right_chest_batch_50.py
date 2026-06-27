from __future__ import annotations

import argparse
import math
import random
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tshirt_print_tool import Placement, composite_one, list_images  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "\u6a21\u7279\u56fe-\u5e72\u51c0"
PRINT_ROOT = ROOT / "\u5370\u82b1\u56fe_\u900f\u660e\u5e95"
MOCKUP_ROOT = ROOT / "AI\u5370\u82b1\u8d34\u56fe\u6d4b\u8bd5"
PROMPT_ROOT = ROOT / "\u751f\u6210\u63d0\u793a\u8bcd"
FONT_DIR = Path("C:/Windows/Fonts")

BLACK = (18, 18, 18, 255)
INK = (28, 28, 26, 255)
WHITE = (255, 255, 255, 255)
CREAM = (246, 241, 225, 255)
RED = (198, 45, 43, 255)
BLUE = (45, 88, 160, 255)
GREEN = (55, 125, 88, 255)
GOLD = (196, 148, 67, 255)
PINK = (218, 92, 132, 255)
CYAN = (34, 178, 196, 255)
GRAY = (92, 92, 88, 255)

ACCENTS = [RED, BLUE, GREEN, GOLD, PINK, CYAN]


@dataclass(frozen=True)
class Family:
    key: str
    label: str
    note: str


FAMILIES = [
    Family("tiny_type", "small typography chest mark", "short readable type with underline"),
    Family("club_badge", "retro numbered club badge", "small sports badge with a number"),
    Family("botanical", "fine botanical line badge", "leaf and small flower motif"),
    Family("mini_heart", "hand drawn mini symbol", "simple hand drawn icon and small text"),
    Family("wave_word", "wave short word", "wavy line with short word"),
    Family("geo_square", "geometric frame label", "small square frame streetwear mark"),
    Family("sun_mark", "daily sun mark", "round sun icon with text"),
    Family("pixel_tag", "pixel tech tag", "pixel blocks and numeric tag"),
    Family("script_mark", "soft script mark", "small handwritten word mark"),
    Family("leaf_number", "leaf number patch", "natural number label"),
]

TINY_WORDS = [("LITTLE", "DAY"), ("GOOD", "NOISE"), ("OPEN", "AIR"), ("LOCAL", "MOOD"), ("NOVA", "CLUB")]
CLUB_WORDS = [("27", "LOCAL"), ("14", "RALLY"), ("86", "TRACK"), ("05", "FIELD"), ("99", "CLUB")]
BOTANICAL_WORDS = ["BLOOM", "MOSS", "ROOT", "TIDE", "FERN"]
HEART_WORDS = ["tiny mood", "soft sign", "good luck", "slow love", "mini day"]
WAVE_WORDS = [("SLOW", "WAVE"), ("COOL", "TIDE"), ("OPEN", "SEA"), ("LOW", "NOISE"), ("SOFT", "AIR")]
GEO_WORDS = ["LINE", "GRID", "FRAME", "BOX", "SIGN"]
SUN_WORDS = [("SUN", "DAILY"), ("RAY", "CLUB"), ("DAY", "LIGHT"), ("SOL", "LOCAL"), ("HOT", "MARK")]
PIXEL_WORDS = [("404", "BYTE"), ("101", "SYNC"), ("808", "CTRL"), ("303", "VOID"), ("256", "MODE")]
SCRIPT_WORDS = [("mellow", "small sign"), ("simple", "daily mark"), ("easy", "tiny note"), ("wander", "soft line"), ("quiet", "mini type")]
LEAF_WORDS = [("08", "ROOT"), ("12", "MOSS"), ("21", "LEAF"), ("35", "FERN"), ("46", "HERB")]


def safe_name(text: str) -> str:
    return re.sub(r"[^\w\-.]+", "_", text, flags=re.UNICODE).strip("_") or "image"


def font(candidates: list[str], size: int) -> ImageFont.ImageFont:
    for name in candidates:
        path = FONT_DIR / name
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def text_box(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    fnt: ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
    stroke_fill: tuple[int, int, int, int] = WHITE,
    stroke_width: int = 5,
    anchor: str = "mm",
) -> None:
    draw.text(xy, text, font=fnt, fill=fill, anchor=anchor, stroke_fill=stroke_fill, stroke_width=stroke_width)


def star_points(cx: int, cy: int, outer: int, inner: int, points: int = 5) -> list[tuple[int, int]]:
    coords = []
    for i in range(points * 2):
        radius = outer if i % 2 == 0 else inner
        angle = -math.pi / 2 + i * math.pi / points
        coords.append((cx + int(math.cos(angle) * radius), cy + int(math.sin(angle) * radius)))
    return coords


def crop_save(img: Image.Image, output_path: Path) -> None:
    bbox = img.getbbox()
    if bbox:
        pad = 38
        img = img.crop((
            max(0, bbox[0] - pad),
            max(0, bbox[1] - pad),
            min(img.width, bbox[2] + pad),
            min(img.height, bbox[3] + pad),
        ))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)


def lighten_on_transparent(img: Image.Image, factor: float = 1.0) -> Image.Image:
    if factor == 1.0:
        return img
    r, g, b, a = img.split()
    rgb = Image.merge("RGB", (r, g, b))
    rgb = ImageEnhance.Brightness(rgb).enhance(factor)
    r, g, b = rgb.split()
    return Image.merge("RGBA", (r, g, b, a))


def draw_tiny_type(draw: ImageDraw.ImageDraw, variant: int) -> str:
    top, bottom = TINY_WORDS[variant]
    accent = ACCENTS[variant % len(ACCENTS)]
    text_box(draw, (500, 400), top, font(["GOTHICB.TTF", "arialbd.ttf"], 98), INK, CREAM, 8)
    text_box(draw, (500, 520), bottom, font(["impact.ttf", "arialbd.ttf"], 166), BLACK, WHITE, 8)
    draw.rounded_rectangle((325, 620, 675, 660), radius=18, fill=accent)
    if variant % 2 == 0:
        draw.line((370, 708, 630, 708), fill=BLACK, width=12)
    else:
        for x in range(385, 626, 60):
            draw.ellipse((x - 12, 696, x + 12, 720), fill=BLACK)
    return f"{top.lower()}_{bottom.lower()}"


def draw_club_badge(draw: ImageDraw.ImageDraw, variant: int) -> str:
    number, label = CLUB_WORDS[variant]
    accent = [RED, BLUE, GREEN, GOLD, PINK][variant]
    draw.rounded_rectangle((280, 260, 720, 740), radius=76, fill=CREAM, outline=BLACK, width=18)
    draw.rounded_rectangle((340, 325, 660, 675), radius=44, outline=accent, width=14)
    text_box(draw, (500, 445), number, font(["impact.ttf", "arialbd.ttf"], 204), BLACK, CREAM, 5)
    text_box(draw, (500, 610), label, font(["GOTHICB.TTF", "arialbd.ttf"], 68), accent, WHITE, 5)
    draw.polygon(star_points(320, 275, 34, 13), fill=GOLD)
    draw.polygon(star_points(680, 275, 34, 13), fill=GOLD)
    return f"{label.lower()}_{number}"


def draw_botanical(draw: ImageDraw.ImageDraw, variant: int) -> str:
    label = BOTANICAL_WORDS[variant]
    accent = [GREEN, GOLD, BLUE, CYAN, PINK][variant]
    draw.rounded_rectangle((285, 265, 715, 760), radius=80, fill=CREAM, outline=BLACK, width=8)
    stem_shift = (variant - 2) * 12
    draw.line((410 + stem_shift, 680, 545 + stem_shift, 315), fill=BLACK, width=13)
    for idx, (y, side) in enumerate([(610, -1), (555, 1), (500, -1), (445, 1), (392, -1)]):
        x = int(498 + side * (20 + variant * 3) + stem_shift)
        box = (x - 95, y - 58, x + 16, y + 30) if side < 0 else (x - 16, y - 58, x + 95, y + 30)
        draw.ellipse(box, outline=accent if idx % 2 else GREEN, width=11)
    for cx, cy in [(618, 405), (652, 460), (596, 488)]:
        draw.ellipse((cx - 26, cy - 26, cx + 26, cy + 26), outline=BLACK, width=8)
    text_box(draw, (500, 735), label, font(["GOTHICB.TTF", "arialbd.ttf"], 66), BLACK, WHITE, 5)
    return label.lower()


def draw_mini_heart(draw: ImageDraw.ImageDraw, variant: int) -> str:
    label = HEART_WORDS[variant]
    accent = [RED, PINK, BLUE, GOLD, GREEN][variant]
    x_shift = (variant - 2) * 10
    draw.line((500 + x_shift, 705, 500 + x_shift, 360), fill=BLACK, width=11)
    draw.arc((340 + x_shift, 300, 506 + x_shift, 505), 205, 55, fill=accent, width=28)
    draw.arc((494 + x_shift, 300, 660 + x_shift, 505), 125, 335, fill=accent, width=28)
    draw.line((355 + x_shift, 438, 500 + x_shift, 620), fill=accent, width=28)
    draw.line((645 + x_shift, 438, 500 + x_shift, 620), fill=accent, width=28)
    if variant % 2:
        draw.polygon(star_points(640, 350, 28, 11), fill=GOLD)
    text_box(draw, (500, 760), label, font(["segoepr.ttf", "arial.ttf"], 54), BLACK, WHITE, 4)
    return safe_name(label)


def draw_wave_word(draw: ImageDraw.ImageDraw, variant: int) -> str:
    top, bottom = WAVE_WORDS[variant]
    colors = [(BLUE, BLACK, CYAN), (GREEN, BLACK, GOLD), (PINK, BLACK, BLUE), (GOLD, BLACK, RED), (CYAN, BLACK, GREEN)][variant]
    draw.rounded_rectangle((260, 320, 740, 805), radius=42, fill=CREAM, outline=BLACK, width=8)
    for idx, y in enumerate([405, 465, 525]):
        pts = []
        for x in range(270, 731, 18):
            pts.append((x, y + int(math.sin((x + idx * 25 + variant * 20) / 42) * 22)))
        draw.line(pts, fill=colors[idx], width=13)
    text_box(draw, (500, 640), top, font(["impact.ttf", "arialbd.ttf"], 146), BLACK, WHITE, 8)
    text_box(draw, (500, 760), bottom, font(["GOTHICB.TTF", "arialbd.ttf"], 60), colors[0], WHITE, 4)
    return f"{top.lower()}_{bottom.lower()}"


def draw_geo_square(draw: ImageDraw.ImageDraw, variant: int) -> str:
    label = GEO_WORDS[variant]
    accent = [GOLD, BLUE, GREEN, RED, CYAN][variant]
    draw.rounded_rectangle((278, 278, 722, 760), radius=26, fill=CREAM)
    for offset, color in [(0, BLACK), (35, accent), (70, BLACK)]:
        draw.rounded_rectangle((300 + offset, 305 + offset, 700 - offset, 705 - offset), radius=18, outline=color, width=12)
    for i in range(8):
        y = 365 + i * 38
        wobble = 18 if (i + variant) % 2 else -18
        draw.line((360, y, 640, y + wobble), fill=BLACK, width=6)
    text_box(draw, (500, 755), label, font(["impact.ttf", "arialbd.ttf"], 82), BLACK, WHITE, 5)
    return label.lower()


def draw_sun_mark(draw: ImageDraw.ImageDraw, variant: int) -> str:
    top, bottom = SUN_WORDS[variant]
    accent = [GOLD, RED, BLUE, GREEN, PINK][variant]
    rays = 16 + variant
    for i in range(rays):
        angle = i * math.tau / rays
        x1 = 500 + int(math.cos(angle) * 155)
        y1 = 485 + int(math.sin(angle) * 155)
        x2 = 500 + int(math.cos(angle) * (230 + variant * 4))
        y2 = 485 + int(math.sin(angle) * (230 + variant * 4))
        draw.line((x1, y1, x2, y2), fill=accent if i % 2 else BLACK, width=12)
    draw.ellipse((345, 330, 655, 640), fill=CREAM, outline=BLACK, width=16)
    text_box(draw, (500, 495), top, font(["impact.ttf", "arialbd.ttf"], 132), BLACK, WHITE, 5)
    text_box(draw, (500, 725), bottom, font(["GOTHICB.TTF", "arialbd.ttf"], 62), accent, WHITE, 4)
    return f"{top.lower()}_{bottom.lower()}"


def draw_pixel_tag(draw: ImageDraw.ImageDraw, variant: int) -> str:
    number, label = PIXEL_WORDS[variant]
    accent = [CYAN, RED, BLUE, PINK, GREEN][variant]
    rng = random.Random(618 + variant)
    for _ in range(28 + variant):
        x = rng.randrange(295, 690, 28)
        y = rng.randrange(300, 650, 28)
        color = accent if rng.random() < 0.38 else BLACK
        draw.rectangle((x, y, x + 24, y + 24), fill=color)
    draw.rounded_rectangle((330, 390, 670, 620), radius=24, fill=CREAM, outline=BLACK, width=13)
    text_box(draw, (500, 505), number, font(["impact.ttf", "arialbd.ttf"], 150), BLACK, WHITE, 6)
    text_box(draw, (500, 720), label, font(["GOTHICB.TTF", "arialbd.ttf"], 68), accent, WHITE, 5)
    return f"{label.lower()}_{number}"


def draw_script_mark(draw: ImageDraw.ImageDraw, variant: int) -> str:
    top, bottom = SCRIPT_WORDS[variant]
    accent = [PINK, BLUE, GREEN, GOLD, RED][variant]
    text_box(draw, (500, 470), top, font(["segoesc.ttf", "segoepr.ttf", "ariali.ttf"], 112), BLACK, WHITE, 7)
    draw.arc((270, 475, 730, 720), 185, 355, fill=accent, width=14)
    for cx in [345, 500, 655]:
        draw.ellipse((cx - 18, 685, cx + 18, 721), fill=BLACK)
    text_box(draw, (500, 760), bottom, font(["GOTHICB.TTF", "arialbd.ttf"], 48), accent, WHITE, 4)
    return safe_name(top)


def draw_leaf_number(draw: ImageDraw.ImageDraw, variant: int) -> str:
    number, label = LEAF_WORDS[variant]
    accent = [GREEN, GOLD, BLUE, CYAN, PINK][variant]
    draw.rounded_rectangle((295, 280, 705, 720), radius=90, fill=CREAM, outline=BLACK, width=16)
    text_box(draw, (500, 450), number, font(["impact.ttf", "arialbd.ttf"], 190), BLACK, CREAM, 7)
    draw.line((385, 635, 610, 535), fill=accent, width=12)
    for x, y, side in [(430, 615, -1), (485, 590, 1), (545, 562, -1), (590, 542, 1)]:
        box = (x - 55, y - 36, x, y + 22) if side < 0 else (x, y - 36, x + 55, y + 22)
        draw.ellipse(box, outline=accent, width=8)
    text_box(draw, (500, 745), label, font(["GOTHICB.TTF", "arialbd.ttf"], 58), accent, WHITE, 4)
    return f"{label.lower()}_{number}"


DRAWERS = [
    draw_tiny_type,
    draw_club_badge,
    draw_botanical,
    draw_mini_heart,
    draw_wave_word,
    draw_geo_square,
    draw_sun_mark,
    draw_pixel_tag,
    draw_script_mark,
    draw_leaf_number,
]


def render_prints(output_dir: Path, count: int) -> list[Path]:
    paths: list[Path] = []
    if count % len(FAMILIES) != 0:
        raise ValueError(f"count must be divisible by {len(FAMILIES)}")
    variants_per_family = count // len(FAMILIES)
    if variants_per_family > 5:
        raise ValueError("this script currently supports up to 5 variants per family")

    index = 1
    for family, drawer in zip(FAMILIES, DRAWERS, strict=True):
        for variant in range(variants_per_family):
            img = Image.new("RGBA", (1000, 1000), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            slug = drawer(draw, variant)
            # Slightly warm the full print so tiny marks are less harsh on white shirts.
            img = lighten_on_transparent(img, 1.0)
            output_path = output_dir / f"{index:03d}_{family.key}_{safe_name(slug)}.png"
            crop_save(img, output_path)
            paths.append(output_path)
            print(f"print {index:03d}: {output_path}")
            index += 1
    return paths


def make_overview(image_paths: list[Path], output_path: Path, title: str, cols: int = 10) -> None:
    tile_w, tile_h = 210, 230
    label_h = 34
    rows = (len(image_paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_w, 48 + rows * (tile_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    draw.text((16, 16), title, fill=(0, 0, 0))
    for idx, path in enumerate(image_paths):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
        bg = Image.new("RGBA", img.size, "white")
        bg.alpha_composite(img)
        preview = bg.convert("RGB")
        preview.thumbnail((tile_w - 24, tile_h - 24), Image.Resampling.LANCZOS)
        x0 = (idx % cols) * tile_w
        y0 = 48 + (idx // cols) * (tile_h + label_h)
        sheet.paste(preview, (x0 + (tile_w - preview.width) // 2, y0 + (tile_h - preview.height) // 2))
        draw.text((x0 + 8, y0 + tile_h + 8), path.stem[:28], fill=(0, 0, 0))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=94)


def make_mockups(print_paths: list[Path], output_dir: Path, seed: int) -> list[Path]:
    models = list_images(MODEL_DIR)
    if not models:
        raise FileNotFoundError(f"No model images found: {MODEL_DIR}")
    rng = random.Random(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    placement = Placement(
        center_x=0.62,
        center_y=0.32,
        width=0.115,
        opacity=0.98,
        rotation=0.0,
        shadow_strength=0.16,
        wave_strength=0.003,
        remove_white_bg=False,
    )

    outputs: list[Path] = []
    for index, print_path in enumerate(print_paths, start=1):
        model_path = rng.choice(models)
        output_path = output_dir / f"{index:03d}_{safe_name(model_path.stem)}__{safe_name(print_path.stem)}_right_chest.png"
        composite_one(model_path, print_path, output_path, placement)
        outputs.append(output_path)
        print(f"mockup {index:03d}: {output_path}")
    return outputs


def write_notes(output_path: Path, print_dir: Path, mockup_dir: Path, count: int) -> None:
    lines = [
        f"Small right upper chest print batch: {count} designs",
        "",
        "Style basis: the approved 10-image test direction, expanded into 10 families x 5 variants.",
        "Families: tiny typography, retro club badge, botanical line badge, hand drawn mini symbol, wave word, geometric frame, sun mark, pixel tag, soft script, leaf number.",
        "Placement: center_x=0.62, center_y=0.32, width=0.115, opacity=0.98, shadow_strength=0.16, wave_strength=0.003.",
        f"Transparent prints: {print_dir}",
        f"Main-image mockups: {mockup_dir}",
        "",
    ]
    lines.extend(f"- {family.key}: {family.label}; {family.note}" for family in FAMILIES)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a 50-image small right upper chest print batch.")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d_%H%M"))
    parser.add_argument("--seed", type=int, default=2026061350)
    parser.add_argument("--count", type=int, default=50)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    batch_name = f"right_chest_small_badges_{args.count}_{args.date}"
    print_dir = PRINT_ROOT / batch_name
    mockup_dir = MOCKUP_ROOT / f"{batch_name}_main_mockups"
    notes_path = PROMPT_ROOT / f"{batch_name}.txt"

    print_paths = render_prints(print_dir, args.count)
    make_overview(print_paths, print_dir / "_prints_overview.jpg", "small right chest transparent print batch")

    mockup_paths = make_mockups(print_paths, mockup_dir, args.seed)
    make_overview(mockup_paths, mockup_dir / "_mockups_overview.jpg", "small right upper chest mockup batch")
    write_notes(notes_path, print_dir, mockup_dir, args.count)

    print(f"Prints: {print_dir}")
    print(f"Mockups: {mockup_dir}")
    print(f"Notes: {notes_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
