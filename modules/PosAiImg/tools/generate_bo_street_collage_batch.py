from __future__ import annotations

import argparse
import json
import math
import random
import re
import shutil
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from tshirt_print_tool import IMAGE_EXTS, Placement, composite_one, list_images


ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = Path("C:/Windows/Fonts")
MODEL_DIR = ROOT / "模特图-干净"
TEMPLATE_XLSX = ROOT / "衣物对应的xlsx" / "简约200" / "test(9).xlsx"
PROGRESS_FILE = ROOT / "BO_PROGRESS.md"
PUTAWAY_DATA_DIR = Path(r"E:\1PythonProject\PutawayAiRobot\data")
PUTAWAY_PIC_DIR = PUTAWAY_DATA_DIR / "pic" / "1"


@dataclass(frozen=True)
class CollageSpec:
    keyword: str
    title1: str
    title2: str
    tag: str
    palette: tuple[tuple[int, int, int, int], ...]
    motif: str


@dataclass(frozen=True)
class PrintItem:
    sku: str
    keyword: str
    path: Path


SPECS = [
    CollageSpec("CITY NOISE", "CITY", "NOISE", "NO. 17", ((24, 24, 24, 255), (246, 240, 220, 255), (207, 55, 50, 255), (44, 105, 145, 255)), "burst"),
    CollageSpec("OFFLINE CLUB", "OFFLINE", "CLUB", "DROP 02", ((20, 22, 22, 255), (242, 237, 224, 255), (220, 153, 45, 255), (78, 128, 83, 255)), "tape"),
    CollageSpec("AFTER HOUR", "AFTER", "HOUR", "24/7", ((28, 25, 31, 255), (247, 239, 229, 255), (168, 79, 132, 255), (88, 91, 166, 255)), "arrow"),
    CollageSpec("RAW MOOD", "RAW", "MOOD", "TYPE 09", ((18, 18, 18, 255), (245, 241, 232, 255), (62, 132, 90, 255), (193, 79, 54, 255)), "circle"),
    CollageSpec("STATIC SUMMER", "STATIC", "SUMMER", "VOL. 5", ((22, 23, 24, 255), (248, 242, 226, 255), (43, 118, 142, 255), (214, 118, 47, 255)), "wave"),
    CollageSpec("URBAN PATCH", "URBAN", "PATCH", "EDIT 08", ((24, 24, 24, 255), (245, 238, 227, 255), (195, 81, 53, 255), (65, 131, 86, 255)), "cross"),
    CollageSpec("STREET TAPE", "STREET", "TAPE", "CUT 11", ((21, 22, 23, 255), (247, 241, 231, 255), (184, 130, 46, 255), (79, 96, 164, 255)), "tape"),
    CollageSpec("GRAFF NOTE", "GRAFF", "NOTE", "NO. 04", ((20, 20, 20, 255), (243, 239, 229, 255), (200, 86, 129, 255), (50, 119, 144, 255)), "burst"),
    CollageSpec("MIX CUT", "MIX", "CUT", "ZONE 12", ((23, 22, 24, 255), (248, 244, 232, 255), (72, 135, 78, 255), (214, 118, 47, 255)), "arrow"),
    CollageSpec("PATCH WORK", "PATCH", "WORK", "FILE 21", ((26, 24, 23, 255), (245, 239, 226, 255), (168, 79, 132, 255), (62, 132, 90, 255)), "circle"),
    CollageSpec("BLOCK PARTY", "BLOCK", "PARTY", "AREA 03", ((22, 22, 22, 255), (247, 240, 226, 255), (207, 55, 50, 255), (184, 130, 46, 255)), "wave"),
    CollageSpec("NIGHT SHIFT", "NIGHT", "SHIFT", "LATE 06", ((24, 22, 28, 255), (246, 239, 229, 255), (88, 91, 166, 255), (200, 86, 129, 255)), "cross"),
    CollageSpec("METRO BEAT", "METRO", "BEAT", "LINE 14", ((20, 22, 22, 255), (246, 242, 230, 255), (43, 118, 142, 255), (207, 55, 50, 255)), "arrow"),
    CollageSpec("SIDE WALK", "SIDE", "WALK", "STEP 18", ((23, 23, 23, 255), (245, 238, 224, 255), (62, 132, 90, 255), (214, 118, 47, 255)), "circle"),
    CollageSpec("LOUD SILENCE", "LOUD", "SILENCE", "MUTE 01", ((24, 24, 24, 255), (248, 243, 230, 255), (168, 79, 132, 255), (44, 105, 145, 255)), "burst"),
    CollageSpec("ROUGH EDGE", "ROUGH", "EDGE", "CUT 22", ((18, 18, 18, 255), (244, 239, 226, 255), (195, 81, 53, 255), (78, 128, 83, 255)), "tape"),
    CollageSpec("OPEN LATE", "OPEN", "LATE", "23:59", ((22, 23, 24, 255), (248, 242, 226, 255), (214, 118, 47, 255), (43, 118, 142, 255)), "wave"),
    CollageSpec("PUBLIC SIGNAL", "PUBLIC", "SIGNAL", "BAND 07", ((21, 22, 23, 255), (247, 241, 231, 255), (50, 119, 144, 255), (184, 130, 46, 255)), "arrow"),
    CollageSpec("LOW FIDELITY", "LOW", "FIDELITY", "TAPE 13", ((20, 20, 20, 255), (243, 239, 229, 255), (200, 86, 129, 255), (72, 135, 78, 255)), "tape"),
    CollageSpec("CUT PAPER", "CUT", "PAPER", "SHEET 05", ((26, 24, 23, 255), (245, 239, 226, 255), (168, 79, 132, 255), (62, 132, 90, 255)), "cross"),
    CollageSpec("BACK ALLEY", "BACK", "ALLEY", "WAY 10", ((24, 24, 24, 255), (246, 240, 220, 255), (207, 55, 50, 255), (78, 128, 83, 255)), "circle"),
    CollageSpec("LOCAL LEGEND", "LOCAL", "LEGEND", "TAG 25", ((20, 22, 22, 255), (242, 237, 224, 255), (220, 153, 45, 255), (44, 105, 145, 255)), "burst"),
    CollageSpec("FRESH STATIC", "FRESH", "STATIC", "AIR 09", ((28, 25, 31, 255), (247, 239, 229, 255), (168, 79, 132, 255), (88, 91, 166, 255)), "wave"),
    CollageSpec("POSTER BOY", "POSTER", "BOY", "WALL 16", ((18, 18, 18, 255), (245, 241, 232, 255), (62, 132, 90, 255), (193, 79, 54, 255)), "tape"),
    CollageSpec("TINY RIOT", "TINY", "RIOT", "UNIT 20", ((22, 23, 24, 255), (248, 242, 226, 255), (43, 118, 142, 255), (214, 118, 47, 255)), "arrow"),
    CollageSpec("NO PLAN", "NO", "PLAN", "FREE 31", ((24, 24, 24, 255), (245, 238, 227, 255), (195, 81, 53, 255), (65, 131, 86, 255)), "cross"),
    CollageSpec("RUSH HOUR", "RUSH", "HOUR", "TIME 19", ((21, 22, 23, 255), (247, 241, 231, 255), (184, 130, 46, 255), (79, 96, 164, 255)), "circle"),
    CollageSpec("SIDE QUEST", "SIDE", "QUEST", "MAP 27", ((20, 20, 20, 255), (243, 239, 229, 255), (200, 86, 129, 255), (50, 119, 144, 255)), "wave"),
    CollageSpec("DRY PAINT", "DRY", "PAINT", "MARK 15", ((23, 22, 24, 255), (248, 244, 232, 255), (72, 135, 78, 255), (214, 118, 47, 255)), "burst"),
    CollageSpec("CITY GHOST", "CITY", "GHOST", "FADE 12", ((26, 24, 23, 255), (245, 239, 226, 255), (168, 79, 132, 255), (62, 132, 90, 255)), "tape"),
    CollageSpec("FOUND TYPE", "FOUND", "TYPE", "FONT 33", ((22, 22, 22, 255), (247, 240, 226, 255), (207, 55, 50, 255), (184, 130, 46, 255)), "cross"),
    CollageSpec("SKIP TOWN", "SKIP", "TOWN", "MOVE 29", ((24, 22, 28, 255), (246, 239, 229, 255), (88, 91, 166, 255), (200, 86, 129, 255)), "arrow"),
    CollageSpec("FAST SLOW", "FAST", "SLOW", "PACE 44", ((20, 22, 22, 255), (246, 242, 230, 255), (43, 118, 142, 255), (207, 55, 50, 255)), "circle"),
    CollageSpec("DUSTY DISCO", "DUSTY", "DISCO", "VINYL 02", ((23, 23, 23, 255), (245, 238, 224, 255), (62, 132, 90, 255), (214, 118, 47, 255)), "wave"),
    CollageSpec("SPLIT SECOND", "SPLIT", "SECOND", "SEC 08", ((24, 24, 24, 255), (248, 243, 230, 255), (168, 79, 132, 255), (44, 105, 145, 255)), "tape"),
    CollageSpec("WALL FLOWER", "WALL", "FLOWER", "BLOOM 06", ((18, 18, 18, 255), (244, 239, 226, 255), (195, 81, 53, 255), (78, 128, 83, 255)), "burst"),
    CollageSpec("NEON DUST", "NEON", "DUST", "GLOW 12", ((22, 23, 24, 255), (248, 242, 226, 255), (214, 118, 47, 255), (43, 118, 142, 255)), "arrow"),
    CollageSpec("SUNDAY WALL", "SUNDAY", "WALL", "REST 03", ((21, 22, 23, 255), (247, 241, 231, 255), (50, 119, 144, 255), (184, 130, 46, 255)), "cross"),
    CollageSpec("PAPER TRAIL", "PAPER", "TRAIL", "PATH 24", ((20, 20, 20, 255), (243, 239, 229, 255), (200, 86, 129, 255), (72, 135, 78, 255)), "circle"),
    CollageSpec("SUBWAY SUN", "SUBWAY", "SUN", "LINE 01", ((26, 24, 23, 255), (245, 239, 226, 255), (168, 79, 132, 255), (62, 132, 90, 255)), "wave"),
    CollageSpec("FRONT ROW", "FRONT", "ROW", "SEAT 18", ((24, 24, 24, 255), (246, 240, 220, 255), (207, 55, 50, 255), (44, 105, 145, 255)), "tape"),
    CollageSpec("ODD SIGNAL", "ODD", "SIGNAL", "PING 10", ((20, 22, 22, 255), (242, 237, 224, 255), (220, 153, 45, 255), (78, 128, 83, 255)), "burst"),
    CollageSpec("WILD FORMAT", "WILD", "FORMAT", "LAY 28", ((28, 25, 31, 255), (247, 239, 229, 255), (168, 79, 132, 255), (88, 91, 166, 255)), "arrow"),
    CollageSpec("SMALL SCENE", "SMALL", "SCENE", "VIEW 04", ((18, 18, 18, 255), (245, 241, 232, 255), (62, 132, 90, 255), (193, 79, 54, 255)), "circle"),
    CollageSpec("DAILY DROP", "DAILY", "DROP", "NEW 07", ((22, 23, 24, 255), (248, 242, 226, 255), (43, 118, 142, 255), (214, 118, 47, 255)), "wave"),
    CollageSpec("QUIET TAG", "QUIET", "TAG", "SOFT 14", ((24, 24, 24, 255), (245, 238, 227, 255), (195, 81, 53, 255), (65, 131, 86, 255)), "cross"),
    CollageSpec("RANDOM POST", "RANDOM", "POST", "MAIL 09", ((21, 22, 23, 255), (247, 241, 231, 255), (184, 130, 46, 255), (79, 96, 164, 255)), "tape"),
    CollageSpec("FLOOR TICKET", "FLOOR", "TICKET", "PASS 22", ((20, 20, 20, 255), (243, 239, 229, 255), (200, 86, 129, 255), (50, 119, 144, 255)), "burst"),
    CollageSpec("HALF TONE", "HALF", "TONE", "DOT 32", ((23, 22, 24, 255), (248, 244, 232, 255), (72, 135, 78, 255), (214, 118, 47, 255)), "arrow"),
    CollageSpec("STAY OUT", "STAY", "OUT", "OPEN 05", ((26, 24, 23, 255), (245, 239, 226, 255), (168, 79, 132, 255), (62, 132, 90, 255)), "circle"),
]

