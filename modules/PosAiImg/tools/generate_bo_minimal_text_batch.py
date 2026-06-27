from __future__ import annotations

import argparse
import os
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
FONT_DIR = Path("C:/Windows/Fonts")
MODEL_DIR = ROOT / "模特图-干净"
TEMPLATE_XLSX = ROOT / "衣物对应的xlsx" / "简约200" / "test(9).xlsx"


def batch_name(start: int, count: int, batch_date: str | None = None) -> str:
    end = start + count - 1
    stamp = batch_date or date.today().isoformat()
    return f"简约艺术字文字印花_BO-{start}-BO-{end}_{stamp}"


def batch_paths(start: int, count: int, batch_date: str | None = None) -> tuple[Path, Path, Path, Path]:
    name = batch_name(start, count, batch_date)
    return (
        ROOT / "印花图_透明底" / name,
        ROOT / "批量贴图结果" / f"{name}_随机主图{count}",
        ROOT / "生成提示词" / f"{name}.txt",
        ROOT / "衣物对应的xlsx" / "简约200" / f"{name}.xlsx",
    )


LEGACY_PRINT_DIR, LEGACY_MOCKUP_DIR, LEGACY_PROMPT_FILE, LEGACY_OUTPUT_XLSX = batch_paths(
    306,
    200,
    "2026-06-09",
)
LEGACY_SIMPLIFIED_MOCKUP_DIR = ROOT / "批量贴图结果" / "BO中等标题200"


@dataclass(frozen=True)
class Phrase:
    lang: str
    text: str


@dataclass(frozen=True)
class PrintItem:
    sku: str
    phrase: Phrase
    print_path: Path


@dataclass(frozen=True)
class MockupItem:
    sku: str
    title: str
    color: str
    model_path: Path
    print_path: Path
    output_path: Path


KOREAN = [
    "안녕", "좋아", "하루", "느긋", "산책", "바람", "여유", "소소", "달빛", "커피",
    "미소", "오늘", "별빛", "휴식", "맑음", "고요", "작은꿈", "순간", "마음", "봄날",
    "햇살", "평온", "기록", "낮잠", "새벽", "모래", "파도", "온기", "초록", "밤공기",
    "천천히", "우리", "가볍게", "선물", "조용히", "다시", "낭만", "귤빛", "담담", "웃자",
    "산들", "빛나", "로컬", "주말", "여름", "구름", "꽃길", "편안", "미니", "하늘",
]

JAPANESE = [
    "いい日", "そよ風", "ゆっくり", "さんぽ", "小さな", "月夜", "きもち", "ひと息", "休日", "晴れ",
    "まどろみ", "余白", "朝", "夜", "花", "雲", "海", "森", "空", "夢",
    "静か", "今日", "明日", "光", "手紙", "純白", "青空", "旅", "喫茶", "音",
    "線", "柔らか", "きらり", "ほっと", "ことば", "まるい", "春", "夏", "秋", "冬",
    "日々", "風景", "淡い", "ねむい", "星", "水色", "こころ", "はじまり", "余韻", "日常",
]

CHINESE = [
    "慢慢来", "好天气", "小日子", "松弛感", "今天很好", "去散步", "微风", "晚安", "早安", "自在",
    "留白", "日常", "片刻", "温柔", "山海", "云朵", "夏天", "春日", "秋风", "冬夜",
    "小岛", "咖啡", "月光", "安静", "晴天", "慢生活", "去看海", "慢热", "轻轻", "呼吸",
    "远方", "花开", "旧时光", "平常心", "自由", "软软", "认真", "放空", "不赶路", "简单点",
    "有光", "微甜", "小确幸", "山野", "好好睡", "慢半拍", "向阳", "你好", "一起", "悠悠",
]

