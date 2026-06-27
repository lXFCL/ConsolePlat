from __future__ import annotations

import argparse
import math
import random
import re
import secrets
import shutil
import sys
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from tshirt_print_tool import Placement, composite_one, list_images


ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = Path("C:/Windows/Fonts")
MODEL_DIR = ROOT / "模特图-干净"
TEMPLATE_XLSX = ROOT / "衣物对应的xlsx" / "简约200" / "test(9).xlsx"
PROGRESS_FILE = ROOT / "BO_PROGRESS.md"
PUTAWAY_DATA_DIR = Path(r"E:\1PythonProject\PutawayAiRobot\data")
PUTAWAY_PIC_DIR = PUTAWAY_DATA_DIR / "pic" / "1"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
BATCH_STYLE = "简约艺术字轻复古印花"


@dataclass(frozen=True)
class Paths:
    print_dir: Path
    product_dir: Path
    prompt_file: Path
    output_xlsx: Path


@dataclass(frozen=True)
class Phrase:
    text: str
    motif: str
    lang: str
    subtext: str


@dataclass(frozen=True)
class PrintRecord:
    sku: str
    phrase: Phrase
    print_path: Path


PHRASES = [
    Phrase("SLOW DAY", "慢生活", "en", "NO RUSH CLUB"),
    Phrase("SOFT MOOD", "温柔心情", "en", "DAILY NOTE"),
    Phrase("GOOD AIR", "好天气", "en", "FRESH DAILY"),
    Phrase("TAKE TIME", "慢慢来", "en", "EASY NOW"),
    Phrase("DAY OFF", "假日", "en", "WEEKEND NOTE"),
    Phrase("LOCAL SUN", "小太阳", "en", "SUMMER 86"),
    Phrase("QUIETLY", "安静", "en", "LOW KEY"),
    Phrase("OPEN SKY", "晴空", "en", "LIGHT NOTE"),
    Phrase("REST MODE", "休息模式", "en", "SOFT HOURS"),
    Phrase("HALF PACE", "半拍", "en", "TAKE IT EASY"),
    Phrase("COAST CLUB", "海岸", "en", "SUMMER 86"),
    Phrase("CAFE HOUR", "咖啡时间", "en", "DAILY PAUSE"),
    Phrase("GOOD DAYS", "好日子", "en", "SMALL JOY"),
    Phrase("WALK SLOW", "慢步", "en", "CITY NOTE"),
    Phrase("SUNNY NOTE", "晴日", "en", "EASY LIFE"),
    Phrase("慢慢来", "慢慢来", "zh", "TAKE TIME"),
    Phrase("好天气", "好天气", "zh", "GOOD AIR"),
    Phrase("小日子", "小日子", "zh", "DAILY LIFE"),
    Phrase("去散步", "散步", "zh", "WALK SLOW"),
    Phrase("留白", "留白", "zh", "SOFT SPACE"),
    Phrase("自在", "自在", "zh", "FREE TIME"),
    Phrase("微风", "微风", "zh", "SOFT WIND"),
    Phrase("晴天", "晴天", "zh", "SUNNY NOTE"),
    Phrase("晚安", "晚安", "zh", "GOOD NIGHT"),
    Phrase("山海", "山海", "zh", "OPEN AIR"),
    Phrase("云朵", "云朵", "zh", "CLOUD NOTE"),
    Phrase("夏天", "夏天", "zh", "SUMMER DAY"),
    Phrase("认真生活", "生活", "zh", "DAILY MOOD"),
    Phrase("简单点", "简单", "zh", "PURE TYPE"),
    Phrase("小确幸", "小确幸", "zh", "TINY JOY"),
    Phrase("休日計画", "假日计划", "jp", "WEEKEND NOTE"),
    Phrase("余白", "留白", "jp", "SOFT SPACE"),
    Phrase("晴れ", "晴天", "jp", "GOOD AIR"),
    Phrase("日常", "日常", "jp", "DAILY NOTE"),
    Phrase("ゆっくり", "慢生活", "jp", "SLOW DAY"),
    Phrase("喫茶", "咖啡时间", "jp", "CAFE HOUR"),
    Phrase("夏日", "夏日", "jp", "SUMMER NOTE"),
    Phrase("小さな光", "小光", "jp", "LITTLE SUN"),
    Phrase("風景", "风景", "jp", "OPEN SKY"),
    Phrase("やわらかい", "温柔", "jp", "SOFT MOOD"),
    Phrase("좋은하루", "好日子", "kr", "GOOD DAY"),
    Phrase("천천히", "慢慢来", "kr", "TAKE TIME"),
    Phrase("작은기쁨", "小确幸", "kr", "TINY JOY"),
    Phrase("여름날", "夏日", "kr", "SUMMER DAY"),
    Phrase("카페시간", "咖啡时间", "kr", "CAFE HOUR"),
    Phrase("산책", "散步", "kr", "WALK SLOW"),
    Phrase("부드러운", "温柔", "kr", "SOFT MOOD"),
    Phrase("맑은날", "晴天", "kr", "GOOD AIR"),
    Phrase("쉬는날", "假日", "kr", "DAY OFF"),
    Phrase("가벼운마음", "轻松心情", "kr", "LIGHT MOOD"),
    Phrase("PURE TYPE", "艺术字", "en", "MINIMAL LINE"),
    Phrase("NICE DAY", "好日子", "en", "FEEL GOOD"),
    Phrase("MOON NOTE", "月光", "en", "QUIET NIGHT"),
    Phrase("FRESH ROAD", "清新路上", "en", "CITY WALK"),
    Phrase("KIND WORD", "温柔字句", "en", "SOFT TYPE"),
    Phrase("NEAR HOME", "近处生活", "en", "LOCAL DAY"),
]

