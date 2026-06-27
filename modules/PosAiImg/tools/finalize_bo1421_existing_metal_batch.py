from __future__ import annotations

import json
import math
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
START = 1421
SOURCE_DIR = ROOT / "印花图_透明底" / "imggen_爆款1_金属字_5张"
COUNT = len([p for p in SOURCE_DIR.glob("metal_spiky_print_*.png") if p.is_file()])
STAMP = date.today().isoformat()
BATCH_NAME = f"爆款金属字印花_BO-{START}-BO-{START + COUNT - 1}_{STAMP}"
PRINT_DIR = ROOT / "印花图_透明底" / BATCH_NAME
MOCKUP_DIR = ROOT / "批量贴图结果" / f"{BATCH_NAME}_按色主图{COUNT}"
PROMPT_FILE = ROOT / "生成提示词" / f"{BATCH_NAME}.txt"
XLSX_PATH = ROOT / "衣物对应的xlsx" / "简约200" / f"{BATCH_NAME}.xlsx"
TEMPLATE_DIR = ROOT / "衣物对应的xlsx" / "简约200"
MODEL_DIR = ROOT / "模特图-干净"
PROGRESS_FILE = ROOT / "BO_PROGRESS.md"
PUTAWAY_DATA_DIR = Path(r"E:\1PythonProject\PutawayAiRobot\data")
PUTAWAY_PIC_DIR = PUTAWAY_DATA_DIR / "pic" / "1"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

KEYWORDS = ["尖刺银字", "重铬字形", "暗纹金属字", "锋利链字", "银灰爆裂字"]
SELLING_POINTS = [
    "圆领短袖 透气微弹针织上衣 日常休闲百搭",
    "圆领短袖 透气舒适针织上衣 户外休闲日常百搭",
    "圆领短袖 轻薄透气针织上衣 休闲通勤日常百搭",
    "圆领短袖 柔软透气针织上衣 夏季日常百搭",
]


@dataclass(frozen=True)
class PrintItem:
    sku: str
    keyword: str
    path: Path
    source: Path
    luma: float


def safe_filename(text: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid or ord(char) < 32 else char for char in text)
    return re.sub(r"_+", "_", cleaned).strip(" ._")


def alpha_luma(path: Path) -> float:
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
    arr = np.asarray(img, dtype=np.float32)
    alpha = arr[..., 3] > 12
    if not np.any(alpha):
        return 255.0
    rgb = arr[..., :3][alpha]
    luma = 0.2126 * rgb[:, 0] + 0.7152 * rgb[:, 1] + 0.0722 * rgb[:, 2]
    return float(np.median(luma))


def shirt_color(model_path: Path) -> tuple[str, str]:
    stem = model_path.stem
    if "白" in stem:
        return "白色", "白"
    if "黑" in stem:
        return "黑色", "黑"
    img = ImageOps.exif_transpose(Image.open(model_path)).convert("RGB")
    w, h = img.size
    crop = img.crop((int(w * 0.32), int(h * 0.22), int(w * 0.68), int(h * 0.62)))
    arr = np.asarray(crop, dtype=np.float32)
    luma = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    return ("白色", "白") if float(np.median(luma)) >= 150 else ("黑色", "黑")


def choose_model(print_luma: float, index: int) -> Path:
    models = list_images(MODEL_DIR)
    black = [p for p in models if "黑" in p.stem]
    white = [p for p in models if "白" in p.stem]
    if not black or not white:
        raise FileNotFoundError(f"Need black and white model images in {MODEL_DIR}")
    candidates = black if print_luma >= 145 else white
    return candidates[index % len(candidates)]


def product_title(color_word: str, keyword: str) -> str:
    suffix = SELLING_POINTS[sum(ord(c) for c in color_word + keyword) % len(SELLING_POINTS)]
    return f"夏季{color_word}高街金属字{keyword}印花T恤 {suffix}"


