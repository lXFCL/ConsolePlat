from __future__ import annotations

import json
import re
import shutil
import zipfile
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image

from finalize_bo1421_generated_metal_batch import (
    IMAGE_EXTS,
    KEYWORDS,
    MODEL_DIR,
    PROGRESS_FILE,
    PUTAWAY_DATA_DIR,
    PUTAWAY_PIC_DIR,
    ROOT,
    SELLING_POINTS,
    START,
    alpha_luma,
    choose_model,
    make_overview,
    product_title,
    rows_from_product_filenames,
    safe_filename,
    shirt_color,
    sku_numbers,
)
from tshirt_print_tool import Placement, composite_one, list_images


COUNT = 43
STAMP = "2026-06-17"
BATCH_NAME = f"爆款金属字印花_BO-{START}-BO-{START + COUNT - 1}_{STAMP}"
PRINT_DIR = ROOT / "印花图_透明底" / BATCH_NAME
MOCKUP_DIR = ROOT / "批量贴图结果" / f"{BATCH_NAME}_中大图稍下43"
XLSX_PATH = ROOT / "衣物对应的xlsx" / "简约200" / f"{BATCH_NAME}_中大图稍下.xlsx"
TEMPLATE_DIR = ROOT / "衣物对应的xlsx" / "简约200"


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


def make_products() -> list[Path]:
    print_files = sorted(p for p in list_images(PRINT_DIR) if re.fullmatch(r"BO-\d+\.png", p.name, re.IGNORECASE))
    if len(print_files) != COUNT:
        raise RuntimeError(f"Expected {COUNT} print files in {PRINT_DIR}, got {len(print_files)}")
    MOCKUP_DIR.mkdir(parents=True, exist_ok=True)
    placement = Placement(
        center_x=0.50,
        center_y=0.38,
        width=0.44,
        opacity=0.96,
        rotation=0.0,
        shadow_strength=0.28,
        wave_strength=0.006,
        remove_white_bg=False,
    )
    outputs: list[Path] = []
    for idx, print_path in enumerate(print_files):
        keyword = KEYWORDS[idx % len(KEYWORDS)]
        model = choose_model(alpha_luma(print_path), idx)
        color_word, _ = shirt_color(model)
        title = product_title(color_word, keyword)
        output = MOCKUP_DIR / safe_filename(f"BO-{START + idx}_{title}.png")
        composite_one(model, print_path, output, placement)
        outputs.append(output)
    make_overview(outputs, MOCKUP_DIR / "_overview.jpg")
    return outputs


def validate_outputs() -> dict:
    expected = list(range(START, START + COUNT))
    product_files = sorted(p for p in list_images(MOCKUP_DIR) if not p.name.startswith("_"))
    rows = rows_from_product_filenames(MOCKUP_DIR)
    summary = {
        "print_count": len([p for p in list_images(PRINT_DIR) if re.fullmatch(r"BO-\d+\.png", p.name, re.IGNORECASE)]),
        "product_count": len(product_files),
        "product_skus": sku_numbers(product_files),
        "xlsx_exists": XLSX_PATH.exists(),
        "xlsx_rows_including_header": len(rows) + 1,
        "xlsx_first_sku": rows[0][3] if rows else "",
        "xlsx_last_sku": rows[-1][3] if rows else "",
        "overview_exists": (MOCKUP_DIR / "_overview.jpg").exists(),
    }
    if summary["print_count"] != COUNT or summary["product_count"] != COUNT:
        raise RuntimeError(f"Count validation failed: {summary}")
    if summary["product_skus"] != expected:
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
    skus = sku_numbers(files)
    summary = {
        "putaway_pic_count": len(files),
        "putaway_skus": skus,
        "putaway_range_ok": skus == expected,
        "putaway_xlsx_exists": (PUTAWAY_DATA_DIR / XLSX_PATH.name).exists(),
    }
    if len(files) != COUNT or skus != expected or not summary["putaway_xlsx_exists"]:
        raise RuntimeError(f"Putaway validation failed: {summary}")
    return summary


def update_progress(validation: dict, putaway: dict) -> None:
    text = PROGRESS_FILE.read_text(encoding="utf-8")
    today = date.today().isoformat()
    text = re.sub(r"更新时间[：:]\s*.*", f"更新时间：{today}", text)
    text = re.sub(r"上次已分配到[：:]\s*BO-\d+", "上次已分配到：BO-1463", text)
    text = re.sub(r"下次建议从[：:]\s*BO-\d+", "下次建议从：BO-1464", text)
    addition = (
        f"\n- {today} 根据用户反馈“整体位置往下调一些，大小小一点”，已再次重贴 BO-1421 到 BO-1463 爆款金属字批次；未重新生成印花。\n"
        f"- 新产品图目录：`{MOCKUP_DIR}`，当前校验为 {validation['product_count']} 张，范围 BO-1421 到 BO-1463，无缺号；贴图参数为 center_x=0.50、center_y=0.38、width=0.44。\n"
        f"- 新 xlsx：`{XLSX_PATH}`，当前校验为 44 行，表头为 店铺名称、产品分类、产品标题、产品序列号、颜色，首条 BO-1421，末条 BO-1463。\n"
        f"- 已重新同步到 `{PUTAWAY_PIC_DIR}`，目标目录校验为 {putaway['putaway_pic_count']} 张，范围 BO-1421 到 BO-1463，无缺号；xlsx 已复制到 `{PUTAWAY_DATA_DIR}`。\n"
        f"- 视觉抽查：已生成新版 `_overview.jpg`，用于确认大图上胸位置是否满足要求。\n"
    )
    marker = "## 后续规则"
    if marker in text:
        text = text.replace(marker, addition + "\n" + marker, 1)
    else:
        text += addition
    PROGRESS_FILE.write_text(text, encoding="utf-8")


def main() -> int:
    outputs = make_products()
    write_xlsx(MOCKUP_DIR, XLSX_PATH, COUNT)
    validation = validate_outputs()
    sync_putaway()
    putaway = validate_putaway()
    update_progress(validation, putaway)
    print(json.dumps({
        "mockup_dir": str(MOCKUP_DIR),
        "xlsx": str(XLSX_PATH),
        "product_count": len(outputs),
        "placement": {
            "center_x": 0.50,
            "center_y": 0.38,
            "width": 0.44,
        },
        "validation": validation,
        "putaway": putaway,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
