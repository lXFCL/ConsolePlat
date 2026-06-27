from __future__ import annotations

import argparse
import os
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
from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

import render_small_right_chest_batch_50 as badge  # noqa: E402
from tshirt_print_tool import Placement, composite_one, list_images  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "\u6a21\u7279\u56fe-\u5e72\u51c0"
PRINT_ROOT = ROOT / "\u5370\u82b1\u56fe_\u900f\u660e\u5e95"
MOCKUP_ROOT = ROOT / "\u6279\u91cf\u8d34\u56fe\u7ed3\u679c"
PROMPT_ROOT = ROOT / "\u751f\u6210\u63d0\u793a\u8bcd"
TEMPLATE_DIR = ROOT / "\u8863\u7269\u5bf9\u5e94\u7684xlsx" / "\u7b80\u7ea6200"
TEMPLATE_XLSX = TEMPLATE_DIR / "test(9).xlsx"
PUTAWAY_DATA = Path("E:/1PythonProject/PutawayAiRobot/data")
PUTAWAY_PIC_DIR = PUTAWAY_DATA / "pic" / "1"

STORE_NAME = "YUHAOBO"
CATEGORY = "T\u6064"
HEADERS = ("\u5e97\u94fa\u540d\u79f0", "\u4ea7\u54c1\u5206\u7c7b", "\u4ea7\u54c1\u6807\u9898", "\u4ea7\u54c1\u5e8f\u5217\u53f7", "\u989c\u8272")

SELLING_POINTS = (
    "\u5706\u9886\u77ed\u8896 \u900f\u6c14\u5fae\u5f39\u9488\u7ec7\u4e0a\u8863 \u65e5\u5e38\u4f11\u95f2\u767e\u642d",
    "\u5706\u9886\u77ed\u8896 \u900f\u6c14\u8212\u9002\u9488\u7ec7\u4e0a\u8863 \u6237\u5916\u4f11\u95f2\u65e5\u5e38\u767e\u642d",
    "\u5706\u9886\u77ed\u8896 \u8f7b\u8584\u900f\u6c14\u9488\u7ec7\u4e0a\u8863 \u4f11\u95f2\u901a\u52e4\u65e5\u5e38\u767e\u642d",
    "\u5706\u9886\u77ed\u8896 \u67d4\u8f6f\u900f\u6c14\u9488\u7ec7\u4e0a\u8863 \u590f\u5b63\u65e5\u5e38\u767e\u642d",
)

TITLE_WORDS = [
    "\u5c0f\u5b57\u6bcd", "\u566a\u70b9\u5b57\u6807", "\u5f00\u653e\u7a7a\u6c14", "\u672c\u5730\u60c5\u7eea", "\u661f\u65b0\u4ff1\u4e50\u90e8",
    "\u590d\u53e4\u7f16\u53f7", "\u62c9\u529b\u5fbd\u7ae0", "\u8fd0\u52a8\u5b57\u53f7", "\u7530\u5f84\u5c0f\u6807", "\u4ff1\u4e50\u90e8\u5fbd\u7ae0",
    "\u7ec6\u7ebf\u82b1\u53f6", "\u82d4\u85d3\u53f6\u7247", "\u6839\u7cfb\u7ebf\u6761", "\u6d77\u6f6e\u690d\u7269", "\u8568\u53f6\u5c0f\u6807",
    "\u624b\u7ed8\u7231\u5fc3", "\u67d4\u548c\u7231\u5fc3", "\u5e78\u8fd0\u7b26\u53f7", "\u6162\u6162\u559c\u6b22", "\u8ff7\u4f60\u5fc3\u60c5",
    "\u6ce2\u6d6a\u6162\u8282\u594f", "\u51b7\u8c03\u6d6a\u7ebf", "\u5f00\u653e\u6d77\u98ce", "\u4f4e\u8c03\u566a\u70b9", "\u67d4\u8f6f\u7a7a\u6c14",
    "\u51e0\u4f55\u7ebf\u6846", "\u683c\u7ebf\u5c0f\u6807", "\u65b9\u6846\u6807\u7b7e", "\u7ebf\u6846\u5b57\u6807", "\u7b26\u53f7\u6807\u7b7e",
    "\u65e5\u5e38\u5c0f\u592a\u9633", "\u5149\u8292\u4ff1\u4e50\u90e8", "\u767d\u663c\u5149\u611f", "\u672c\u5730\u9633\u5149", "\u70ed\u611f\u5c0f\u6807",
    "\u50cf\u7d20\u4ee3\u7801", "\u540c\u6b65\u7535\u7801", "\u63a7\u5236\u6570\u5b57", "\u865a\u7a7a\u4ee3\u7801", "\u6a21\u5f0f\u6570\u5b57",
    "\u624b\u5199\u67d4\u548c", "\u7b80\u5355\u624b\u5199", "\u8f7b\u677e\u624b\u5199", "\u6f2b\u6b65\u5b57\u6807", "\u5b89\u9759\u5b57\u6807",
    "\u53f6\u7247\u7f16\u53f7", "\u82d4\u85d3\u7f16\u53f7", "\u53f6\u7247\u6570\u5b57", "\u8568\u53f6\u5c0f\u724c", "\u9999\u8349\u7f16\u53f7",
]