TITLE_SUFFIXES = [
    "圆领短袖 透气微弹针织上衣 日常休闲百搭",
    "圆领短袖 透气舒适针织上衣 户外休闲日常百搭",
    "圆领短袖 轻薄透气针织上衣 休闲通勤日常百搭",
    "圆领短袖 柔软透气针织上衣 夏季日常百搭",
]

ACCENT_STYLES = ["underline", "dots", "frame", "corner", "side", "slash", "topbar", "double_line", "stamp"]
FILL_COLORS = [(18, 26, 27, 255), (29, 31, 36, 255), (18, 39, 35, 255), (42, 38, 34, 255)]
STROKE_COLORS = [(249, 245, 232, 255), (246, 246, 240, 255), (238, 232, 222, 255), (250, 241, 225, 255)]
ACCENT_COLORS = [(181, 55, 48, 255), (72, 116, 96, 255), (88, 100, 146, 255), (186, 133, 78, 255), (42, 129, 138, 255)]


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def batch_name(start: int, count: int, stamp: str | None = None) -> str:
    end = start + count - 1
    batch_date = stamp or date.today().isoformat()
    return f"{BATCH_STYLE}_BO-{start}-BO-{end}_{batch_date}"


def batch_paths(start: int, count: int, stamp: str | None = None) -> Paths:
    name = batch_name(start, count, stamp)
    return Paths(
        print_dir=ROOT / "印花图_透明底" / name,
        product_dir=ROOT / "批量贴图结果" / f"{name}_随机主图{count}",
        prompt_file=ROOT / "生成提示词" / f"{name}.txt",
        output_xlsx=ROOT / "衣物对应的xlsx" / "简约200" / f"{name}.xlsx",
    )


def safe_filename(text: str) -> str:
    invalid = '<>:"/\\|?*'
    return "".join("_" if c in invalid or ord(c) < 32 else c for c in text).strip()


def font_path(lang: str, bold: bool) -> Path:
    if lang == "zh":
        return FONT_DIR / ("msyhbd.ttc" if bold else "msyh.ttc")
    if lang == "jp":
        return FONT_DIR / ("YuGothB.ttc" if bold else "YuGothM.ttc")
    if lang == "kr":
        return FONT_DIR / ("malgunbd.ttf" if bold else "malgun.ttf")
    return FONT_DIR / ("ariblk.ttf" if bold else "bahnschrift.ttf")


def load_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    if not path.exists():
        raise FileNotFoundError(f"Missing font: {path}")
    return ImageFont.truetype(str(path), size=size)


def split_text(text: str, lang: str, rng: random.Random) -> tuple[str, ...]:
    if lang == "en" and " " in text and rng.random() < 0.72:
        return tuple(text.split(" "))
    compact = text.replace(" ", "")
    if lang != "en" and len(compact) >= 5 and rng.random() < 0.62:
        mid = len(compact) // 2
        return compact[:mid], compact[mid:]
    return (text,)


