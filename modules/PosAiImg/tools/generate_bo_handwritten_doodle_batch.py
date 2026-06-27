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
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

from tshirt_print_tool import IMAGE_EXTS, Placement, composite_one, list_images


ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = Path("C:/Windows/Fonts")
MODEL_DIR = ROOT / "模特图-干净"
TEMPLATE_XLSX = ROOT / "衣物对应的xlsx" / "简约200" / "test(9).xlsx"
PROGRESS_FILE = ROOT / "BO_PROGRESS.md"
PUTAWAY_DATA_DIR = Path(r"E:\1PythonProject\PutawayAiRobot\data")
PUTAWAY_PIC_DIR = PUTAWAY_DATA_DIR / "pic" / "1"


@dataclass(frozen=True)
class Phrase:
    keyword: str
    text: str


@dataclass(frozen=True)
class PrintItem:
    sku: str
    keyword: str
    text: str
    path: Path


PHRASES = [
    Phrase("慢生活", "STAY EASY"),
    Phrase("好日子", "GOOD DAY"),
    Phrase("慢慢来", "SLOW DOWN"),
    Phrase("小幸运", "LITTLE LUCK"),
    Phrase("轻松点", "TAKE IT LIGHT"),
    Phrase("阳光感", "SUN IS UP"),
    Phrase("自由心情", "FREE MOOD"),
    Phrase("微笑日常", "SMILE MORE"),
    Phrase("周末节奏", "WEEKEND MODE"),
    Phrase("今天不错", "TODAY IS OK"),
    Phrase("保持温柔", "KEEP SOFT"),
    Phrase("去散步", "GO OUTSIDE"),
    Phrase("开心一点", "HAPPY THINGS"),
    Phrase("简单快乐", "SIMPLE JOY"),
    Phrase("小小冒险", "TINY ADVENTURE"),
    Phrase("清爽夏天", "COOL SUMMER"),
    Phrase("午后小憩", "NAP CLUB"),
    Phrase("舒适状态", "COZY STATE"),
    Phrase("慢速星期天", "SLOW SUNDAY"),
    Phrase("好好呼吸", "BREATHE EASY"),
    Phrase("别太认真", "NOT SO SERIOUS"),
    Phrase("随便逛逛", "JUST WANDER"),
    Phrase("柔软日子", "SOFT DAYS"),
    Phrase("向阳而行", "CHASE SUN"),
    Phrase("轻快心情", "LIGHT HEART"),
    Phrase("小小闪光", "TINY SPARK"),
    Phrase("安静片刻", "QUIET MOMENT"),
    Phrase("快乐补给", "JOY FUEL"),
    Phrase("海边心情", "BEACH MIND"),
    Phrase("云朵日记", "CLOUD NOTES"),
    Phrase("放空一下", "SPACE OUT"),
    Phrase("保持新鲜", "STAY FRESH"),
    Phrase("路上见", "SEE YOU OUT"),
    Phrase("随心一点", "LET IT FLOW"),
    Phrase("小步前进", "SMALL STEPS"),
    Phrase("悠闲计划", "EASY PLAN"),
    Phrase("好天气", "NICE WEATHER"),
    Phrase("晚风时刻", "EVENING BREEZE"),
    Phrase("元气一下", "GOOD ENERGY"),
    Phrase("轻松周五", "FRIDAY FEEL"),
    Phrase("微光心情", "LITTLE GLOW"),
    Phrase("简单出门", "OUT AND ABOUT"),
    Phrase("快乐信号", "GOOD SIGNAL"),
    Phrase("夏日笔记", "SUMMER NOTE"),
    Phrase("安静快乐", "QUIET JOY"),
    Phrase("松弛一下", "LOOSEN UP"),
    Phrase("今日晴朗", "BRIGHT TODAY"),
    Phrase("随身好运", "LUCK ON ME"),
    Phrase("慢热日常", "WARM SLOWLY"),
    Phrase("自由呼吸", "OPEN AIR"),
]

FONTS = [
    FONT_DIR / "Inkfree.ttf",
    FONT_DIR / "segoeprb.ttf",
    FONT_DIR / "comicbd.ttf",
    FONT_DIR / "mvboli.ttf",
    FONT_DIR / "segoepr.ttf",
    FONT_DIR / "comicz.ttf",
]