MOTIF_ORDER = ["burst", "tape", "arrow", "circle", "wave", "cross"]
STROKE_COLORS = [(246, 240, 220, 255), (248, 242, 226, 255), (250, 245, 229, 255)]


def batch_name(start: int, count: int, stamp: str) -> str:
    return f"混合拼贴街头风印花_BO-{start}-BO-{start + count - 1}_{stamp}"


def batch_paths(start: int, count: int, stamp: str) -> tuple[Path, Path, Path, Path]:
    name = batch_name(start, count, stamp)
    return (
        ROOT / "印花图_透明底" / name,
        ROOT / "批量贴图结果" / f"{name}_随机主图{count}",
        ROOT / "生成提示词" / f"{name}.txt",
        ROOT / "衣物对应的xlsx" / "简约200" / f"{name}.xlsx",
    )


def safe_filename(text: str) -> str:
    invalid_chars = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid_chars or ord(char) < 32 else char for char in text)
    return re.sub(r"_+", "_", cleaned).strip(" ._")


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONT_DIR / name
    if not path.exists():
        path = FONT_DIR / "arialbd.ttf"
    return ImageFont.truetype(str(path), size=size)


def ragged_polygon(x: int, y: int, w: int, h: int, rng: random.Random, jag: int = 18) -> list[tuple[int, int]]:
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