@dataclass(frozen=True)
class ProductRecord:
    sku: str
    title: str
    color: str
    output_path: Path


def sku_for(start: int, index: int) -> str:
    return f"BO-{start + index}"


def batch_name(start: int, count: int, batch_date: str | None) -> str:
    end = start + count - 1
    stamp = batch_date or date.today().isoformat()
    return f"\u53f3\u4e0a\u80f8\u5c0f\u6807\u5370\u82b1_BO-{start}-BO-{end}_{stamp}"


def safe_filename(text: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid or ord(char) < 32 else char for char in text)
    return re.sub(r"_+", "_", cleaned).strip(" ._")


def win_path(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def render_bo_prints(print_dir: Path, start: int, count: int) -> list[Path]:
    temp_dir = print_dir / "_style_source"
    source_paths = badge.render_prints(temp_dir, count)
    print_paths: list[Path] = []
    for index, source_path in enumerate(source_paths):
        sku = sku_for(start, index)
        output_path = print_dir / f"{sku}.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, output_path)
        print_paths.append(output_path)
        print(f"{sku}: print {output_path}")
    badge.make_overview(print_paths, print_dir / "_prints_overview.jpg", "BO right chest small badge prints")
    return print_paths


def shirt_color(model_path: Path) -> tuple[str, str]:
    if "\u767d" in model_path.stem:
        return "\u767d\u8272", "\u767d"
    if "\u9ed1" in model_path.stem:
        return "\u9ed1\u8272", "\u9ed1"
    img = ImageOps.exif_transpose(Image.open(model_path)).convert("RGB")
    w, h = img.size
    crop = img.crop((int(w * 0.32), int(h * 0.22), int(w * 0.68), int(h * 0.62)))
    arr = np.asarray(crop, dtype=np.float32)
    luma = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    return ("\u767d\u8272", "\u767d") if float(np.median(luma)) >= 150 else ("\u9ed1\u8272", "\u9ed1")


def title_for(color_word: str, title_word: str, index: int) -> str:
    suffix = SELLING_POINTS[index % len(SELLING_POINTS)]
    return f"\u590f\u5b63{color_word}\u7b80\u7ea6\u5c0f\u80f8\u6807{title_word}\u5370\u82b1T\u6064 {suffix}"


def make_mockups(print_paths: list[Path], mockup_dir: Path, start: int, seed: int) -> list[ProductRecord]:
    models = list_images(MODEL_DIR)
    if not models:
        raise FileNotFoundError(f"No model images found: {MODEL_DIR}")
    rng = random.Random(seed)
    mockup_dir.mkdir(parents=True, exist_ok=True)
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
    records: list[ProductRecord] = []
    for index, print_path in enumerate(print_paths):
        sku = sku_for(start, index)
        model_path = rng.choice(models)
        color_word, color_col = shirt_color(model_path)
        title = title_for(color_word, TITLE_WORDS[index], index)
        output_path = mockup_dir / safe_filename(f"{sku}_{title}.png")
        composite_one(model_path, print_path, output_path, placement)
        records.append(ProductRecord(sku, title, color_col, output_path))
        print(f"{sku}: product {output_path.name}")
    return records


def make_overview(paths: list[Path], output_path: Path) -> None:
    tile_w, tile_h = 230, 310
    cols = 10
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (235, 235, 235))
    for index, path in enumerate(paths):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        img.thumbnail((210, 245), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (tile_w, tile_h), "white")
        tile.paste(img, ((tile_w - img.width) // 2, 8))
        draw = ImageDraw.Draw(tile)
        draw.text((8, 260), path.stem[:30], fill=(0, 0, 0))
        sheet.paste(tile, ((index % cols) * tile_w, (index // cols) * tile_h))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=92)


def parse_product_rows(mockup_dir: Path) -> list[tuple[str, str, str, str, str]]:
    pattern = re.compile(r"^(BO-\d+)_(.+)\.png$", re.IGNORECASE)
    rows: list[tuple[str, str, str, str, str]] = []
    for path in list_images(mockup_dir):
        if path.name.startswith("_"):
            continue
        match = pattern.match(path.name)
        if not match:
            continue
        sku, title = match.groups()
        color = "\u767d" if "\u767d\u8272" in title else "\u9ed1" if "\u9ed1\u8272" in title else ""
        rows.append((STORE_NAME, CATEGORY, title, sku, color))
    rows.sort(key=lambda row: int(row[3].split("-")[1]))
    return rows


def build_sheet_xml(rows: list[tuple[str, str, str, str, str]]) -> str:
    def cell(ref: str, value: str, style: int | None = None) -> str:
        style_attr = "" if style is None else f' s="{style}"'
        return f'<c r="{ref}" t="inlineStr"{style_attr}><is><t>{escape(value)}</t></is></c>'

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


def write_xlsx_from_filenames(mockup_dir: Path, output_xlsx: Path, expected_count: int) -> None:
    rows_without_header = parse_product_rows(mockup_dir)
    if len(rows_without_header) != expected_count:
        raise RuntimeError(f"Expected {expected_count} product rows, got {len(rows_without_header)}")
    rows = [HEADERS]
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


def write_prompt_file(prompt_path: Path, start: int, count: int) -> None:
    end = start + count - 1
    lines = [
        f"\u53f3\u4e0a\u80f8\u5c0f\u6807\u5370\u82b1 BO-{start}-BO-{end}",
        "\u98ce\u683c\uff1a\u5c0f\u9762\u79ef\u80f8\u6807\u3001\u77ed\u5b57\u6bcd/\u7f16\u53f7\u3001\u7ec6\u7ebf\u690d\u7269\u3001\u6781\u7b80\u7b26\u53f7\u3001\u50cf\u7d20\u6807\u7b7e\u3002",
        "\u4f4d\u7f6e\uff1acenter_x=0.62, center_y=0.32, width=0.115, opacity=0.98, shadow_strength=0.16, wave_strength=0.003.",
        "",
    ]
    for index, title_word in enumerate(TITLE_WORDS[:count]):
        lines.append(f"{sku_for(start, index)}: {title_word}")
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def sync_putaway(mockup_dir: Path, output_xlsx: Path) -> None:
    expected = Path("E:/1PythonProject/PutawayAiRobot/data/pic/1").resolve()
    target = PUTAWAY_PIC_DIR.resolve()
    if target != expected:
        raise RuntimeError(f"Refusing to clear unexpected target: {target}")
    PUTAWAY_PIC_DIR.mkdir(parents=True, exist_ok=True)
    for path in PUTAWAY_PIC_DIR.iterdir():
        if path.is_file():
            path.unlink()
    for source in list_images(mockup_dir):
        if source.name.startswith("_"):
            continue
        shutil.copy2(source, PUTAWAY_PIC_DIR / source.name)
    PUTAWAY_DATA.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output_xlsx, PUTAWAY_DATA / output_xlsx.name)


def validate(start: int, count: int, print_dir: Path, mockup_dir: Path, output_xlsx: Path, check_putaway: bool) -> None:
    expected_skus = [sku_for(start, index) for index in range(count)]
    print_files = sorted(p for p in print_dir.glob("BO-*.png") if p.is_file())
    mockup_files = sorted(p for p in mockup_dir.glob("BO-*.png") if p.is_file())
    if [p.stem for p in print_files] != expected_skus:
        raise RuntimeError("Print SKU range mismatch")
    mockup_skus = sorted(path.name.split("_", 1)[0] for path in mockup_files)
    if mockup_skus != expected_skus:
        raise RuntimeError("Mockup SKU range mismatch")
    if len(print_files) != count or len(mockup_files) != count:
        raise RuntimeError(f"Expected {count}, got prints={len(print_files)} mockups={len(mockup_files)}")
    if not all(Image.open(path).mode in ("RGBA", "LA") or "transparency" in Image.open(path).info for path in print_files):
        raise RuntimeError("Not all print files have transparency")
    rows = parse_product_rows(mockup_dir)
    if len(rows) != count or rows[0][3] != expected_skus[0] or rows[-1][3] != expected_skus[-1]:
        raise RuntimeError("Parsed product rows mismatch")
    if not output_xlsx.exists():
        raise FileNotFoundError(output_xlsx)
    if check_putaway:
        putaway_files = sorted(p for p in PUTAWAY_PIC_DIR.glob("BO-*.png") if p.is_file())
        putaway_skus = sorted(path.name.split("_", 1)[0] for path in putaway_files)
        if len(putaway_files) != count or putaway_skus != expected_skus:
            raise RuntimeError("Putaway image sync mismatch")
        if not (PUTAWAY_DATA / output_xlsx.name).exists():
            raise FileNotFoundError(PUTAWAY_DATA / output_xlsx.name)


def run(start: int, count: int, seed: int, batch_date: str | None, sync: bool) -> tuple[Path, Path, Path, Path]:
    if count != 50:
        raise ValueError("This right-chest small badge batch currently expects count=50")
    name = batch_name(start, count, batch_date)
    print_dir = PRINT_ROOT / name
    mockup_dir = MOCKUP_ROOT / f"{name}_\u968f\u673a\u4e3b\u56fe{count}"
    prompt_path = PROMPT_ROOT / f"{name}.txt"
    output_xlsx = TEMPLATE_DIR / f"{name}.xlsx"
    write_prompt_file(prompt_path, start, count)
    print_paths = render_bo_prints(print_dir, start, count)
    records = make_mockups(print_paths, mockup_dir, start, seed)
    make_overview([record.output_path for record in records], mockup_dir / "_overview.jpg")
    write_xlsx_from_filenames(mockup_dir, output_xlsx, count)
    if sync:
        sync_putaway(mockup_dir, output_xlsx)
    validate(start, count, print_dir, mockup_dir, output_xlsx, sync)
    return print_dir, mockup_dir, prompt_path, output_xlsx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate BO right-chest small badge prints, products, xlsx, and putaway sync.")
    parser.add_argument("--start", type=int, default=756)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", type=int, default=2026061356)
    parser.add_argument("--date", default=None)
    parser.add_argument("--sync-putaway", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print_dir, mockup_dir, prompt_path, output_xlsx = run(args.start, args.count, args.seed, args.date, args.sync_putaway)
    print(f"Print dir: {print_dir}")
    print(f"Product dir: {mockup_dir}")
    print(f"Prompt file: {prompt_path}")
    print(f"XLSX: {output_xlsx}")
    if args.sync_putaway:
        print(f"Putaway synced: {PUTAWAY_PIC_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