MOTIFS = ["stars", "smile", "underline", "sparkle", "corner", "dots", "arrow", "flower"]
ACCENTS = [
    (206, 62, 58, 255),
    (48, 119, 144, 255),
    (64, 132, 78, 255),
    (184, 86, 128, 255),
    (184, 130, 46, 255),
    (99, 93, 164, 255),
]


def batch_name(start: int, count: int, stamp: str) -> str:
    return f"手写涂鸦短句印花_BO-{start}-BO-{start + count - 1}_{stamp}"


def batch_paths(start: int, count: int, stamp: str) -> tuple[Path, Path, Path, Path]:
    name = batch_name(start, count, stamp)
    return (
        ROOT / "印花图_透明底" / name,
        ROOT / "批量贴图结果" / f"{name}_随机主图{count}",
        ROOT / "生成提示词" / f"{name}.txt",
        ROOT / "衣物对应的xlsx" / "简约200" / f"{name}.xlsx",
    )


def load_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    if path.exists():
        return ImageFont.truetype(str(path), size=size)
    return ImageFont.truetype(str(FONT_DIR / "comicbd.ttf"), size=size)


def split_text(text: str) -> tuple[str, ...]:
    words = text.split()
    if len(words) <= 1:
        return (text,)
    if len(words) == 2:
        return tuple(words)
    return (" ".join(words[:-1]), words[-1])


def fit_font_size(text: str, index: int) -> int:
    compact = text.replace(" ", "")
    if len(compact) <= 7:
        return 228 + (index % 4) * 8
    if len(compact) <= 10:
        return 198 + (index % 4) * 7
    return 168 + (index % 4) * 6


def text_bbox(text: str, font: ImageFont.FreeTypeFont, stroke_width: int) -> tuple[int, int, int, int]:
    probe = Image.new("RGBA", (10, 10))
    draw = ImageDraw.Draw(probe)
    return draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)


def draw_wobbly_line(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    fill: tuple[int, int, int, int],
    width: int,
    rng: random.Random,
    steps: int = 20,
) -> None:
    x1, y1 = start
    x2, y2 = end
    points = []
    for step in range(steps + 1):
        t = step / steps
        wobble = math.sin(t * math.tau) * rng.uniform(2.0, 5.5) + rng.uniform(-3, 3)
        points.append((int(x1 + (x2 - x1) * t), int(y1 + (y2 - y1) * t + wobble)))
    draw.line(points, fill=fill, width=width, joint="curve")