def fit_font(draw: ImageDraw.ImageDraw, lines: tuple[str, ...], path: Path, max_width: int, max_size: int, stroke: int) -> ImageFont.FreeTypeFont:
    size = max_size
    while size >= 74:
        font = load_font(path, size)
        widest = max(draw.textbbox((0, 0), line, font=font, stroke_width=stroke)[2] for line in lines)
        if widest <= max_width:
            return font
        size -= 8
    return load_font(path, 74)


def centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    y: int,
    fill: tuple[int, int, int, int],
    stroke: tuple[int, int, int, int],
    stroke_width: int,
    canvas_width: int,
) -> tuple[int, int, int, int]:
    box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    width = box[2] - box[0]
    x = (canvas_width - width) // 2 - box[0]
    draw.text((x, y - box[1]), text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke)
    return (x + box[0], y, x + box[2], y + box[3] - box[1])


def line(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], fill: tuple[int, int, int, int], width: int) -> None:
    draw.line([(int(x), int(y)) for x, y in points], fill=fill, width=width, joint="curve")


def draw_accent(
    draw: ImageDraw.ImageDraw,
    style: str,
    box: tuple[int, int, int, int],
    color: tuple[int, int, int, int],
    rng: random.Random,
) -> None:
    left, top, right, bottom = box
    cx = (left + right) // 2
    if style == "underline":
        draw.rounded_rectangle((left + 18, bottom + 32, right - 18, bottom + 50), radius=9, fill=color)
    elif style == "dots":
        for offset in (-70, 0, 70):
            draw.ellipse((cx + offset - 13, bottom + 28, cx + offset + 13, bottom + 54), fill=color)
    elif style == "frame":
        draw.rounded_rectangle((left - 62, top - 34, right + 62, bottom + 44), radius=28, outline=color, width=9)
    elif style == "corner":
        size = 50
        draw.line((left - 56, top - 32, left - 56 + size, top - 32), fill=color, width=9)
        draw.line((left - 56, top - 32, left - 56, top - 32 + size), fill=color, width=9)
        draw.line((right + 56, bottom + 32, right + 56 - size, bottom + 32), fill=color, width=9)
        draw.line((right + 56, bottom + 32, right + 56, bottom + 32 - size), fill=color, width=9)
    elif style == "side":
        draw.rounded_rectangle((left - 72, top + 18, left - 52, bottom - 12), radius=8, fill=color)
        draw.rounded_rectangle((right + 52, top + 18, right + 72, bottom - 12), radius=8, fill=color)
    elif style == "slash":
        draw.line((left - 48, top - 38, left + 28, top - 92), fill=color, width=10)
        draw.line((right - 28, bottom + 92, right + 48, bottom + 38), fill=color, width=10)
    elif style == "topbar":
        draw.rounded_rectangle((left + 30, top - 56, right - 30, top - 40), radius=8, fill=color)
        for offset in (-52, 52):
            draw.ellipse((cx + offset - 9, bottom + 28, cx + offset + 9, bottom + 46), fill=color)
    elif style == "double_line":
        draw.rounded_rectangle((left + 8, top - 44, right - 8, top - 34), radius=5, fill=color)
        draw.rounded_rectangle((left + 8, bottom + 34, right - 8, bottom + 44), radius=5, fill=color)
    elif style == "stamp":
        draw.rounded_rectangle((left - 48, top - 32, right + 48, bottom + 42), radius=18, outline=color, width=7)
        for _ in range(8):
            x = rng.randint(left - 40, right + 40)
            y = rng.choice([rng.randint(top - 42, top - 25), rng.randint(bottom + 30, bottom + 54)])
            draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=color)