ENGLISH = [
    "SLOW DAY", "SOFT MOOD", "EASY NOW", "GOOD AIR", "HELLO", "WEEKEND", "DAY OFF", "TAKE TIME", "STAY SOFT", "QUIETLY",
    "SIMPLE", "LOW KEY", "FRESH AIR", "SMALL JOY", "COZY", "OPEN SKY", "LITTLE SUN", "WARM NOTE", "DAILY", "CALM DOWN",
    "NICE DAY", "WALK SLOW", "LIGHTLY", "SOFT LINE", "CAFE HOUR", "MOON NOTE", "STILL HERE", "EASY WALK", "GOOD DAY", "SOFT WAVE",
    "REST MODE", "SLOWLY", "TINY JOY", "MORNING", "AFTERNOON", "GOOD NIGHT", "LOCAL DAY", "DREAM ON", "BRIGHT", "NEAR HOME",
    "PURE TYPE", "ONE DAY", "MILD SUN", "HALF PACE", "KIND WORD", "FREE TIME", "SOFT ROAD", "NO RUSH", "SUNNY", "FEEL GOOD",
]


def all_phrases() -> list[Phrase]:
    phrases = (
        [Phrase("韩文", text) for text in KOREAN]
        + [Phrase("日文", text) for text in JAPANESE]
        + [Phrase("中文", text) for text in CHINESE]
        + [Phrase("英文", text) for text in ENGLISH]
    )
    if len(phrases) != 200:
        raise RuntimeError(f"Expected 200 phrases, got {len(phrases)}")
    return phrases


def font_for(lang: str, variant: int) -> Path:
    if lang == "韩文":
        return [FONT_DIR / "malgunbd.ttf", FONT_DIR / "malgun.ttf"][variant % 2]
    if lang == "日文":
        return [FONT_DIR / "YuGothB.ttc", FONT_DIR / "msgothic.ttc"][variant % 2]
    if lang == "中文":
        return [FONT_DIR / "STKAITI.TTF", FONT_DIR / "msyhbd.ttc", FONT_DIR / "simhei.ttf"][variant % 3]
    return [FONT_DIR / "GOTHICB.TTF", FONT_DIR / "GOTHIC.TTF"][variant % 2]


def load_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    if not path.exists():
        raise FileNotFoundError(f"Font not found: {path}")
    return ImageFont.truetype(str(path), size=size)


def split_lines(text: str, lang: str) -> tuple[str, ...]:
    if lang == "英文" and " " in text:
        words = text.split()
        if len(words) == 2:
            return words[0], words[1]
    compact = text.replace(" ", "")
    if lang != "英文" and len(compact) >= 5:
        mid = len(compact) // 2
        return compact[:mid], compact[mid:]
    return (text,)


def font_size_for(text: str, lang: str) -> int:
    length = len(text.replace(" ", ""))
    if lang == "英文":
        return 218 if length <= 6 else 178 if length <= 9 else 148
    if lang == "中文":
        return 306 if length <= 3 else 250 if length <= 4 else 210
    if lang == "日文":
        return 292 if length <= 3 else 238 if length <= 4 else 200
    return 308 if length <= 2 else 248 if length <= 4 else 205


def tracked_text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, tracking: int, stroke_width: int) -> tuple[int, int]:
    widths: list[int] = []
    heights: list[int] = []
    for char in text:
        box = draw.textbbox((0, 0), char, font=font, stroke_width=stroke_width)
        widths.append(box[2] - box[0])
        heights.append(box[3] - box[1])
    return sum(widths) + max(0, len(text) - 1) * tracking, max(heights or [0])


def draw_tracked_text(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    stroke: tuple[int, int, int, int],
    stroke_width: int,
    tracking: int,
) -> None:
    for char in text:
        draw.text((x, y), char, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke)
        box = draw.textbbox((x, y), char, font=font, stroke_width=stroke_width)
        x += box[2] - box[0] + tracking