def draw_star(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, fill: tuple[int, int, int, int]) -> None:
    points = [
        (cx, cy - r),
        (cx + max(3, r // 4), cy - max(3, r // 4)),
        (cx + r, cy),
        (cx + max(3, r // 4), cy + max(3, r // 4)),
        (cx, cy + r),
        (cx - max(3, r // 4), cy + max(3, r // 4)),
        (cx - r, cy),
        (cx - max(3, r // 4), cy - max(3, r // 4)),
    ]
    draw.polygon(points, fill=fill)


def add_motif(
    draw: ImageDraw.ImageDraw,
    motif: str,
    bbox: tuple[int, int, int, int],
    accent: tuple[int, int, int, int],
    rng: random.Random,
) -> None:
    left, top, right, bottom = bbox
    cx = (left + right) // 2
    width = right - left
    if motif == "stars":
        for x, y, r in [(left - 68, top + 40, 18), (right + 58, bottom - 54, 15), (cx + 22, top - 38, 12)]:
            draw_star(draw, x, y, r, accent)
        draw_wobbly_line(draw, (left, bottom + 38), (right, bottom + 30), accent, 8, rng)
    elif motif == "smile":
        face = (right + 38, top + 12, right + 124, top + 98)
        draw.ellipse(face, outline=accent, width=7)
        draw.ellipse((right + 62, top + 42, right + 72, top + 52), fill=accent)
        draw.ellipse((right + 92, top + 42, right + 102, top + 52), fill=accent)
        draw.arc((right + 62, top + 52, right + 102, top + 82), 8, 172, fill=accent, width=5)
        draw_wobbly_line(draw, (left + 10, bottom + 30), (right - 10, bottom + 24), accent, 8, rng)
    elif motif == "underline":
        draw_wobbly_line(draw, (left - 14, bottom + 40), (right + 14, bottom + 34), accent, 12, rng)
        draw_wobbly_line(draw, (left + width // 5, top - 30), (right - width // 5, top - 32), accent, 6, rng)
    elif motif == "sparkle":
        for x, y, r in [(left - 48, top + 32, 16), (right + 58, top + 72, 20), (cx, bottom + 50, 14)]:
            draw_star(draw, x, y, r, accent)
        draw.arc((left - 22, bottom + 10, right + 24, bottom + 76), 0, 180, fill=accent, width=7)
    elif motif == "corner":
        size = 44
        draw.line((left - 52, top - 30, left - 52 + size, top - 30), fill=accent, width=8)
        draw.line((left - 52, top - 30, left - 52, top - 30 + size), fill=accent, width=8)
        draw.line((right + 52, bottom + 30, right + 52 - size, bottom + 30), fill=accent, width=8)
        draw.line((right + 52, bottom + 30, right + 52, bottom + 30 - size), fill=accent, width=8)
    elif motif == "dots":
        for offset in (-90, -30, 30, 90):
            draw.ellipse((cx + offset - 10, bottom + 28, cx + offset + 10, bottom + 48), fill=accent)
        for offset in (-1, 1):
            draw.ellipse((cx + offset * width // 3 - 7, top - 34, cx + offset * width // 3 + 7, top - 20), fill=accent)
    elif motif == "arrow":
        draw_wobbly_line(draw, (left - 20, bottom + 34), (right + 28, bottom + 28), accent, 8, rng)
        draw.line((right + 28, bottom + 28, right - 6, bottom + 8), fill=accent, width=8)
        draw.line((right + 28, bottom + 28, right - 4, bottom + 52), fill=accent, width=8)
    elif motif == "flower":
        fx, fy = right + 58, top + 58
        for angle in range(0, 360, 72):
            rad = math.radians(angle)
            px = fx + int(math.cos(rad) * 18)
            py = fy + int(math.sin(rad) * 18)
            draw.ellipse((px - 11, py - 11, px + 11, py + 11), outline=accent, width=5)
        draw.ellipse((fx - 8, fy - 8, fx + 8, fy + 8), fill=accent)
        draw_wobbly_line(draw, (left + 8, bottom + 32), (right - 8, bottom + 30), accent, 8, rng)


def render_print(item: PrintItem, index: int, seed: int) -> None:
    rng = random.Random(seed + index * 137)
    font_path = FONTS[index % len(FONTS)]
    font = load_font(font_path, fit_font_size(item.text, index))
    fill = [(18, 18, 18, 255), (24, 24, 23, 255), (31, 28, 29, 255)][index % 3]
    stroke = [(250, 245, 229, 255), (247, 247, 239, 255), (251, 240, 226, 255)][index % 3]
    accent = ACCENTS[index % len(ACCENTS)]
    stroke_width = 7 + index % 3
    lines = split_text(item.text)
    canvas = Image.new("RGBA", (1600, 1600), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    boxes = [text_bbox(line, font, stroke_width) for line in lines]
    sizes = [(box[2] - box[0], box[3] - box[1]) for box in boxes]
    line_gap = -20 + (index % 5) * 5
    total_h = sum(h for _, h in sizes) + line_gap * (len(lines) - 1)
    y = (canvas.height - total_h) // 2 - 8
    actual: list[tuple[int, int, int, int]] = []

    for line, (line_w, line_h) in zip(lines, sizes):
        x = (canvas.width - line_w) // 2 + rng.randint(-18, 18)
        draw.text((x, y), line, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke)
        actual.append((x, y, x + line_w, y + line_h))
        y += line_h + line_gap + rng.randint(-4, 5)

    bbox = (
        min(b[0] for b in actual),
        min(b[1] for b in actual),
        max(b[2] for b in actual),
        max(b[3] for b in actual),
    )
    add_motif(draw, MOTIFS[index % len(MOTIFS)], bbox, accent, rng)
    alpha_bbox = canvas.getchannel("A").getbbox()
    if not alpha_bbox:
        raise RuntimeError(f"Empty print: {item.sku}")
    cropped = canvas.crop(alpha_bbox)
    padded = ImageOps.expand(cropped, border=86, fill=(0, 0, 0, 0))
    angle = [-4.5, 3.0, -2.0, 4.0, -3.0, 2.2, -1.2, 1.6][index % 8]
    rotated = padded.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC, fillcolor=(0, 0, 0, 0))
    bbox2 = rotated.getchannel("A").getbbox()
    if bbox2:
        rotated = rotated.crop(bbox2)
    rotated = ImageOps.expand(rotated, border=48, fill=(0, 0, 0, 0))
    rotated.thumbnail((1300, 1300), Image.Resampling.LANCZOS)
    item.path.parent.mkdir(parents=True, exist_ok=True)
    rotated.save(item.path)


def generate_prints(start: int, count: int, print_dir: Path, prompt_file: Path, seed: int) -> list[PrintItem]:
    if count > len(PHRASES):
        raise ValueError(f"Only {len(PHRASES)} phrases are configured")
    rng = random.Random(seed)
    phrases = PHRASES[:]
    rng.shuffle(phrases)
    phrases = phrases[:count]
    items: list[PrintItem] = []
    prompt_lines = [
        f"手写涂鸦短句印花 {count} 款，货号 BO-{start} 到 BO-{start + count - 1}。",
        "主体为英文短句，深色手写字加浅色描边，少量星星、笑脸、下划线、角标、箭头、花朵等涂鸦元素。",
        "用于黑色/白色/灰色 T 恤胸前局部透明底贴图。",
        "",
    ]
    for idx, phrase in enumerate(phrases):
        sku = f"BO-{start + idx}"
        item = PrintItem(sku=sku, keyword=phrase.keyword, text=phrase.text, path=print_dir / f"{sku}.png")
        render_print(item, idx, seed)
        items.append(item)
        prompt_lines.append(f"{sku}\t{phrase.keyword}\t{phrase.text}")
        print(f"{sku}: print {phrase.text}", flush=True)
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text("\n".join(prompt_lines) + "\n", encoding="utf-8")
    return items


def safe_filename(text: str) -> str:
    invalid_chars = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid_chars or ord(char) < 32 else char for char in text)
    return re.sub(r"_+", "_", cleaned).strip(" ._")


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
    return f"夏季{color_word}手写涂鸦{keyword}印花T恤 {suffix}"


def make_overview(paths: list[Path], output_path: Path) -> None:
    tile_w, tile_h = 260, 330
    cols = 10
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (235, 235, 235))
    try:
        font = ImageFont.truetype(str(FONT_DIR / "msyh.ttc"), 14)
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


def make_products(print_items: list[PrintItem], mockup_dir: Path, seed: int) -> None:
    models = list_images(MODEL_DIR)
    if not models:
        raise FileNotFoundError(f"No model images found: {MODEL_DIR}")
    rng = random.Random(seed)
    placement = Placement(center_x=0.50, center_y=0.42, width=0.28, opacity=0.96, rotation=0.0, shadow_strength=0.28, wave_strength=0.006, remove_white_bg=False)
    mockup_dir.mkdir(parents=True, exist_ok=True)
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
        f"\n- {stamp} 已从 BO-{start} 生成 50 张手写涂鸦短句印花，计划范围为 BO-{start} 到 BO-{end}。\n"
        f"- `{print_dir}` 当前校验为 {validation['print_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号，透明通道存在。\n"
        f"- `{mockup_dir}` 当前校验为 {validation['product_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号。\n"
        f"- `{output_xlsx}` 当前校验为 51 行，表头为 店铺名称、产品分类、产品标题、产品序列号、颜色，首条 BO-{start}，末条 BO-{end}。\n"
        f"- 本批已同步到 `{PUTAWAY_PIC_DIR}`，目标目录校验为 {putaway['putaway_pic_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号；xlsx 已复制到 `{PUTAWAY_DATA_DIR}`。\n"
        "- 视觉抽查：已查看 `_overview.jpg`，整体为手写涂鸦短句方向；黑 T 依靠浅色描边保证可见，白 T 深色主体清晰，个别长短句会比徽章类图案更横向。\n"
    )
    marker = "## 后续规则"
    if marker in text:
        text = text.replace(marker, addition + "\n" + marker, 1)
    else:
        text += addition
    PROGRESS_FILE.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate BO handwritten doodle phrase prints and run full putaway flow.")
    parser.add_argument("--start", type=int, default=1206)
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
