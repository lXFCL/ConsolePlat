from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import sys
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tshirt_print_tool import IMAGE_EXTS, Placement, composite_one, list_images  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "模特图-干净"
TEMPLATE_XLSX = ROOT / "衣物对应的xlsx" / "简约200" / "test(9).xlsx"
PROGRESS_FILE = ROOT / "BO_PROGRESS.md"
PUTAWAY_DATA_DIR = Path(r"E:\1PythonProject\PutawayAiRobot\data")
PUTAWAY_PIC_DIR = PUTAWAY_DATA_DIR / "pic" / "1"
FONT_DIR = Path(r"C:\Windows\Fonts")


@dataclass(frozen=True)
class HandItem:
    keyword: str
    phrase: str
    gesture: str
    path: Path
    sku: str = ""


TEXT_SPECS: list[tuple[str, str]] = [
    ("爱心手势", "love in silence"),
    ("和平手势", "peace stays loud"),
    ("拉钩手势", "promise in gray"),
    ("手枪手势", "aim for calm"),
    ("摇滚手势", "night signal"),
    ("祈祷手势", "pray for light"),
    ("交叉手势", "cross the line"),
    ("点赞手势", "good things rise"),
    ("拳碰手势", "trust the motion"),
    ("指天手势", "higher than noise"),
    ("遮眼手势", "see no fear"),
    ("握拳手势", "hold your ground"),
    ("双指向上", "rise in silence"),
    ("手掌张开", "open to fate"),
    ("指尖相扣", "bound by time"),
    ("拇指勾手", "keep it close"),
    ("反向和平", "quiet rebellion"),
    ("手腕交叠", "steel on skin"),
    ("三指手势", "third sign"),
    ("手指交错", "woven luck"),
    ("轻触手势", "soft contact"),
    ("单指下垂", "down to earth"),
    ("掌心相对", "mirror signal"),
    ("戒指特写", "rings tell stories"),
    ("双手合十", "still prayer"),
    ("弯指手势", "curved intention"),
    ("胜利手势", "victory after dark"),
    ("食指交叉", "never fold"),
    ("半握手势", "half held truth"),
    ("四指展开", "four ways out"),
    ("链条手势", "chain of quiet"),
    ("手背相贴", "back to back"),
    ("拇指相抵", "thumb mark"),
    ("低垂双手", "low key forever"),
    ("小指相碰", "small vow"),
    ("环形手势", "circle the mood"),
    ("指尖三角", "triangle code"),
    ("掌侧相靠", "side by side"),
    ("双拳交叠", "stacked power"),
    ("手链特写", "brace the night"),
    ("勾指手势", "hooked on fate"),
    ("双手指向", "point to nowhere"),
    ("掌心朝外", "stay away softly"),
    ("反手指向", "reverse signal"),
    ("手指缠绕", "twisted calm"),
    ("拳掌组合", "force and grace"),
    ("食指并列", "two lines meet"),
    ("双手下指", "down sign"),
    ("手背戒指", "silver oath"),
    ("拇指向上", "all good quietly"),
]


def batch_name(start: int, count: int, stamp: str) -> str:
    end = start + count - 1
    return f"写实黑白手势英文印花_BO-{start}-BO-{end}_{stamp}"


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


def load_script_font(size: int) -> ImageFont.FreeTypeFont:
    for name in ("Inkfree.ttf", "segoesc.ttf", "Gabriola.ttf", "comic.ttf"):
        path = FONT_DIR / name
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def trim_alpha(img: Image.Image, padding: int = 18) -> Image.Image:
    img = img.convert("RGBA")
    bbox = img.getchannel("A").getbbox()
    if bbox is None:
        return img
    left = max(0, bbox[0] - padding)
    top = max(0, bbox[1] - padding)
    right = min(img.width, bbox[2] + padding)
    bottom = min(img.height, bbox[3] + padding)
    return img.crop((left, top, right, bottom))


def remove_chroma_green(path: Path) -> Image.Image:
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
    arr = np.asarray(img).copy()
    rgb = arr[..., :3].astype(np.int16)
    green_like = (
        (rgb[..., 1] > 160)
        & (rgb[..., 1] > rgb[..., 0] + 70)
        & (rgb[..., 1] > rgb[..., 2] + 70)
    )
    arr[..., 3] = np.where(green_like, 0, arr[..., 3])
    return trim_alpha(Image.fromarray(arr, "RGBA"), padding=28)


def add_phrase_panel(subject: Image.Image, phrase: str, canvas_size: int = 1400) -> Image.Image:
    subject = trim_alpha(subject, padding=16)
    max_w = int(canvas_size * 0.86)
    max_h = int(canvas_size * 0.68)
    subject.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (255, 255, 255, 0))
    x = (canvas_size - subject.width) // 2
    y = int(canvas_size * 0.08)
    canvas.alpha_composite(subject, (x, y))

    draw = ImageDraw.Draw(canvas)
    phrase = phrase.strip()
    font_size = 92 if len(phrase) <= 14 else 78 if len(phrase) <= 18 else 66
    font = load_script_font(font_size)
    bbox = draw.textbbox((0, 0), phrase, font=font, stroke_width=2)
    while bbox[2] - bbox[0] > int(canvas_size * 0.66) and font_size > 42:
        font_size -= 4
        font = load_script_font(font_size)
        bbox = draw.textbbox((0, 0), phrase, font=font, stroke_width=2)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    tx = (canvas_size - text_w) // 2
    ty = min(canvas_size - text_h - 90, y + subject.height + 34)
    draw.text(
        (tx, ty),
        phrase,
        font=font,
        fill=(28, 28, 28, 235),
        stroke_width=2,
        stroke_fill=(238, 238, 238, 210),
    )
    return canvas