def add_accent(draw: ImageDraw.ImageDraw, style: str, bbox: tuple[int, int, int, int], color: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = bbox
    cx = (left + right) // 2
    if style == "underline":
        draw.rounded_rectangle((left + 18, bottom + 38, right - 18, bottom + 52), radius=7, fill=color)
    elif style == "dots":
        for offset in (-58, 0, 58):
            draw.ellipse((cx + offset - 11, bottom + 34, cx + offset + 11, bottom + 56), fill=color)
    elif style == "thin_frame":
        draw.rounded_rectangle((left - 45, top - 28, right + 45, bottom + 36), radius=34, outline=color, width=8)
    elif style == "side_marks":
        draw.rounded_rectangle((left - 55, top + 22, left - 38, bottom - 8), radius=8, fill=color)
        draw.rounded_rectangle((right + 38, top + 22, right + 55, bottom - 8), radius=8, fill=color)
    elif style == "corner_marks":
        size = 40
        draw.line((left - 50, top - 26, left - 50 + size, top - 26), fill=color, width=8)
        draw.line((left - 50, top - 26, left - 50, top - 26 + size), fill=color, width=8)
        draw.line((right + 50, bottom + 26, right + 50 - size, bottom + 26), fill=color, width=8)
        draw.line((right + 50, bottom + 26, right + 50, bottom + 26 - size), fill=color, width=8)
    elif style == "slash":
        draw.line((cx - 76, top - 34, cx - 45, top - 68), fill=color, width=10)
        draw.line((cx + 45, bottom + 68, cx + 76, bottom + 34), fill=color, width=10)


def render_print(sku: str, phrase: Phrase, index: int, print_dir: Path) -> Path:
    font = load_font(font_for(phrase.lang, index), font_size_for(phrase.text, phrase.lang))
    lines = split_lines(phrase.text, phrase.lang)
    fill_options = [(16, 16, 16, 255), (31, 33, 35, 255), (24, 39, 35, 255)]
    stroke_options = [(252, 248, 235, 255), (246, 246, 240, 255), (238, 232, 222, 255)]
    accent_options = [(174, 55, 50, 255), (68, 105, 91, 255), (84, 101, 142, 255), (178, 132, 84, 255)]
    accent_styles = ["underline", "dots", "thin_frame", "side_marks", "corner_marks", "slash"]
    fill = fill_options[index % len(fill_options)]
    stroke = stroke_options[index % len(stroke_options)]
    accent = accent_options[index % len(accent_options)]
    accent_style = accent_styles[index % len(accent_styles)]
    tracking = (index % 6) * 2 - 3
    stroke_width = 10
    line_gap = 4 + (index % 4) * 5

    canvas = Image.new("RGBA", (1500, 1500), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    sizes = [tracked_text_size(draw, line, font, tracking, stroke_width) for line in lines]
    total_h = sum(height for _, height in sizes) + max(0, len(lines) - 1) * line_gap
    y = (canvas.height - total_h) // 2
    boxes: list[tuple[int, int, int, int]] = []
    for line, (line_w, line_h) in zip(lines, sizes):
        x = (canvas.width - line_w) // 2
        draw_tracked_text(draw, x, y, line, font, fill, stroke, stroke_width, tracking)
        boxes.append((x, y, x + line_w, y + line_h))
        y += line_h + line_gap

    bbox = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
    add_accent(draw, accent_style, bbox, accent)

    crop = canvas.getbbox()
    if crop:
        pad = 105
        canvas = canvas.crop((max(0, crop[0] - pad), max(0, crop[1] - pad), min(canvas.width, crop[2] + pad), min(canvas.height, crop[3] + pad)))

    print_dir.mkdir(parents=True, exist_ok=True)
    path = print_dir / f"{sku}.png"
    canvas.save(path)
    return path


def shirt_color(model_path: Path) -> str:
    img = ImageOps.exif_transpose(Image.open(model_path)).convert("RGB")
    w, h = img.size
    crop = img.crop((int(w * 0.32), int(h * 0.22), int(w * 0.68), int(h * 0.62)))
    arr = np.asarray(crop, dtype=np.float32)
    luma = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    return "白" if float(np.median(luma)) >= 150 else "黑"


def title_for(phrase: Phrase, color: str) -> str:
    color_word = "白色" if color == "白" else "黑色"
    phrase_word = phrase.text.replace(" ", "")
    return medium_title(color_word, phrase_word)


def simplified_title_from_existing(old_title: str) -> str:
    color_word = "白色" if "白色" in old_title else "黑色" if "黑色" in old_title else ""
    match = re.search(r"简约艺术字(.+?)印花T恤", old_title)
    phrase_word = match.group(1).replace(" ", "") if match else ""
    return medium_title(color_word, phrase_word)


def medium_title(color_word: str, phrase_word: str) -> str:
    variants = [
        "圆领短袖 透气微弹针织上衣 日常休闲百搭",
        "圆领短袖 透气舒适针织上衣 户外休闲日常百搭",
        "圆领短袖 轻薄透气针织上衣 休闲通勤日常百搭",
        "圆领短袖 柔软透气针织上衣 夏季日常百搭",
    ]
    key = sum(ord(char) for char in color_word + phrase_word)
    suffix = variants[key % len(variants)]
    return f"夏季{color_word}简约艺术字{phrase_word}印花T恤 {suffix}"


def safe_filename(text: str) -> str:
    invalid_chars = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid_chars or ord(char) < 32 else char for char in text)
    return re.sub(r"_+", "_", cleaned).strip(" ._")


def win_path(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def make_overview(paths: list[Path], output_path: Path) -> None:
    tile_w, tile_h = 220, 290
    cols = 10
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (235, 235, 235))
    for index, path in enumerate(paths):
        img = Image.open(path).convert("RGB")
        img.thumbnail((200, 230), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (tile_w, tile_h), "white")
        tile.paste(img, ((tile_w - img.width) // 2, 8))
        draw = ImageDraw.Draw(tile)
        draw.text((8, 260), path.stem[:28], fill=(0, 0, 0))
        sheet.paste(tile, ((index % cols) * tile_w, (index // cols) * tile_h))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=92)


def build_sheet_xml(rows: list[tuple[str, str, str, str, str]]) -> str:
    def cell(ref: str, value: str, style: int | None = None) -> str:
        s_attr = "" if style is None else f' s="{style}"'
        return f'<c r="{ref}" t="inlineStr"{s_attr}><is><t>{escape(value)}</t></is></c>'

    row_xml: list[str] = []
    for row_idx, values in enumerate(rows, start=1):
        style = 1 if row_idx == 1 else None
        cells = "".join(cell(f"{chr(65 + col)}{row_idx}", value, style) for col, value in enumerate(values))
        row_xml.append(f'<row r="{row_idx}">{cells}</row>')
    dimension = f"A1:E{len(rows)}"
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="{dimension}"/>'
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


def write_xlsx_from_rows(rows_without_header: list[tuple[str, str, str, str, str]], output_xlsx: Path) -> None:
    rows: list[tuple[str, str, str, str, str]] = [("店铺名称", "产品分类", "产品标题", "产品序列号", "颜色")]
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


def write_xlsx_from_mockup_filenames(mockup_dir: Path, output_xlsx: Path, expected_count: int) -> None:
    rows = rows_from_mockup_filenames(mockup_dir)
    if len(rows) != expected_count:
        raise RuntimeError(f"Expected {expected_count} product image rows, got {len(rows)} from {mockup_dir}")
    write_xlsx_from_rows(rows, output_xlsx)


def simplify_existing_mockup_titles(mockup_dir: Path = LEGACY_MOCKUP_DIR) -> int:
    pattern = re.compile(r"^(BO-\d+)_(.+)\.png$", re.IGNORECASE)
    renamed = 0
    for path in list_images(mockup_dir):
        if path.name.startswith("_"):
            continue
        match = pattern.match(path.name)
        if not match:
            continue
        sku, old_title = match.groups()
        new_title = simplified_title_from_existing(old_title)
        new_name = safe_filename(f"{sku}_{new_title}.png")
        new_path = path.with_name(new_name)
        if path.name == new_name:
            continue
        if new_path.exists():
            raise FileExistsError(f"Target exists: {new_path}")
        os.replace(win_path(path), win_path(new_path))
        renamed += 1
    write_xlsx_from_mockup_filenames(mockup_dir, LEGACY_OUTPUT_XLSX, 200)
    return renamed


def copy_existing_mockups_with_simplified_titles(
    source_dir: Path = LEGACY_MOCKUP_DIR,
    target_dir: Path = LEGACY_SIMPLIFIED_MOCKUP_DIR,
) -> int:
    pattern = re.compile(r"^(BO-\d+)_(.+)\.png$", re.IGNORECASE)
    target_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for path in list_images(source_dir):
        if path.name.startswith("_"):
            continue
        match = pattern.match(path.name)
        if not match:
            continue
        sku, old_title = match.groups()
        new_title = simplified_title_from_existing(old_title)
        new_path = target_dir / safe_filename(f"{sku}_{new_title}.png")
        shutil.copy2(path, new_path)
        copied += 1
    overview = source_dir / "_overview.jpg"
    if overview.exists():
        shutil.copy2(overview, target_dir / "_overview_old_titles.jpg")
    write_xlsx_from_mockup_filenames(target_dir, LEGACY_OUTPUT_XLSX, 200)
    return copied


def write_prompt_file(items: list[PrintItem], prompt_file: Path) -> None:
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"简约艺术字文字印花 {len(items)} 款：主体只保留文字，辅以少量下划线、点、细框、角标。",
        "所有印花贴在黑色、白色或深浅不同 T 恤上都必须清晰可见，采用深色主体加浅色描边和高对比点线辅助。",
    ]
    lines.extend(f"{item.sku}: {item.phrase.lang} {item.phrase.text}" for item in items)
    prompt_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(start: int, count: int, seed: int, batch_date: str | None = None) -> tuple[list[PrintItem], list[MockupItem], Path, Path, Path]:
    print_dir, mockup_dir, prompt_file, output_xlsx = batch_paths(start, count, batch_date)
    phrases = all_phrases()
    rng = random.Random(seed)
    rng.shuffle(phrases)
    phrases = phrases[:count]
    models = list_images(MODEL_DIR)
    if not models:
        raise FileNotFoundError(f"No model images found: {MODEL_DIR}")

    print_items: list[PrintItem] = []
    for idx, phrase in enumerate(phrases):
        sku = f"BO-{start + idx}"
        path = render_print(sku, phrase, idx, print_dir)
        print_items.append(PrintItem(sku=sku, phrase=phrase, print_path=path))
    write_prompt_file(print_items, prompt_file)

    shuffled_prints = print_items[:]
    rng.shuffle(shuffled_prints)
    placement = Placement(center_x=0.50, center_y=0.42, width=0.28, opacity=0.96, rotation=0, shadow_strength=0.28, wave_strength=0.006, remove_white_bg=False)
    mockup_dir.mkdir(parents=True, exist_ok=True)
    mockups: list[MockupItem] = []
    for item in shuffled_prints:
        model_path = rng.choice(models)
        color = shirt_color(model_path)
        title = title_for(item.phrase, color)
        filename = safe_filename(f"{item.sku}_{title}.png")
        output_path = mockup_dir / filename
        composite_one(model_path, item.print_path, output_path, placement)
        mockups.append(MockupItem(item.sku, title, color, model_path, item.print_path, output_path))
        print(f"{item.sku}: exported")
    make_overview([item.output_path for item in mockups], mockup_dir / "_overview.jpg")
    write_xlsx_from_mockup_filenames(mockup_dir, output_xlsx, count)
    return print_items, mockups, print_dir, mockup_dir, output_xlsx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate BO minimal typography prints, unique random mockups, and xlsx metadata.")
    parser.add_argument("--start", type=int, default=306)
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260610)
    parser.add_argument("--date", default=None, help="Batch date stamp, defaults to today (YYYY-MM-DD).")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print_items, mockups, print_dir, mockup_dir, output_xlsx = run(args.start, args.count, args.seed, args.date)
    print(f"Created {len(print_items)} print(s): {print_dir}")
    print(f"Created {len(mockups)} mockup(s): {mockup_dir}")
    print(f"Created xlsx: {output_xlsx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