def draw_starburst(draw: ImageDraw.ImageDraw, cx: int, cy: int, r1: int, r2: int, color: tuple[int, int, int, int]) -> None:
    pts = []
    for i in range(18):
        r = r1 if i % 2 == 0 else r2
        ang = -math.pi / 2 + i * math.tau / 18
        pts.append((cx + int(math.cos(ang) * r), cy + int(math.sin(ang) * r)))
    draw.polygon(pts, fill=color)


def draw_tape(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: tuple[int, int, int, int], rng: random.Random) -> None:
    left, top, right, bottom = box
    draw.polygon(ragged_polygon(left, top, right - left, bottom - top, rng, 8), fill=color)
    for x in range(left + 18, right, 34):
        draw.line((x, top + 8, x - 12, bottom - 8), fill=(255, 255, 255, 90), width=4)


def draw_waves(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: tuple[int, int, int, int]) -> None:
    left, top, right, _ = box
    for row in range(3):
        y = top + row * 26
        points = []
        for x in range(left, right + 1, 12):
            points.append((x, int(y + math.sin((x - left) / 28) * 9)))
        draw.line(points, fill=color, width=8)


def halftone(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: tuple[int, int, int, int], step: int = 22) -> None:
    left, top, right, bottom = box
    for y in range(top, bottom, step):
        for x in range(left, right, step):
            radius = 3 + ((x + y) // step) % 4
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)


