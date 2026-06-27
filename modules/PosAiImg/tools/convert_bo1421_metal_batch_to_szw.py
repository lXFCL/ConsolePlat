from __future__ import annotations

import json
import re
import shutil
import zipfile
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from finalize_bo1421_generated_metal_batch import (
    IMAGE_EXTS,
    PUTAWAY_DATA_DIR,
    PUTAWAY_PIC_DIR,
    ROOT,
    make_overview,
    safe_filename,
)
from tshirt_print_tool import list_images


SOURCE_START = 1421
SOURCE_COUNT = 43
TARGET_START = 2875
STORE_NAME = "YUHOOBO"
STAMP = "2026-06-17"
SOURCE_DIR = ROOT / "批量贴图结果" / "爆款金属字印花_BO-1421-BO-1463_2026-06-17_中大图稍下43"
TARGET_BATCH = f"爆款金属字印花_SZW-{TARGET_START}-SZW-{TARGET_START + SOURCE_COUNT - 1}_{STAMP}_中大图稍下"
TARGET_DIR = ROOT / "批量贴图结果" / f"{TARGET_BATCH}43"
XLSX_DIR = ROOT / "衣物对应的xlsx" / "SZW"
XLSX_PATH = XLSX_DIR / f"{TARGET_BATCH}.xlsx"
TEMPLATE_DIRS = [ROOT / "衣物对应的xlsx" / "SZW", ROOT / "衣物对应的xlsx" / "简约200"]


def source_product_files() -> list[Path]:
    files = [p for p in list_images(SOURCE_DIR) if p.name.startswith("BO-")]
    files.sort(key=lambda p: int(re.match(r"BO-(\d+)_", p.name).group(1)))
    if len(files) != SOURCE_COUNT:
        raise RuntimeError(f"Expected {SOURCE_COUNT} BO products, got {len(files)} from {SOURCE_DIR}")
    expected = list(range(SOURCE_START, SOURCE_START + SOURCE_COUNT))
    got = serial_numbers(files, "BO")
    if got != expected:
        raise RuntimeError(f"Source BO range mismatch: {got[:3]} ... {got[-3:]}")
    return files


def serial_numbers(files: list[Path], prefix: str) -> list[int]:
    pattern = re.compile(rf"{re.escape(prefix)}-(\d+)", re.IGNORECASE)
    values: list[int] = []
    for path in files:
        match = pattern.search(path.name)
        if match:
            values.append(int(match.group(1)))
    return sorted(values)


def convert_products() -> list[Path]:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    pattern = re.compile(r"^BO-\d+_(.+)\.png$", re.IGNORECASE)
    for index, source in enumerate(source_product_files()):
        match = pattern.match(source.name)
        if not match:
            raise RuntimeError(f"Unexpected product filename: {source.name}")
        title = match.group(1)
        sku = f"SZW-{TARGET_START + index}"
        target = TARGET_DIR / safe_filename(f"{sku}_{title}.png")
        shutil.copy2(source, target)
        outputs.append(target)
    make_overview(outputs, TARGET_DIR / "_overview.jpg")
    return outputs


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


def rows_from_szw_filenames() -> list[tuple[str, str, str, str, str]]:
    pattern = re.compile(r"^(SZW-\d+)_(.+)\.png$", re.IGNORECASE)
    rows: list[tuple[str, str, str, str, str]] = []
    for path in list_images(TARGET_DIR):
        if path.name.startswith("_"):
            continue
        match = pattern.match(path.name)
        if not match:
            continue
        sku, title = match.groups()
        color = "白" if "白色" in title else "黑" if "黑色" in title else ""
        rows.append((STORE_NAME, "T恤", title, sku, color))
    return sorted(rows, key=lambda row: int(row[3].split("-")[1]))


def find_template() -> Path:
    templates: list[Path] = []
    for directory in TEMPLATE_DIRS:
        if directory.exists():
            templates.extend(p for p in directory.glob("*.xlsx") if not p.name.startswith("~$") and p != XLSX_PATH)
    if not templates:
        raise FileNotFoundError(f"No xlsx template found in {TEMPLATE_DIRS}")
    return sorted(templates, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def write_xlsx() -> None:
    rows = [("店铺名称", "产品分类", "产品标题", "产品序列号", "颜色"), *rows_from_szw_filenames()]
    if len(rows) != SOURCE_COUNT + 1:
        raise RuntimeError(f"Expected {SOURCE_COUNT + 1} xlsx rows including header, got {len(rows)}")
    XLSX_DIR.mkdir(parents=True, exist_ok=True)
    tmp = XLSX_PATH.with_suffix(".tmp.xlsx")
    shutil.copy2(find_template(), tmp)
    with zipfile.ZipFile(tmp, "r") as src, zipfile.ZipFile(XLSX_PATH, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = build_sheet_xml(rows) if info.filename == "xl/worksheets/sheet1.xml" else src.read(info.filename)
            dst.writestr(info, data)
    tmp.unlink(missing_ok=True)


def validate_local() -> dict:
    expected = list(range(TARGET_START, TARGET_START + SOURCE_COUNT))
    products = [p for p in list_images(TARGET_DIR) if p.name.startswith("SZW-")]
    rows = rows_from_szw_filenames()
    skus = serial_numbers(products, "SZW")
    summary = {
        "product_count": len(products),
        "product_skus": skus,
        "range_ok": skus == expected,
        "xlsx_exists": XLSX_PATH.exists(),
        "xlsx_rows_including_header": len(rows) + 1,
        "xlsx_first_sku": rows[0][3] if rows else "",
        "xlsx_last_sku": rows[-1][3] if rows else "",
        "store_names": sorted({row[0] for row in rows}),
        "overview_exists": (TARGET_DIR / "_overview.jpg").exists(),
    }
    if len(products) != SOURCE_COUNT or skus != expected:
        raise RuntimeError(f"Product validation failed: {summary}")
    if not XLSX_PATH.exists() or len(rows) != SOURCE_COUNT or summary["store_names"] != [STORE_NAME]:
        raise RuntimeError(f"XLSX validation failed: {summary}")
    return summary


def sync_putaway() -> None:
    PUTAWAY_PIC_DIR.mkdir(parents=True, exist_ok=True)
    for path in PUTAWAY_PIC_DIR.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            path.unlink()
    for path in list_images(TARGET_DIR):
        if path.name.startswith("SZW-"):
            shutil.copy2(path, PUTAWAY_PIC_DIR / path.name)
    PUTAWAY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(XLSX_PATH, PUTAWAY_DATA_DIR / XLSX_PATH.name)


def validate_putaway() -> dict:
    expected = list(range(TARGET_START, TARGET_START + SOURCE_COUNT))
    files = [p for p in list_images(PUTAWAY_PIC_DIR) if p.name.startswith("SZW-")]
    skus = serial_numbers(files, "SZW")
    summary = {
        "putaway_pic_count": len(files),
        "putaway_skus": skus,
        "putaway_range_ok": skus == expected,
        "putaway_xlsx_exists": (PUTAWAY_DATA_DIR / XLSX_PATH.name).exists(),
    }
    if len(files) != SOURCE_COUNT or skus != expected or not summary["putaway_xlsx_exists"]:
        raise RuntimeError(f"Putaway validation failed: {summary}")
    return summary


def main() -> int:
    products = convert_products()
    write_xlsx()
    local = validate_local()
    sync_putaway()
    putaway = validate_putaway()
    print(json.dumps({
        "target_dir": str(TARGET_DIR),
        "xlsx": str(XLSX_PATH),
        "product_count": len(products),
        "local": local,
        "putaway": putaway,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