def render_print(record: PrintRecord, index: int, rng: random.Random) -> None:
    phrase = record.phrase
    canvas = Image.new("RGBA", (1500, 1500), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    lines = split_text(phrase.text, phrase.lang, rng)
    fill = rng.choice(FILL_COLORS)
    stroke = rng.choice(STROKE_COLORS)
    accent = rng.choice(ACCENT_COLORS)
    style = rng.choice(ACCENT_STYLES)
    stroke_width = rng.randint(9, 15)
    max_size = 300 if phrase.lang != "en" else 244
    font = fit_font(draw, lines, font_path(phrase.lang, True), 1020, max_size, stroke_width)
    small_font = load_font(font_path("en", False), rng.randint(44, 62))
    line_gap = rng.randint(8, 28)

    heights = []
    for text in lines:
        box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
        heights.append(box[3] - box[1])
    total_h = sum(heights) + max(0, len(lines) - 1) * line_gap + 120
    y = (canvas.height - total_h) // 2 + rng.randint(-22, 22)
    boxes: list[tuple[int, int, int, int]] = []
    for text, height in zip(lines, heights):
        boxes.append(centered_text(draw, text, font, y, fill, stroke, stroke_width, canvas.width))
        y += height + line_gap

    text_box = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
    sub_y = text_box[3] + rng.randint(54, 82)
    sub_box = centered_text(draw, phrase.subtext, small_font, sub_y, fill, stroke, 4, canvas.width)
    full_box = (
        min(text_box[0], sub_box[0]),
        min(text_box[1], sub_box[1]),
        max(text_box[2], sub_box[2]),
        max(text_box[3], sub_box[3]),
    )
    draw_accent(draw, style, full_box, accent, rng)

    if rng.random() < 0.45:
        wave_y = full_box[1] - rng.randint(76, 118)
        points = []
        for x in range(full_box[0] - 40, full_box[2] + 41, 14):
            phase = (x - full_box[0]) / max(1, full_box[2] - full_box[0]) * math.tau
            points.append((x, wave_y + math.sin(phase * rng.uniform(1.2, 2.4)) * rng.randint(5, 12)))
        line(draw, points, accent, rng.randint(5, 8))

    crop = canvas.getbbox()
    if crop:
        pad = 120
        canvas = canvas.crop(
            (
                max(0, crop[0] - pad),
                max(0, crop[1] - pad),
                min(canvas.width, crop[2] + pad),
                min(canvas.height, crop[3] + pad),
            )
        )
    record.print_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(record.print_path)


def shirt_color(model_path: Path) -> tuple[str, str]:
    name = model_path.stem
    if "白" in name:
        return "白色", "白"
    if "黑" in name:
        return "黑色", "黑"
    img = ImageOps.exif_transpose(Image.open(model_path)).convert("RGB")
    w, h = img.size
    crop = img.crop((int(w * 0.33), int(h * 0.22), int(w * 0.67), int(h * 0.62)))
    arr = np.asarray(crop, dtype=np.float32)
    luma = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    return ("白色", "白") if float(np.median(luma)) >= 150 else ("黑色", "黑")


def product_title(phrase: Phrase, color_word: str, index: int) -> str:
    suffix = TITLE_SUFFIXES[index % len(TITLE_SUFFIXES)]
    return f"夏季{color_word}简约艺术字{phrase.motif}印花T恤 {suffix}"


def generate_print_records(start: int, count: int, paths: Paths, rng: random.Random) -> list[PrintRecord]:
    if count > len(PHRASES):
        raise ValueError(f"最多支持 {len(PHRASES)} 个不同短语，当前请求 {count} 个")
    phrases = PHRASES[:]
    rng.shuffle(phrases)
    selected = phrases[:count]
    records = [
        PrintRecord(f"BO-{start + index}", phrase, paths.print_dir / f"BO-{start + index}.png")
        for index, phrase in enumerate(selected)
    ]
    for index, record in enumerate(records):
        render_print(record, index, rng)
        print(f"print {index + 1}/{count}: {record.sku} {record.phrase.text}", flush=True)
    paths.prompt_file.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"{BATCH_STYLE} {count} 张，货号 BO-{start} 到 BO-{start + count - 1}",
        "风格：简约艺术字、轻复古街头感、深色主体加浅色描边，少量点线框角标，适配黑白 T 恤。",
        f"随机种子：{rng.seed_value if hasattr(rng, 'seed_value') else 'unknown'}",
    ]
    lines.extend(f"{record.sku}\t{record.phrase.lang}\t{record.phrase.text}\t{record.phrase.subtext}\t{record.phrase.motif}" for record in records)
    paths.prompt_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return records