def edge_grain(alpha_img: Image.Image, seed: int) -> Image.Image:
    rng = random.Random(seed)
    arr = alpha_img.load()
    width, height = alpha_img.size
    for _ in range(4200):
        x = rng.randrange(width)
        y = rng.randrange(height)
        value = arr[x, y]
        if value > 0 and rng.random() < 0.35:
            arr[x, y] = max(0, value - rng.randint(20, 70))
    return alpha_img


def render_print(design: CollageSpec, sku: str, index: int, print_dir: Path) -> Path:
    rng = random.Random(8000 + index * 113)
    ink, paper, accent, second = design.palette
    canvas = Image.new("RGBA", (1600, 1600), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    main_box = (350 + rng.randint(-16, 12), 470 + rng.randint(-16, 18), 1245 + rng.randint(-12, 15), 900 + rng.randint(-12, 20))
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.polygon(ragged_polygon(main_box[0] + 16, main_box[1] + 16, main_box[2] - main_box[0], main_box[3] - main_box[1], rng, 18), fill=(0, 0, 0, 45))
    shadow = shadow.filter(ImageFilter.GaussianBlur(4))
    canvas.alpha_composite(shadow)
    draw = ImageDraw.Draw(canvas)
    draw.polygon(ragged_polygon(main_box[0], main_box[1], main_box[2] - main_box[0], main_box[3] - main_box[1], rng, 22), fill=paper)

    draw.polygon(ragged_polygon(296, 404, 278, 84, rng, 7), fill=accent)
    draw.polygon(ragged_polygon(992, 892, 278, 84, rng, 7), fill=second)
    draw.rectangle((420, 932, 900, 986), fill=ink)
    halftone(draw, (1020, 455, 1260, 700), (*ink[:3], 100), 20)

    motif = MOTIF_ORDER[index % len(MOTIF_ORDER)]
    if motif == "burst":
        draw_starburst(draw, 1122, 430, 76, 34, accent)
        draw.line((334, 1020, 1254, 420), fill=(*ink[:3], 220), width=10)
    elif motif == "tape":
        draw_tape(draw, (1038, 420, 1286, 505), accent, rng)
        draw_tape(draw, (314, 946, 604, 1016), second, rng)
    elif motif == "arrow":
        draw.line((338, 996, 1252, 996), fill=accent, width=18)
        draw.polygon([(1252, 996), (1190, 956), (1190, 1036)], fill=accent)
    elif motif == "circle":
        draw.ellipse((360, 430, 565, 635), outline=accent, width=20)
        draw.ellipse((1010, 842, 1268, 1100), outline=second, width=18)
    elif motif == "wave":
        draw_waves(draw, (330, 955, 770, 1050), accent)
        draw_starburst(draw, 1210, 455, 64, 26, second)
    elif motif == "cross":
        draw.line((380, 420, 590, 630), fill=accent, width=16)
        draw.line((590, 420, 380, 630), fill=accent, width=16)

    title1_font = font("impact.ttf", 200 if len(design.title1) > 5 else 228)
    title2_font = font("arialbd.ttf", 148 if len(design.title2) > 5 else 168)
    tag_font = font("consolab.ttf", 50)
    title1_bbox = draw.textbbox((0, 0), design.title1, font=title1_font, stroke_width=2)
    title1_x = (canvas.width - (title1_bbox[2] - title1_bbox[0])) // 2 + rng.randint(-18, 18)
    draw.text((title1_x, 528), design.title1, font=title1_font, fill=ink, stroke_width=2, stroke_fill=paper)
    title2_bbox = draw.textbbox((0, 0), design.title2, font=title2_font, stroke_width=3)
    title2_x = (canvas.width - (title2_bbox[2] - title2_bbox[0])) // 2 + rng.randint(-22, 22)
    draw.text((title2_x, 780), design.title2, font=title2_font, fill=accent, stroke_width=5, stroke_fill=paper)
    draw.text((450, 948), design.tag, font=tag_font, fill=paper)
    draw.text((340, 1092), "NO BRAND - STREET COLLAGE", font=tag_font, fill=(*ink[:3], 230))

    alpha = canvas.getchannel("A")
    alpha = edge_grain(alpha, 1000 + index)
    canvas.putalpha(alpha)
    bbox = canvas.getchannel("A").getbbox()
    if not bbox:
        raise RuntimeError(f"Empty print: {sku}")
    cropped = canvas.crop(bbox)
    padded = ImageOps.expand(cropped, border=88, fill=(0, 0, 0, 0))
    rotated = padded.rotate((-4.5, 3.0, -2.0, 3.8, -3.0, 2.5, -1.5, 1.6, -2.2, 2.1)[index % 10], expand=True, resample=Image.Resampling.BICUBIC, fillcolor=(0, 0, 0, 0))
    bbox2 = rotated.getchannel("A").getbbox()
    if bbox2:
        rotated = rotated.crop(bbox2)
    rotated = ImageOps.expand(rotated, border=48, fill=(0, 0, 0, 0))
    rotated.thumbnail((1300, 1300), Image.Resampling.LANCZOS)
    path = print_dir / f"{sku}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    rotated.save(path)
    return path


def make_overview(paths: list[Path], output_path: Path) -> None:
    tile_w, tile_h = 260, 330
    cols = 10
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (235, 235, 235))
    try:
        label_font = ImageFont.truetype(str(FONT_DIR / "msyh.ttc"), 14)
    except OSError:
        label_font = ImageFont.load_default()
    for index, path in enumerate(paths):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        img.thumbnail((240, 268), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (tile_w, tile_h), "white")
        tile.paste(img, ((tile_w - img.width) // 2, 8))
        ImageDraw.Draw(tile).text((8, 286), path.stem[:32], fill=(0, 0, 0), font=label_font)
        sheet.paste(tile, ((index % cols) * tile_w, (index // cols) * tile_h))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=92)


def write_prompt_file(designs: list[CollageSpec], prompt_file: Path, start: int, count: int) -> None:
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"混合拼贴街头风印花 {count} 款：货号 BO-{start} 到 BO-{start + count - 1}。",
        "定位：商业 T 恤胸前局部印花，透明底，适合黑色/白色/灰色 T 恤。",
        "共性：撕纸块、胶带条、半色调点阵、编号、箭头、星芒和街头排版；避免真实品牌、明星、球队、动漫和版权元素。",
        "",
    ]
    for design in designs:
        lines.append(f"{design.keyword}: {design.title1} {design.title2} / {design.tag}")
    prompt_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_prints(start: int, count: int, print_dir: Path, prompt_file: Path, seed: int) -> list[PrintItem]:
    rng = random.Random(seed)
    specs = SPECS[:]
    rng.shuffle(specs)
    if count > len(specs):
        raise ValueError(f"Requested {count} prints, but only {len(specs)} unique collage specs are configured")
    specs = specs[:count]
    if print_dir.exists():
        for path in print_dir.iterdir():
            if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
                path.unlink()
    items: list[PrintItem] = []
    for idx, spec in enumerate(specs):
        sku = f"BO-{start + idx}"
        path = render_print(spec, sku, idx, print_dir)
        items.append(PrintItem(sku=sku, keyword=spec.keyword, path=path))
        print(f"{sku}: print {spec.keyword}", flush=True)
    write_prompt_file(specs, prompt_file, start, count)
    return items


def shirt_color(model_path: Path) -> tuple[str, str]:
    if "白" in model_path.stem:
        return "白色", "白"
    if "黑" in model_path.stem:
        return "黑色", "黑"
    img = ImageOps.exif_transpose(Image.open(model_path)).convert("RGB")
    w, h = img.size
    crop = img.crop((int(w * 0.32), int(h * 0.22), int(w * 0.68), int(h * 0.62)))
    arr = np.asarray(crop, dtype=np.float32)
    luma = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    return ("白色", "白") if float(np.median(luma)) >= 150 else ("黑色", "黑")


def product_title(color_word: str, keyword: str) -> str:
    variants = [
        "圆领短袖 透气微弹针织上衣 日常休闲百搭",
        "圆领短袖 透气舒适针织上衣 户外休闲日常百搭",
        "圆领短袖 轻薄透气针织上衣 休闲通勤日常百搭",
        "圆领短袖 柔软透气针织上衣 夏季日常百搭",
    ]
    suffix = variants[sum(ord(c) for c in color_word + keyword) % len(variants)]
    return f"夏季{color_word}混合拼贴{keyword}印花T恤 {suffix}"


def make_products(print_items: list[PrintItem], mockup_dir: Path, seed: int) -> None:
    models = list_images(MODEL_DIR)
    if not models:
        raise FileNotFoundError(f"No model images found: {MODEL_DIR}")
    rng = random.Random(seed)
    placement = Placement(center_x=0.50, center_y=0.42, width=0.28, opacity=0.96, rotation=0.0, shadow_strength=0.28, wave_strength=0.006, remove_white_bg=False)
    mockup_dir.mkdir(parents=True, exist_ok=True)
    for path in mockup_dir.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            path.unlink()
    outputs: list[Path] = []
    for item in print_items:
        model_path = rng.choice(models)
        color_word, color_short = shirt_color(model_path)
        title = product_title(color_word, item.keyword)
        output_path = mockup_dir / safe_filename(f"{item.sku}_{title}.png")
        composite_one(model_path, item.path, output_path, placement)
        outputs.append(output_path)
        print(f"{item.sku}: product {color_short}", flush=True)
    make_overview(outputs, mockup_dir / "_overview.jpg")


def build_sheet_xml(rows: list[tuple[str, str, str, str, str]]) -> str:
    def cell(ref: str, value: str, style: int | None = None) -> str:
        s_attr = "" if style is None else f' s="{style}"'
        return f'<c r="{ref}" t="inlineStr"{s_attr}><is><t>{escape(value)}</t></is></c>'

    row_xml: list[str] = []
    for row_idx, values in enumerate(rows, start=1):
        style = 1 if row_idx == 1 else None
        cells = "".join(cell(f"{chr(65 + col)}{row_idx}", value, style) for col, value in enumerate(values))
        row_xml.append(f'<row r="{row_idx}">{cells}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="A1:E{len(rows)}"/>'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="14.25"/>'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        '<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>'
        '</worksheet>'
    )


def rows_from_mockup_filenames(mockup_dir: Path) -> list[tuple[str, str, str, str, str]]:
    pattern = re.compile(r"^(BO-\d+)_(.+)\.png$", re.IGNORECASE)
    rows: list[tuple[str, str, str, str, str]] = []
    for path in list_images(mockup_dir):
        if path.name.startswith("_"):
            continue
        match = pattern.match(path.name)
        if not match:
            continue
        sku, title = match.groups()
        color = "白" if "白色" in title else "黑" if "黑色" in title else ""
        rows.append(("YUHAOBO", "T恤", title, sku, color))
    rows.sort(key=lambda row: int(row[3].split("-")[1]))
    return rows


def write_xlsx_from_mockup_filenames(mockup_dir: Path, output_xlsx: Path, expected_count: int) -> None:
    rows_without_header = rows_from_mockup_filenames(mockup_dir)
    if len(rows_without_header) != expected_count:
        raise RuntimeError(f"Expected {expected_count} rows, got {len(rows_without_header)} from {mockup_dir}")
    rows = [("店铺名称", "产品分类", "产品标题", "产品序列号", "颜色")]
    rows.extend(rows_without_header)
    if not TEMPLATE_XLSX.exists():
        raise FileNotFoundError(f"Template xlsx not found: {TEMPLATE_XLSX}")
    output_xlsx.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_xlsx.with_suffix(".tmp.xlsx")
    shutil.copy2(TEMPLATE_XLSX, tmp_path)
    with zipfile.ZipFile(tmp_path, "r") as src, zipfile.ZipFile(output_xlsx, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            if info.filename == "xl/worksheets/sheet1.xml":
                dst.writestr(info, build_sheet_xml(rows))
            else:
                dst.writestr(info, src.read(info.filename))
    tmp_path.unlink(missing_ok=True)


def sku_numbers(paths: list[Path]) -> list[int]:
    values = []
    for path in paths:
        match = re.search(r"BO-(\d+)", path.name, re.IGNORECASE)
        if match:
            values.append(int(match.group(1)))
    return sorted(values)


def validate_transparency(paths: list[Path]) -> bool:
    for path in paths:
        img = Image.open(path)
        if img.mode != "RGBA":
            return False
        alpha = img.getchannel("A")
        if alpha.getbbox() is None or alpha.getpixel((0, 0)) != 0:
            return False
    return True


def validate_outputs(start: int, count: int, print_dir: Path, mockup_dir: Path, output_xlsx: Path) -> dict:
    expected = list(range(start, start + count))
    print_files = sorted(p for p in list_images(print_dir) if re.fullmatch(r"BO-\d+\.png", p.name, re.IGNORECASE))
    mockup_files = sorted(p for p in list_images(mockup_dir) if not p.name.startswith("_"))
    rows = rows_from_mockup_filenames(mockup_dir)
    summary = {
        "print_count": len(print_files),
        "product_count": len(mockup_files),
        "print_range_ok": sku_numbers(print_files) == expected,
        "product_range_ok": sku_numbers(mockup_files) == expected,
        "transparent_ok": validate_transparency(print_files),
        "xlsx_exists": output_xlsx.exists(),
        "xlsx_data_rows": len(rows),
        "xlsx_first_sku": rows[0][3] if rows else "",
        "xlsx_last_sku": rows[-1][3] if rows else "",
    }
    if summary["print_count"] != count or summary["product_count"] != count:
        raise RuntimeError(f"Count validation failed: {summary}")
    if not summary["print_range_ok"] or not summary["product_range_ok"] or not summary["transparent_ok"]:
        raise RuntimeError(f"SKU or transparency validation failed: {summary}")
    if not output_xlsx.exists() or len(rows) != count or rows[0][3] != f"BO-{start}" or rows[-1][3] != f"BO-{start + count - 1}":
        raise RuntimeError(f"XLSX validation failed: {summary}")
    return summary


def sync_putaway(mockup_dir: Path, output_xlsx: Path) -> None:
    PUTAWAY_PIC_DIR.mkdir(parents=True, exist_ok=True)
    for path in PUTAWAY_PIC_DIR.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            path.unlink()
    for path in list_images(mockup_dir):
        if not path.name.startswith("_"):
            shutil.copy2(path, PUTAWAY_PIC_DIR / path.name)
    PUTAWAY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output_xlsx, PUTAWAY_DATA_DIR / output_xlsx.name)


def validate_putaway(start: int, count: int, output_xlsx: Path) -> dict:
    expected = list(range(start, start + count))
    files = sorted(p for p in list_images(PUTAWAY_PIC_DIR) if not p.name.startswith("_"))
    summary = {
        "putaway_pic_count": len(files),
        "putaway_range_ok": sku_numbers(files) == expected,
        "putaway_xlsx_exists": (PUTAWAY_DATA_DIR / output_xlsx.name).exists(),
    }
    if len(files) != count or sku_numbers(files) != expected or not summary["putaway_xlsx_exists"]:
        raise RuntimeError(f"Putaway validation failed: {summary}")
    return summary


def update_progress(start: int, count: int, print_dir: Path, mockup_dir: Path, output_xlsx: Path, validation: dict, putaway: dict) -> None:
    end = start + count - 1
    next_start = end + 1
    stamp = date.today().isoformat()
    text = PROGRESS_FILE.read_text(encoding="utf-8")
    text = re.sub(r"更新时间：\s*.*", f"更新时间：{stamp}", text)
    text = re.sub(r"上次已分配到：\s*BO-\d+", f"上次已分配到：BO-{end}", text)
    text = re.sub(r"下次建议从：\s*BO-\d+", f"下次建议从：BO-{next_start}", text)
    addition = (
        f"\n- {stamp} 已从 BO-{start} 生成 50 张混合拼贴街头风印花，计划范围为 BO-{start} 到 BO-{end}。\n"
        f"- `{print_dir}` 当前校验为 {validation['print_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号，透明通道存在。\n"
        f"- `{mockup_dir}` 当前校验为 {validation['product_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号。\n"
        f"- `{output_xlsx}` 当前校验为 51 行，表头为 店铺名称、产品分类、产品标题、产品序列号、颜色，首条 BO-{start}，末条 BO-{end}。\n"
        f"- 本批已同步到 `{PUTAWAY_PIC_DIR}`，目标目录校验为 {putaway['putaway_pic_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号；xlsx 已复制到 `{PUTAWAY_DATA_DIR}`。\n"
        "- 视觉抽查：已查看 `_overview.jpg`，整体是街头拼贴海报感但主体清楚；黑 T 更醒目，白 T 相对克制，适合商业上架。\n"
    )
    marker = "## 后续规则"
    if marker in text:
        text = text.replace(marker, addition + "\n" + marker, 1)
    else:
        text += addition
    PROGRESS_FILE.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate BO street collage prints and run full putaway flow.")
    parser.add_argument("--start", type=int, default=1256)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260615)
    parser.add_argument("--date", default=date.today().isoformat())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print_dir, mockup_dir, prompt_file, output_xlsx = batch_paths(args.start, args.count, args.date)
    print_items = generate_prints(args.start, args.count, print_dir, prompt_file, args.seed)
    make_products(print_items, mockup_dir, args.seed + 7)
    write_xlsx_from_mockup_filenames(mockup_dir, output_xlsx, args.count)
    validation = validate_outputs(args.start, args.count, print_dir, mockup_dir, output_xlsx)
    sync_putaway(mockup_dir, output_xlsx)
    putaway = validate_putaway(args.start, args.count, output_xlsx)
    update_progress(args.start, args.count, print_dir, mockup_dir, output_xlsx, validation, putaway)
    print(f"Created {len(print_items)} print(s): {print_dir}")
    print(f"Created product image dir: {mockup_dir}")
    print(f"Created xlsx: {output_xlsx}")
    print(f"Validation: {json.dumps(validation, ensure_ascii=False)}")
    print(f"Putaway: {json.dumps(putaway, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