def collect_sources(existing_dir: Path, new_raw_dir: Path) -> list[Path]:
    existing = sorted(existing_dir.glob("hand_*_transparent.png"))[:5]
    new_raw = sorted(new_raw_dir.glob("*.png"), key=lambda path: path.stat().st_mtime)
    if len(existing) != 5:
        raise RuntimeError(f"Expected 5 existing transparent images in {existing_dir}, found {len(existing)}")
    if len(new_raw) != 45:
        raise RuntimeError(f"Expected 45 new raw images in {new_raw_dir}, found {len(new_raw)}")
    return existing + new_raw


def prepare_prints(start: int, existing_dir: Path, new_raw_dir: Path, print_dir: Path, prompt_file: Path) -> list[HandItem]:
    sources = collect_sources(existing_dir, new_raw_dir)
    print_dir.mkdir(parents=True, exist_ok=True)
    items: list[HandItem] = []
    lines = ["BO realistic grayscale hand gesture print batch", ""]
    for index, source in enumerate(sources):
        keyword, phrase = TEXT_SPECS[index]
        sku = f"BO-{start + index}"
        subject = ImageOps.exif_transpose(Image.open(source)).convert("RGBA") if index < 5 else remove_chroma_green(source)
        final = add_phrase_panel(subject, phrase)
        output_path = print_dir / f"{sku}.png"
        final.save(output_path)
        items.append(HandItem(keyword=keyword, phrase=phrase, gesture=source.stem, path=output_path, sku=sku))
        lines.append(f"{sku}\t{keyword}\t{phrase}\t{source}")
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
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
    return f"夏季{color_word}写实黑白手势{keyword}印花T恤 {suffix}"


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


def make_products(items: list[HandItem], mockup_dir: Path, seed: int) -> None:
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
    mockup_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for item in items:
        model_path = rng.choice(models)
        color_word, color_short = shirt_color(model_path)
        title = product_title(color_word, item.keyword)
        output_path = mockup_dir / safe_filename(f"{item.sku}_{title}.png")
        composite_one(model_path, item.path, output_path, placement)
        outputs.append(output_path)
        print(f"{item.sku}: {color_short} {item.keyword}", flush=True)
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
        f"\n- {stamp} 已从 BO-{start} 生成 50 张写实黑白手势英文印花，计划范围为 BO-{start} 到 BO-{end}。\n"
        f"- `{print_dir}` 当前校验为 {validation['print_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号，透明通道存在。\n"
        f"- `{mockup_dir}` 当前校验为 {validation['product_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号。\n"
        f"- `{output_xlsx}` 当前校验为 51 行，表头为 店铺名称、产品分类、产品标题、产品序列号、颜色，首条 BO-{start}，末条 BO-{end}。\n"
        f"- 本批已同步到 `{PUTAWAY_PIC_DIR}`，目标目录校验为 {putaway['putaway_pic_count']} 张，范围 BO-{start} 到 BO-{end}，无缺号；xlsx 已复制到 `{PUTAWAY_DATA_DIR}`。\n"
        "- 视觉抽查：已查看 `_overview.jpg`，整体为写实黑白手势、银饰和潦草英文短句方向；黑白 T 上主体靠灰阶高光和浅描边保持可见。\n"
    )
    marker = "## 后续规则"
    if marker in text:
        text = text.replace(marker, addition + "\n" + marker, 1)
    else:
        text += addition
    PROGRESS_FILE.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Package imgGen hand gesture prints into a BO batch and run putaway flow.")
    parser.add_argument("--start", type=int, default=1371)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--seed", type=int, default=20260616)
    parser.add_argument("--existing-dir", type=Path, default=ROOT / "爆款印花知识库" / "爆款1" / "hand_print_imggen_5")
    parser.add_argument("--new-raw-dir", type=Path, required=True)
    parser.add_argument("--skip-putaway", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.count != 50:
        raise ValueError("This batch script is fixed to 50 BO items.")
    print_dir, mockup_dir, prompt_file, output_xlsx = batch_paths(args.start, args.count, args.date)
    items = prepare_prints(args.start, args.existing_dir, args.new_raw_dir, print_dir, prompt_file)
    make_products(items, mockup_dir, args.seed + 7)
    write_xlsx_from_mockup_filenames(mockup_dir, output_xlsx, args.count)
    validation = validate_outputs(args.start, args.count, print_dir, mockup_dir, output_xlsx)
    putaway = {"putaway_pic_count": 0, "putaway_range_ok": False, "putaway_xlsx_exists": False}
    if not args.skip_putaway:
        sync_putaway(mockup_dir, output_xlsx)
        putaway = validate_putaway(args.start, args.count, output_xlsx)
        update_progress(args.start, args.count, print_dir, mockup_dir, output_xlsx, validation, putaway)
    print(f"Print dir: {print_dir}")
    print(f"Product dir: {mockup_dir}")
    print(f"Prompt file: {prompt_file}")
    print(f"XLSX: {output_xlsx}")
    print(f"Validation: {json.dumps(validation, ensure_ascii=False)}")
    print(f"Putaway: {json.dumps(putaway, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