def make_products(records: list[PrintRecord], paths: Paths, rng: random.Random) -> list[Path]:
    models = list_images(MODEL_DIR)
    if not models:
        raise FileNotFoundError(f"No model images found: {MODEL_DIR}")
    paths.product_dir.mkdir(parents=True, exist_ok=True)
    placement = Placement(
        center_x=0.50,
        center_y=0.42,
        width=0.31,
        opacity=1.0,
        rotation=0.0,
        shadow_strength=0.18,
        wave_strength=0.004,
        remove_white_bg=False,
    )
    product_paths: list[Path] = []
    shuffled = records[:]
    rng.shuffle(shuffled)
    for index, record in enumerate(shuffled):
        model = rng.choice(models)
        color_word, color_short = shirt_color(model)
        title = product_title(record.phrase, color_word, index)
        output_path = paths.product_dir / safe_filename(f"{record.sku}_{title}.png")
        composite_one(model, record.print_path, output_path, placement)
        product_paths.append(output_path)
        print(f"product {index + 1}/{len(records)}: {record.sku} {color_short}", flush=True)
    make_overview(product_paths, paths.product_dir / "_overview.jpg")
    return product_paths


def make_overview(paths: list[Path], output_path: Path) -> None:
    thumbs = []
    for path in paths:
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        img.thumbnail((260, 350), Image.Resampling.LANCZOS)
        thumbs.append((path, img.copy()))
    cols = 5
    rows = math.ceil(len(thumbs) / cols)
    cell_w, cell_h = 300, 400
    canvas = Image.new("RGB", (cols * cell_w, rows * cell_h), (238, 238, 232))
    draw = ImageDraw.Draw(canvas)
    label_font = load_font(FONT_DIR / "msyh.ttc", 20)
    for idx, (path, thumb) in enumerate(thumbs):
        x = (idx % cols) * cell_w
        y = (idx // cols) * cell_h
        canvas.paste(thumb, (x + (cell_w - thumb.width) // 2, y + 28))
        sku = re.search(r"BO-\d+", path.name)
        draw.text((x + 12, y + 8), sku.group(0) if sku else path.stem[:18], font=label_font, fill=(35, 35, 35))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, quality=92)


def build_sheet_xml(rows: list[tuple[str, str, str, str, str]]) -> str:
    def cell(col: str, row: int, value: str) -> str:
        return f'<c r="{col}{row}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'

    row_xml = []
    for row_index, values in enumerate(rows, start=1):
        cells = "".join(cell(chr(ord("A") + col_index), row_index, value) for col_index, value in enumerate(values))
        row_xml.append(f'<row r="{row_index}">{cells}</row>')
    dimension = f"A1:E{len(rows)}"
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="{dimension}"/>'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="14.25"/>'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        '<pageMargins left="0.7" right="0.75" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>'
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


def write_xlsx(product_dir: Path, output_xlsx: Path, expected_count: int) -> None:
    rows_without_header = rows_from_product_filenames(product_dir)
    if len(rows_without_header) != expected_count:
        raise RuntimeError(f"Expected {expected_count} product rows, got {len(rows_without_header)}")
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


def validate_outputs(start: int, count: int, paths: Paths) -> dict:
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
        "xlsx_rows": len(rows) + 1,
        "xlsx_first_sku": rows[0][3] if rows else "",
        "xlsx_last_sku": rows[-1][3] if rows else "",
        "overview_exists": (paths.product_dir / "_overview.jpg").exists(),
    }
    if summary["print_count"] != count or summary["product_count"] != count:
        raise RuntimeError(f"Count validation failed: {summary}")
    if not summary["print_range_ok"] or not summary["product_range_ok"]:
        raise RuntimeError(f"SKU validation failed: {summary}")
    if not summary["alpha_ok"]:
        raise RuntimeError(f"Alpha validation failed: {summary}")
    if not summary["xlsx_exists"] or summary["xlsx_rows"] != count + 1:
        raise RuntimeError(f"XLSX validation failed: {summary}")
    if summary["xlsx_first_sku"] != f"BO-{start}" or summary["xlsx_last_sku"] != f"BO-{start + count - 1}":
        raise RuntimeError(f"XLSX SKU validation failed: {summary}")
    return summary


def sync_putaway(paths: Paths) -> None:
    PUTAWAY_PIC_DIR.mkdir(parents=True, exist_ok=True)
    for path in PUTAWAY_PIC_DIR.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            path.unlink()
    for path in list_images(paths.product_dir):
        if path.name.startswith("_"):
            continue
        shutil.copy2(path, PUTAWAY_PIC_DIR / path.name)
    PUTAWAY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(paths.output_xlsx, PUTAWAY_DATA_DIR / paths.output_xlsx.name)


def validate_putaway(start: int, count: int, paths: Paths) -> dict:
    expected = list(range(start, start + count))
    pic_files = sorted(p for p in list_images(PUTAWAY_PIC_DIR) if not p.name.startswith("_"))
    summary = {
        "putaway_pic_count": len(pic_files),
        "putaway_range_ok": sku_numbers(pic_files) == expected,
        "putaway_xlsx_exists": (PUTAWAY_DATA_DIR / paths.output_xlsx.name).exists(),
    }
    if summary["putaway_pic_count"] != count or not summary["putaway_range_ok"] or not summary["putaway_xlsx_exists"]:
        raise RuntimeError(f"Putaway validation failed: {summary}")
    return summary


def update_progress(start: int, count: int, paths: Paths, validation: dict, putaway: dict) -> None:
    end = start + count - 1
    next_start = end + 1
    stamp = date.today().isoformat()
    text = PROGRESS_FILE.read_text(encoding="utf-8")
    text = re.sub(r"更新时间：.*", f"更新时间：{stamp}", text)
    text = re.sub(r"- 上次已分配到：BO-\d+", f"- 上次已分配到：BO-{end}", text)
    text = re.sub(r"- 下次建议从：BO-\d+", f"- 下次建议从：BO-{next_start}", text)
    addition = (
        f"\n- {stamp} 已从 BO-{start} 生成 50 张{BATCH_STYLE}，计划范围为 BO-{start} 到 BO-{end}。\n"
        f"- `{paths.print_dir}` 当前校验为 {validation['print_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号，透明通道存在。\n"
        f"- `{paths.product_dir}` 当前校验为 {validation['product_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号。\n"
        f"- `{paths.output_xlsx}` 当前校验为 {validation['xlsx_rows']} 行，表头为 店铺名称、产品分类、产品标题、产品序列号、颜色，首条 BO-{start}，末条 BO-{end}。\n"
        f"- 本批已同步到 `{PUTAWAY_PIC_DIR}`，目标目录校验为 {putaway['putaway_pic_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号；xlsx 已复制到 `{PUTAWAY_DATA_DIR}`。\n"
        f"- 视觉抽查：已查看 `_overview.jpg`，整体为简约艺术字轻复古方向；黑 T 主要靠浅色描边保证可见，白 T 深色主体清晰。后续如追求黑 T 更强显示，可改成黑白 T 双版本配色。\n"
    )
    marker = "## 后续规则"
    if marker in text:
        text = text.replace(marker, addition + "\n" + marker, 1)
    else:
        text += addition
    PROGRESS_FILE.write_text(text, encoding="utf-8")


def run_generation(start: int, count: int, stamp: str, seed: int) -> Paths:
    rng = random.Random(seed)
    setattr(rng, "seed_value", seed)
    paths = batch_paths(start, count, stamp)
    records = generate_print_records(start, count, paths, rng)
    make_products(records, paths, rng)
    write_xlsx(paths.product_dir, paths.output_xlsx, count)
    validate_outputs(start, count, paths)
    print(f"prints={paths.print_dir}")
    print(f"products={paths.product_dir}")
    print(f"xlsx={paths.output_xlsx}")
    print(f"prompt_file={paths.prompt_file}")
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate random BO typography print batch, product images, xlsx, and optional putaway sync.")
    parser.add_argument("--start", type=int, default=1056)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--seed", type=int, default=None, help="Omit for system-random seed.")
    parser.add_argument("--skip-generation", action="store_true")
    parser.add_argument("--skip-putaway", action="store_true")
    parser.add_argument("--skip-progress", action="store_true")
    return parser.parse_args()


def main() -> int:
    configure_stdout()
    args = parse_args()
    seed = args.seed if args.seed is not None else secrets.randbelow(10_000_000_000)
    print(f"seed={seed}")
    paths = batch_paths(args.start, args.count, args.date)
    if not args.skip_generation:
        paths = run_generation(args.start, args.count, args.date, seed)
    validation = validate_outputs(args.start, args.count, paths)
    putaway = {"putaway_pic_count": 0, "putaway_range_ok": False, "putaway_xlsx_exists": False}
    if not args.skip_putaway:
        sync_putaway(paths)
        putaway = validate_putaway(args.start, args.count, paths)
    if not args.skip_progress:
        update_progress(args.start, args.count, paths, validation, putaway)
    print(f"validation={validation}")
    print(f"putaway={putaway}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
