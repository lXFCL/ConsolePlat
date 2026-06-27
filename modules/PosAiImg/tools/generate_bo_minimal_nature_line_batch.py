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
from PIL import Image, ImageDraw, ImageFont, ImageOps

from tshirt_print_tool import Placement, composite_one, list_images


ROOT = Path(__file__).resolve().parents[1]
STYLE_NAME = "极简自然线稿印花"
MODEL_DIR = ROOT / "模特图-干净"
TEMPLATE_DIR = ROOT / "衣物对应的xlsx" / "简约200"
TEMPLATE_XLSX = TEMPLATE_DIR / "test(9).xlsx"
PROGRESS_FILE = ROOT / "BO_PROGRESS.md"
PUTAWAY_DATA_DIR = Path(r"E:\1PythonProject\PutawayAiRobot\data")
PUTAWAY_PIC_DIR = PUTAWAY_DATA_DIR / "pic" / "1"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

SUFFIXES = [
    "圆领短袖 透气微弹针织上衣 日常休闲百搭",
    "圆领短袖 透气舒适针织上衣 户外休闲日常百搭",
    "圆领短袖 轻薄透气针织上衣 休闲通勤日常百搭",
    "圆领短袖 柔软透气针织上衣 夏季日常百搭",
]

KEYWORDS = [
    "太阳花",
    "月亮海浪",
    "山脉日出",
    "植物星环",
    "海贝弧线",
    "松枝月影",
    "野花圆章",
    "湖面山丘",
    "日落波纹",
    "藤蔓光环",
    "森林小径",
    "海岸贝壳",
    "山谷花枝",
    "星月水纹",
    "草叶圆标",
    "远山太阳",
    "花束线稿",
    "潮汐月相",
    "松果枝叶",
    "晨光山线",
    "海浪太阳",
    "叶片轨道",
    "花环月亮",
    "湖畔芦苇",
    "岛屿日落",
    "抽象花枝",
    "山路晨阳",
    "贝壳海浪",
    "松林星环",
    "柔光水面",
    "野草花束",
    "月夜海面",
    "山花日出",
    "植物圆窗",
    "海风弧线",
    "湖光月影",
    "林间蘑菇",
    "荒野太阳",
    "贝壳地平线",
    "枝叶星点",
    "山海线条",
    "花叶徽章",
    "松针月亮",
    "海浪贝纹",
    "小花日环",
    "远山云线",
    "草木轨迹",
    "日月波纹",
    "湖边花草",
    "自然圆章",
]


@dataclass(frozen=True)
class Paths:
    print_dir: Path
    product_dir: Path
    prompt_file: Path
    output_xlsx: Path


@dataclass(frozen=True)
class PrintItem:
    sku: str
    keyword: str
    path: Path


def batch_name(start: int, count: int, stamp: str) -> str:
    return f"{STYLE_NAME}_BO-{start}-BO-{start + count - 1}_{stamp}"


def batch_paths(start: int, count: int, stamp: str) -> Paths:
    name = batch_name(start, count, stamp)
    return Paths(
        print_dir=ROOT / "印花图_透明底" / name,
        product_dir=ROOT / "批量贴图结果" / f"{name}_随机主图{count}",
        prompt_file=ROOT / "生成提示词" / f"{name}.txt",
        output_xlsx=TEMPLATE_DIR / f"{name}.xlsx",
    )


def safe_filename(text: str) -> str:
    invalid_chars = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid_chars or ord(char) < 32 else char for char in text)
    return re.sub(r"_+", "_", cleaned).strip(" ._")


def palette(index: int) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int], tuple[int, int, int, int], tuple[int, int, int, int]]:
    darks = [(25, 28, 30, 255), (31, 42, 47, 255), (45, 39, 35, 255)]
    creams = [(248, 242, 221, 255), (244, 239, 226, 255), (238, 236, 222, 255)]
    accents = [(205, 112, 67, 245), (105, 144, 124, 245), (75, 129, 145, 245), (164, 132, 181, 240), (196, 166, 96, 245)]
    return darks[index % len(darks)], creams[index % len(creams)], accents[index % len(accents)], accents[(index + 2) % len(accents)]