def make_overview(paths: list[Path], output: Path) -> None:
    cols, tile_w, tile_h = 5, 260, 330
    rows = max(1, math.ceil(len(paths) / cols))
    sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (235, 235, 235))
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 14)
    except OSError:
        font = ImageFont.load_default()
    for index, path in enumerate(paths):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        img.thumbnail((240, 268), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (tile_w, tile_h), "white")
        tile.paste(img, ((tile_w - img.width) // 2, 8))
        ImageDraw.Draw(tile).text((8, 286), path.stem[:32], fill=(0, 0, 0), font=font)
        sheet.paste(tile, ((index % cols) * tile_w, (index // cols) * tile_h))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)


def build_sheet_xml(rows: list[tuple[str, str, str, str, str]]) -> str:
    def cell(ref: str, value: str, style: int | None = None) -> str:
        style_attr = "" if style is None else f' s="{style}"'
        return f'<c r="{ref}" t="inlineStr"{style_attr}><is><t>{escape(value)}</t></is></c>'

    row_xml = []
    for row_idx, values in enumerate(rows, 1):
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
        "</worksheet>"
    )


def rows_from_product_filenames(mockup_dir: Path) -> list[tuple[str, str, str, str, str]]:
    pattern = re.compile(r"^(BO-\d+)_(.+)\.png$", re.IGNORECASE)
    rows = []
    for path in list_images(mockup_dir):
        if path.name.startswith("_"):
            continue
        match = pattern.match(path.name)
        if not match:
            continue
        sku, title = match.groups()
        color = "白" if "白色" in title else "黑" if "黑色" in title else ""
        rows.append(("YUHAOBO", "T恤", title, sku, color))
    return sorted(rows, key=lambda row: int(row[3].split("-")[1]))


def write_xlsx(mockup_dir: Path, output_xlsx: Path, expected_count: int) -> None:
    rows = [("店铺名称", "产品分类", "产品标题", "产品序列号", "颜色"), *rows_from_product_filenames(mockup_dir)]
    if len(rows) != expected_count + 1:
        raise RuntimeError(f"Expected {expected_count + 1} xlsx rows including header, got {len(rows)}")
    templates = [p for p in TEMPLATE_DIR.glob("*.xlsx") if not p.name.startswith("~$")]
    if not templates:
        raise FileNotFoundError(f"No xlsx template found in {TEMPLATE_DIR}")
    template = sorted(templates, key=lambda p: p.stat().st_mtime, reverse=True)[0]
    output_xlsx.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_xlsx.with_suffix(".tmp.xlsx")
    shutil.copy2(template, tmp)
    with zipfile.ZipFile(tmp, "r") as src, zipfile.ZipFile(output_xlsx, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = build_sheet_xml(rows) if info.filename == "xl/worksheets/sheet1.xml" else src.read(info.filename)
            dst.writestr(info, data)
    tmp.unlink(missing_ok=True)


def prepare_prints() -> list[PrintItem]:
    sources = sorted(p for p in SOURCE_DIR.glob("metal_spiky_print_*.png") if p.is_file())
    if not sources:
        raise FileNotFoundError(f"No existing metal print PNGs found in {SOURCE_DIR}")
    PRINT_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for idx, source in enumerate(sources):
        sku = f"BO-{START + idx}"
        target = PRINT_DIR / f"{sku}.png"
        shutil.copy2(source, target)
        keyword = KEYWORDS[idx % len(KEYWORDS)]
        items.append(PrintItem(sku=sku, keyword=keyword, path=target, source=source, luma=alpha_luma(target)))
    PROMPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"{BATCH_NAME}",
        "本批次只接收上一轮已落盘的 5 张金属字透明底图，不继续补生成图片。",
        "贴图主图按印花主体亮度选择：浅色印花贴黑 T，深色印花贴白 T。",
    ]
    lines.extend(f"{item.sku}\t{item.keyword}\t{item.source.name}\tluma={item.luma:.1f}" for item in items)
    PROMPT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return items


def make_products(items: list[PrintItem]) -> list[Path]:
    MOCKUP_DIR.mkdir(parents=True, exist_ok=True)
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
    outputs = []
    for idx, item in enumerate(items):
        model = choose_model(item.luma, idx)
        color_word, _ = shirt_color(model)
        title = product_title(color_word, item.keyword)
        output = MOCKUP_DIR / safe_filename(f"{item.sku}_{title}.png")
        composite_one(model, item.path, output, placement)
        outputs.append(output)
    make_overview(outputs, MOCKUP_DIR / "_overview.jpg")
    return outputs


def sku_numbers(paths: list[Path]) -> list[int]:
    values = []
    for path in paths:
        match = re.search(r"BO-(\d+)", path.name, re.IGNORECASE)
        if match:
            values.append(int(match.group(1)))
    return sorted(values)


def validate_outputs() -> dict:
    expected = list(range(START, START + COUNT))
    print_files = sorted(p for p in list_images(PRINT_DIR) if re.fullmatch(r"BO-\d+\.png", p.name, re.IGNORECASE))
    product_files = sorted(p for p in list_images(MOCKUP_DIR) if not p.name.startswith("_"))
    rows = rows_from_product_filenames(MOCKUP_DIR)
    summary = {
        "print_count": len(print_files),
        "product_count": len(product_files),
        "print_skus": sku_numbers(print_files),
        "product_skus": sku_numbers(product_files),
        "xlsx_exists": XLSX_PATH.exists(),
        "xlsx_rows_including_header": len(rows) + 1,
        "xlsx_first_sku": rows[0][3] if rows else "",
        "xlsx_last_sku": rows[-1][3] if rows else "",
        "overview_exists": (MOCKUP_DIR / "_overview.jpg").exists(),
    }
    if summary["print_count"] != COUNT or summary["product_count"] != COUNT:
        raise RuntimeError(f"Count validation failed: {summary}")
    if summary["print_skus"] != expected or summary["product_skus"] != expected:
        raise RuntimeError(f"SKU validation failed: {summary}")
    if not XLSX_PATH.exists() or len(rows) != COUNT:
        raise RuntimeError(f"XLSX validation failed: {summary}")
    return summary


def sync_putaway() -> None:
    PUTAWAY_PIC_DIR.mkdir(parents=True, exist_ok=True)
    for path in PUTAWAY_PIC_DIR.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            path.unlink()
    for path in list_images(MOCKUP_DIR):
        if not path.name.startswith("_"):
            shutil.copy2(path, PUTAWAY_PIC_DIR / path.name)
    PUTAWAY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(XLSX_PATH, PUTAWAY_DATA_DIR / XLSX_PATH.name)


def validate_putaway() -> dict:
    expected = list(range(START, START + COUNT))
    files = sorted(p for p in list_images(PUTAWAY_PIC_DIR) if not p.name.startswith("_"))
    summary = {
        "putaway_pic_count": len(files),
        "putaway_skus": sku_numbers(files),
        "putaway_range_ok": sku_numbers(files) == expected,
        "putaway_xlsx_exists": (PUTAWAY_DATA_DIR / XLSX_PATH.name).exists(),
    }
    if len(files) != COUNT or sku_numbers(files) != expected or not summary["putaway_xlsx_exists"]:
        raise RuntimeError(f"Putaway validation failed: {summary}")
    return summary


def update_progress(validation: dict, putaway: dict) -> None:
    end = START + COUNT - 1
    next_start = end + 1
    text = PROGRESS_FILE.read_text(encoding="utf-8")
    text = re.sub(r"更新时间[：:]\s*.*", f"更新时间：{STAMP}", text)
    text = re.sub(r"上次已分配到[：:]\s*BO-\d+", f"上次已分配到：BO-{end}", text)
    text = re.sub(r"下次建议从[：:]\s*BO-\d+", f"下次建议从：BO-{next_start}", text)
    addition = (
        f"\n- {STAMP} 按用户要求接续上一轮已生成图片，不再补生成；从 BO-{START} 整理 {COUNT} 张爆款金属字印花，实际范围为 BO-{START} 到 BO-{end}。\n"
        f"- `{PRINT_DIR}` 当前校验为 {validation['print_count']} 张，范围 BO-{START} 到 BO-{end}，无缺号，透明通道来自已落盘透明底图。\n"
        f"- `{MOCKUP_DIR}` 当前校验为 {validation['product_count']} 张，范围 BO-{START} 到 BO-{end}，无缺号；主图按印花亮度选择黑/白 T。\n"
        f"- `{XLSX_PATH}` 当前校验为 {COUNT + 1} 行，表头为 店铺名称、产品分类、产品标题、产品序列号、颜色，首条 BO-{START}，末条 BO-{end}。\n"
        f"- 本批已同步到 `{PUTAWAY_PIC_DIR}`，目标目录校验为 {putaway['putaway_pic_count']} 张，范围 BO-{START} 到 BO-{end}，无缺号；xlsx 已复制到 `{PUTAWAY_DATA_DIR}`。\n"
        f"- 视觉抽查：已生成 `_overview.jpg`，本批只有当前可提取的 {COUNT} 张金属字图；未继续补生成 BO-{next_start} 之后图片。\n"
    )
    marker = "## 后续规则"
    if marker in text:
        text = text.replace(marker, addition + "\n" + marker, 1)
    else:
        text += addition
    PROGRESS_FILE.write_text(text, encoding="utf-8")


def main() -> int:
    items = prepare_prints()
    outputs = make_products(items)
    write_xlsx(MOCKUP_DIR, XLSX_PATH, COUNT)
    validation = validate_outputs()
    sync_putaway()
    putaway = validate_putaway()
    update_progress(validation, putaway)
    print(
        json.dumps(
            {
                "batch": BATCH_NAME,
                "print_dir": str(PRINT_DIR),
                "mockup_dir": str(MOCKUP_DIR),
                "xlsx": str(XLSX_PATH),
                "prompt": str(PROMPT_FILE),
                "products": [str(p) for p in outputs],
                "validation": validation,
                "putaway": putaway,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