def line(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], dark: tuple[int, int, int, int], cream: tuple[int, int, int, int], width: int = 7, accent: tuple[int, int, int, int] | None = None) -> None:
    draw.line(points, fill=cream, width=width + 11, joint="curve")
    draw.line(points, fill=dark, width=width, joint="curve")
    if accent:
        draw.line(points, fill=accent, width=max(3, width // 2), joint="curve")


def ellipse_outline(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], dark: tuple[int, int, int, int], cream: tuple[int, int, int, int], width: int = 7, accent: tuple[int, int, int, int] | None = None) -> None:
    draw.ellipse(box, outline=cream, width=width + 11)
    draw.ellipse(box, outline=dark, width=width)
    if accent:
        draw.ellipse(box, outline=accent, width=max(3, width // 2))


def arc(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], start: int, end: int, dark: tuple[int, int, int, int], cream: tuple[int, int, int, int], width: int = 7, accent: tuple[int, int, int, int] | None = None) -> None:
    draw.arc(box, start, end, fill=cream, width=width + 11)
    draw.arc(box, start, end, fill=dark, width=width)
    if accent:
        draw.arc(box, start, end, fill=accent, width=max(3, width // 2))


def petal(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], angle: float, fill: tuple[int, int, int, int], dark: tuple[int, int, int, int], cream: tuple[int, int, int, int]) -> None:
    cx = (box[0] + box[2]) / 2
    cy = (box[1] + box[3]) / 2
    rx = (box[2] - box[0]) / 2
    ry = (box[3] - box[1]) / 2
    pts = []
    for step in range(28):
        t = math.tau * step / 28
        x = math.cos(t) * rx
        y = math.sin(t) * ry
        ca = math.cos(angle)
        sa = math.sin(angle)
        pts.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    draw.polygon(pts, fill=cream)
    inner = []
    for x, y in pts:
        inner.append((cx + (x - cx) * 0.86, cy + (y - cy) * 0.86))
    draw.polygon(inner, fill=fill)
    draw.line(inner + [inner[0]], fill=dark, width=5, joint="curve")


def leaf(draw: ImageDraw.ImageDraw, x: float, y: float, angle: float, scale: float, dark: tuple[int, int, int, int], cream: tuple[int, int, int, int], fill: tuple[int, int, int, int]) -> None:
    length = 95 * scale
    width = 36 * scale
    ca = math.cos(angle)
    sa = math.sin(angle)
    pts = []
    for sign in (1, -1):
        for i in range(12):
            t = i / 11
            lx = length * t
            ly = sign * math.sin(math.pi * t) * width
            pts.append((x + lx * ca - ly * sa, y + lx * sa + ly * ca))
    draw.polygon(pts, fill=cream)
    inner = [(x + (px - x) * 0.86, y + (py - y) * 0.86) for px, py in pts]
    draw.polygon(inner, fill=fill)
    draw.line(inner + [inner[0]], fill=dark, width=max(3, int(4 * scale)), joint="curve")
    line(draw, [(x, y), (x + length * ca, y + length * sa)], dark, cream, max(3, int(4 * scale)))


def star(draw: ImageDraw.ImageDraw, x: float, y: float, radius: int, color: tuple[int, int, int, int]) -> None:
    draw.line((x - radius, y, x + radius, y), fill=color, width=max(3, radius // 4))
    draw.line((x, y - radius, x, y + radius), fill=color, width=max(3, radius // 4))


def wave_points(x0: int, x1: int, y: float, amp: float, phase: float) -> list[tuple[float, float]]:
    pts = []
    for x in range(x0, x1 + 1, 12):
        env = math.sin(math.pi * (x - x0) / max(1, x1 - x0))
        pts.append((x, y + math.sin(x / 72 + phase) * amp * env))
    return pts


def draw_sunflower(draw: ImageDraw.ImageDraw, rng: random.Random, dark, cream, accent, accent2) -> None:
    cx, cy = 750, 730
    for i in range(24):
        angle = math.tau * i / 24
        x = cx + math.cos(angle) * 170
        y = cy + math.sin(angle) * 170
        petal(draw, (int(x - 48), int(y - 92), int(x + 48), int(y + 92)), angle, accent, dark, cream)
    draw.ellipse((cx - 142, cy - 142, cx + 142, cy + 142), fill=cream)
    draw.ellipse((cx - 105, cy - 105, cx + 105, cy + 105), fill=(218, 204, 182, 255), outline=dark, width=8)
    for _ in range(55):
        x = rng.randint(cx - 82, cx + 82)
        y = rng.randint(cy - 82, cy + 82)
        if (x - cx) ** 2 + (y - cy) ** 2 < 82**2:
            draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=dark)
    for i in range(12):
        angle = math.tau * i / 12
        line(draw, [(cx + math.cos(angle) * 340, cy + math.sin(angle) * 340), (cx + math.cos(angle) * 405, cy + math.sin(angle) * 405)], dark, cream, 5, accent2 if i % 3 == 0 else None)


def draw_moon_wave(draw: ImageDraw.ImageDraw, rng: random.Random, dark, cream, accent, accent2) -> None:
    ellipse_outline(draw, (340, 330, 1160, 1160), dark, cream, 9, accent2)
    draw.ellipse((475, 420, 910, 855), fill=cream)
    draw.ellipse((610, 365, 1010, 765), fill=(0, 0, 0, 0))
    arc(draw, (475, 420, 910, 855), 78, 282, dark, cream, 9)
    for i in range(8):
        line(draw, wave_points(375, 1125, 875 + i * 42, 22 + i, i * 0.65), dark, cream, 7, accent if i % 2 == 0 else None)
    for _ in range(20):
        star(draw, rng.randint(480, 1060), rng.randint(430, 720), rng.choice([7, 9, 12]), rng.choice([dark, accent2]))


def draw_mountain(draw: ImageDraw.ImageDraw, rng: random.Random, dark, cream, accent, accent2) -> None:
    draw.ellipse((350, 350, 1150, 1150), fill=(230, 178, 104, 230))
    draw.polygon([(290, 1010), (610, 585), (845, 1010)], fill=cream)
    draw.polygon([(315, 990), (610, 625), (815, 990)], fill=(210, 154, 84, 245), outline=dark)
    draw.polygon([(610, 1010), (925, 650), (1220, 1010)], fill=cream)
    draw.polygon([(645, 990), (925, 700), (1175, 990)], fill=accent2, outline=dark)
    line(draw, [(292, 1015), (1230, 1015)], dark, cream, 8)
    for i in range(4):
        line(draw, wave_points(390, 1100, 1060 + i * 35, 12, i), dark, cream, 5, accent if i == 1 else None)


def draw_botanical_orbit(draw: ImageDraw.ImageDraw, rng: random.Random, dark, cream, accent, accent2) -> None:
    for i in range(4):
        arc(draw, (330 + i * 44, 360 + i * 55, 1170 - i * 30, 1110 - i * 35), 205, 520, dark, cream, 7, accent if i % 2 == 0 else None)
    stem = [(635, 1050), (650, 930), (690, 790), (750, 645), (840, 520)]
    line(draw, stem, dark, cream, 8)
    for i, (x, y) in enumerate(stem[1:]):
        leaf(draw, x, y, -0.8 if i % 2 else 0.35, 0.85, dark, cream, accent if i % 2 else accent2)
    for _ in range(16):
        star(draw, rng.randint(420, 1110), rng.randint(430, 1050), rng.choice([6, 8, 10]), rng.choice([dark, accent2]))


def draw_shell(draw: ImageDraw.ImageDraw, rng: random.Random, dark, cream, accent, accent2) -> None:
    draw.ellipse((290, 315, 1210, 1235), fill=cream)
    draw.ellipse((330, 355, 1170, 1175), fill=(219, 202, 170, 255), outline=dark, width=9)
    for i in range(12):
        x0 = 405 + i * 58
        arc(draw, (x0 - 260, 380, x0 + 260, 1180), 224, 315, dark, cream, 5, accent if i % 4 == 0 else None)
    for i in range(5):
        line(draw, wave_points(385, 1110, 790 + i * 55, 20, i * 0.7), dark, cream, 6, accent2 if i % 2 else None)


def draw_branch_moon(draw: ImageDraw.ImageDraw, rng: random.Random, dark, cream, accent, accent2) -> None:
    draw.ellipse((410, 410, 850, 850), fill=cream)
    draw.ellipse((545, 360, 920, 735), fill=(0, 0, 0, 0))
    arc(draw, (410, 410, 850, 850), 75, 285, dark, cream, 9)
    line(draw, [(875, 1110), (815, 960), (750, 800), (700, 650), (670, 520)], dark, cream, 8)
    for i in range(10):
        y = 1020 - i * 55
        leaf(draw, 800 + rng.randint(-15, 20), y, -0.75 if i % 2 else 0.35, 0.75, dark, cream, accent if i % 2 else accent2)
    ellipse_outline(draw, (300, 310, 1200, 1210), dark, cream, 7)


def draw_wildflower_badge(draw: ImageDraw.ImageDraw, rng: random.Random, dark, cream, accent, accent2) -> None:
    ellipse_outline(draw, (345, 315, 1155, 1185), dark, cream, 8, accent2)
    for x in [560, 715, 875]:
        line(draw, [(x, 1045), (x + rng.randint(-70, 70), 640)], dark, cream, 6)
        cx = x + rng.randint(-70, 70)
        cy = rng.randint(570, 710)
        for i in range(8):
            angle = math.tau * i / 8
            petal(draw, (int(cx - 24), int(cy - 54), int(cx + 24), int(cy + 54)), angle, accent if x != 715 else accent2, dark, cream)
        draw.ellipse((cx - 28, cy - 28, cx + 28, cy + 28), fill=cream, outline=dark, width=5)
    for i in range(9):
        leaf(draw, 500 + i * 65, 1030 - rng.randint(0, 90), -1.0 if i % 2 else -2.15, 0.55, dark, cream, accent2)


def draw_lake_hills(draw: ImageDraw.ImageDraw, rng: random.Random, dark, cream, accent, accent2) -> None:
    ellipse_outline(draw, (290, 330, 1210, 1170), dark, cream, 8)
    draw.ellipse((610, 430, 890, 710), fill=accent2)
    line(draw, [(350, 815), (520, 675), (700, 790), (870, 620), (1130, 825)], dark, cream, 8, accent)
    for i in range(8):
        line(draw, wave_points(390, 1110, 900 + i * 34, 13, i), dark, cream, 5, accent2 if i % 3 == 0 else None)
    for x in [470, 1030]:
        line(draw, [(x, 835), (x - 32, 910), (x + 32, 910), (x, 835)], dark, cream, 5)


def draw_sunset_ripples(draw: ImageDraw.ImageDraw, rng: random.Random, dark, cream, accent, accent2) -> None:
    draw.ellipse((500, 420, 1000, 920), fill=accent)
    for i in range(8):
        arc(draw, (270 + i * 55, 505 + i * 62, 1230 - i * 55, 1260 - i * 12), 205, 335, dark, cream, 7, accent2 if i % 2 else None)
    for width, y in [(850, 980), (690, 1065), (520, 1140)]:
        line(draw, [(750 - width / 2, y), (750 + width / 2, y)], dark, cream, 8)


def draw_vine_halo(draw: ImageDraw.ImageDraw, rng: random.Random, dark, cream, accent, accent2) -> None:
    ellipse_outline(draw, (350, 340, 1150, 1140), dark, cream, 8, accent)
    for i in range(18):
        angle = math.tau * i / 18
        x = 750 + math.cos(angle) * 380
        y = 740 + math.sin(angle) * 380
        leaf(draw, x, y, angle + math.pi / 2, 0.55, dark, cream, accent2 if i % 2 else accent)
    draw.ellipse((600, 590, 900, 890), fill=cream)
    draw.ellipse((638, 628, 862, 852), outline=dark, width=9)
    for _ in range(18):
        star(draw, rng.randint(480, 1020), rng.randint(500, 1010), rng.choice([6, 8, 10]), rng.choice([dark, accent2]))


MOTIF_DRAWERS = [
    draw_sunflower,
    draw_moon_wave,
    draw_mountain,
    draw_botanical_orbit,
    draw_shell,
    draw_branch_moon,
    draw_wildflower_badge,
    draw_lake_hills,
    draw_sunset_ripples,
    draw_vine_halo,
]


def render_print(sku: str, index: int, keyword: str, output_dir: Path) -> Path:
    rng = random.Random(2026061400 + index * 173)
    image = Image.new("RGBA", (1500, 1500), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    dark, cream, accent, accent2 = palette(index)
    MOTIF_DRAWERS[index % len(MOTIF_DRAWERS)](draw, rng, dark, cream, accent, accent2)

    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox:
        cropped = image.crop(bbox)
        canvas = Image.new("RGBA", (1500, 1500), (0, 0, 0, 0))
        max_side = max(cropped.size)
        scale = min(1.0, 1050 / max_side)
        new_size = (int(cropped.width * scale), int(cropped.height * scale))
        cropped = cropped.resize(new_size, Image.Resampling.LANCZOS)
        canvas.paste(cropped, ((1500 - cropped.width) // 2, (1500 - cropped.height) // 2), cropped)
        image = canvas

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{sku}.png"
    image.save(path)
    return path


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


def product_title(color_word: str, keyword: str, index: int) -> str:
    suffix = SUFFIXES[index % len(SUFFIXES)]
    return f"夏季{color_word}极简自然线稿{keyword}印花T恤 {suffix}"


def make_overview(paths: list[Path], output_path: Path) -> None:
    tile_w, tile_h = 260, 330
    cols = 10
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (235, 235, 235))
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 13)
    except OSError:
        font = ImageFont.load_default()
    for index, path in enumerate(paths):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        img.thumbnail((240, 268), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (tile_w, tile_h), "white")
        tile.paste(img, ((tile_w - img.width) // 2, 8))
        ImageDraw.Draw(tile).text((8, 286), path.stem[:32], fill=(0, 0, 0), font=font)
        sheet.paste(tile, ((index % cols) * tile_w, (index // cols) * tile_h))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=92)


def build_sheet_xml(rows: list[tuple[str, str, str, str, str]]) -> str:
    def cell(ref: str, value: str, style: int | None = None) -> str:
        s_attr = "" if style is None else f' s="{style}"'
        return f'<c r="{ref}" t="inlineStr"{s_attr}><is><t>{escape(value)}</t></is></c>'

    row_xml = []
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


def rows_from_product_filenames(product_dir: Path) -> list[tuple[str, str, str, str, str]]:
    pattern = re.compile(r"^(BO-\d+)_(.+)\.png$", re.IGNORECASE)
    rows: list[tuple[str, str, str, str, str]] = []
    for path in list_images(product_dir):
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


def write_xlsx_from_product_filenames(product_dir: Path, output_xlsx: Path, expected_count: int) -> None:
    rows_without_header = rows_from_product_filenames(product_dir)
    if len(rows_without_header) != expected_count:
        raise RuntimeError(f"Expected {expected_count} rows, got {len(rows_without_header)} from {product_dir}")
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


def generate_prints(start: int, count: int, paths: Paths) -> list[PrintItem]:
    if count > len(KEYWORDS):
        raise ValueError(f"Only {len(KEYWORDS)} keywords configured")
    items: list[PrintItem] = []
    prompt_lines = [
        f"{STYLE_NAME} BO-{start}-BO-{start + count - 1}",
        "风格：自然符号、粗线稿、奶油色描边、少量低饱和橙绿蓝紫点缀，透明底独立印花。",
        "规则：无人物、无文字、无品牌、无衣服形状；黑 T 和白 T 上都要可见。",
        "",
    ]
    for index in range(count):
        sku = f"BO-{start + index}"
        keyword = KEYWORDS[index]
        path = render_print(sku, index, keyword, paths.print_dir)
        items.append(PrintItem(sku=sku, keyword=keyword, path=path))
        prompt_lines.append(f"{sku}\t{keyword}\t{STYLE_NAME}")
    paths.prompt_file.parent.mkdir(parents=True, exist_ok=True)
    paths.prompt_file.write_text("\n".join(prompt_lines) + "\n", encoding="utf-8")
    return items


def make_products(print_items: list[PrintItem], product_dir: Path, seed: int) -> None:
    models = list_images(MODEL_DIR)
    if not models:
        raise FileNotFoundError(f"No model images found: {MODEL_DIR}")
    rng = random.Random(seed)
    placement = Placement(
        center_x=0.50,
        center_y=0.42,
        width=0.28,
        opacity=0.96,
        rotation=0.0,
        shadow_strength=0.28,
        wave_strength=0.006,
        remove_white_bg=False,
    )
    product_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for index, item in enumerate(print_items):
        model_path = rng.choice(models)
        color_word, color_short = shirt_color(model_path)
        title = product_title(color_word, item.keyword, index)
        output_path = product_dir / safe_filename(f"{item.sku}_{title}.png")
        composite_one(model_path, item.path, output_path, placement)
        outputs.append(output_path)
        print(f"{item.sku}: {model_path.name} -> {color_short}", flush=True)
    make_overview(outputs, product_dir / "_overview.jpg")


def sku_numbers(paths: list[Path]) -> list[int]:
    values = []
    for path in paths:
        match = re.search(r"BO-(\d+)", path.name, re.IGNORECASE)
        if match:
            values.append(int(match.group(1)))
    return sorted(values)


def validate_outputs(start: int, count: int, paths: Paths) -> dict[str, object]:
    expected = list(range(start, start + count))
    print_files = sorted(p for p in list_images(paths.print_dir) if re.fullmatch(r"BO-\d+\.png", p.name, re.IGNORECASE))
    product_files = sorted(p for p in list_images(paths.product_dir) if not p.name.startswith("_"))
    rows = rows_from_product_filenames(paths.product_dir)
    alpha_ok = True
    for path in print_files:
        img = Image.open(path).convert("RGBA")
        if img.getchannel("A").getextrema() != (0, 255):
            alpha_ok = False
            break
    summary = {
        "print_count": len(print_files),
        "product_count": len(product_files),
        "print_range_ok": sku_numbers(print_files) == expected,
        "product_range_ok": sku_numbers(product_files) == expected,
        "alpha_ok": alpha_ok,
        "xlsx_exists": paths.output_xlsx.exists(),
        "xlsx_total_rows": len(rows) + 1,
        "xlsx_header": ["店铺名称", "产品分类", "产品标题", "产品序列号", "颜色"],
        "xlsx_first_sku": rows[0][3] if rows else "",
        "xlsx_last_sku": rows[-1][3] if rows else "",
    }
    if summary["print_count"] != count or summary["product_count"] != count:
        raise RuntimeError(f"Count validation failed: {summary}")
    if not summary["print_range_ok"] or not summary["product_range_ok"]:
        raise RuntimeError(f"SKU validation failed: {summary}")
    if not alpha_ok:
        raise RuntimeError(f"Alpha validation failed: {summary}")
    if not paths.output_xlsx.exists() or len(rows) != count:
        raise RuntimeError(f"XLSX validation failed: {summary}")
    return summary


def sync_putaway(product_dir: Path, output_xlsx: Path) -> None:
    PUTAWAY_PIC_DIR.mkdir(parents=True, exist_ok=True)
    for path in PUTAWAY_PIC_DIR.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            path.unlink()
    for path in list_images(product_dir):
        if not path.name.startswith("_"):
            shutil.copy2(path, PUTAWAY_PIC_DIR / path.name)
    PUTAWAY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output_xlsx, PUTAWAY_DATA_DIR / output_xlsx.name)


def validate_putaway(start: int, count: int, output_xlsx: Path) -> dict[str, object]:
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


def update_progress(start: int, count: int, paths: Paths, validation: dict[str, object], putaway: dict[str, object]) -> None:
    end = start + count - 1
    next_start = end + 1
    stamp = date.today().isoformat()
    text = PROGRESS_FILE.read_text(encoding="utf-8")
    text = re.sub(r"更新时间：.*", f"更新时间：{stamp}", text)
    text = re.sub(r"上次已分配到：BO-\d+", f"上次已分配到：BO-{end}", text)
    text = re.sub(r"下次建议从：BO-\d+", f"下次建议从：BO-{next_start}", text)
    addition = (
        f"\n- {stamp} 已从 BO-{start} 生成 50 张{STYLE_NAME}，计划范围为 BO-{start} 到 BO-{end}。\n"
        f"- `{paths.print_dir}` 当前校验为 {validation['print_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号，透明通道存在。\n"
        f"- `{paths.product_dir}` 当前校验为 {validation['product_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号。\n"
        f"- `{paths.output_xlsx}` 当前校验为 {validation['xlsx_total_rows']} 行，表头为 店铺名称、产品分类、产品标题、产品序列号、颜色，首条 BO-{start}，末条 BO-{end}。\n"
        f"- 本批已同步到 `{PUTAWAY_PIC_DIR}`，目标目录校验为 {putaway['putaway_pic_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号；xlsx 已复制到 `{PUTAWAY_DATA_DIR}`。\n"
        f"- 视觉抽查：已生成 `_overview.jpg`，整体为极简自然线稿方向；需查看黑白 T 上主体清晰度和是否有个别图案过大或过淡。\n"
    )
    marker = "## 后续规则"
    if marker in text:
        text = text.replace(marker, addition + "\n" + marker, 1)
    else:
        text += addition
    PROGRESS_FILE.write_text(text, encoding="utf-8")


def run_generate(args: argparse.Namespace) -> tuple[Paths, dict[str, object]]:
    paths = batch_paths(args.start, args.count, args.date)
    print_items = generate_prints(args.start, args.count, paths)
    make_products(print_items, paths.product_dir, args.seed)
    write_xlsx_from_product_filenames(paths.product_dir, paths.output_xlsx, args.count)
    validation = validate_outputs(args.start, args.count, paths)
    return paths, validation


def run_sync(args: argparse.Namespace) -> tuple[Paths, dict[str, object], dict[str, object]]:
    paths = batch_paths(args.start, args.count, args.date)
    validation = validate_outputs(args.start, args.count, paths)
    sync_putaway(paths.product_dir, paths.output_xlsx)
    putaway = validate_putaway(args.start, args.count, paths.output_xlsx)
    update_progress(args.start, args.count, paths, validation, putaway)
    return paths, validation, putaway


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate BO minimal nature line-art prints and run product-table flow.")
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260614)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--skip-sync", action="store_true")
    parser.add_argument("--sync-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.sync_only:
        paths, validation, putaway = run_sync(args)
    else:
        paths, validation = run_generate(args)
        putaway = None
        if not args.skip_sync:
            sync_putaway(paths.product_dir, paths.output_xlsx)
            putaway = validate_putaway(args.start, args.count, paths.output_xlsx)
            update_progress(args.start, args.count, paths, validation, putaway)
    print(f"print_dir={paths.print_dir}")
    print(f"product_dir={paths.product_dir}")
    print(f"prompt_file={paths.prompt_file}")
    print(f"xlsx={paths.output_xlsx}")
    print(f"validation={json.dumps(validation, ensure_ascii=False)}")
    if putaway is not None:
        print(f"putaway={json.dumps(putaway, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
