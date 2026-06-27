from __future__ import annotations

import re
import shutil
import zipfile
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from tshirt_print_tool import list_images


ROOT = Path(__file__).resolve().parents[1]
SKU = "BO-827"
START = 806
END = 855
BATCH = "高街黑白灰金属素描印花_BO-806-BO-855_2026-06-13"
MOCKUP_DIR = ROOT / "批量贴图结果" / f"{BATCH}_随机主图50"
XLSX = ROOT / "衣物对应的xlsx" / "简约200" / f"{BATCH}.xlsx"
TEMPLATE_XLSX = ROOT / "衣物对应的xlsx" / "简约200" / "test(9).xlsx"
PROGRESS_FILE = ROOT / "BO_PROGRESS.md"
PUTAWAY_DATA = Path(r"E:\1PythonProject\PutawayAiRobot\data")
PUTAWAY_PIC = PUTAWAY_DATA / "pic" / "1"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def safe_move_removed(path: Path) -> Path:
    removed_dir = path.parent / "_removed"
    removed_dir.mkdir(parents=True, exist_ok=True)
    target = removed_dir / path.name
    if target.exists():
        target = removed_dir / f"{path.stem}_{date.today().isoformat()}{path.suffix}"
    shutil.move(str(path), str(target))
    return target


def rows_from_mockup_filenames(mockup_dir: Path) -> list[tuple[str, str, str, str, str]]:
    pattern = re.compile(r"^(BO-\d+)_(.+)\.png$", re.IGNORECASE)
    rows: list[tuple[str, str, str, str, str]] = []
    for path in list_images(mockup_dir):
        if path.name.startswith("_") or SKU in path.name:
            continue
        match = pattern.match(path.name)
        if not match:
            continue
        sku, title = match.groups()
        color = "白" if "白色" in title else "黑" if "黑色" in title else ""
        rows.append(("YUHAOBO", "T恤", title, sku, color))
    rows.sort(key=lambda row: int(row[3].split("-")[1]))
    return rows


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


def write_xlsx(rows_without_header: list[tuple[str, str, str, str, str]]) -> None:
    rows = [("店铺名称", "产品分类", "产品标题", "产品序列号", "颜色")]
    rows.extend(rows_without_header)
    backup = XLSX.with_suffix(f".before_remove_{SKU}.xlsx")
    if XLSX.exists() and not backup.exists():
        shutil.copy2(XLSX, backup)
    tmp_path = XLSX.with_suffix(".tmp.xlsx")
    shutil.copy2(TEMPLATE_XLSX, tmp_path)
    with zipfile.ZipFile(tmp_path, "r") as src, zipfile.ZipFile(XLSX, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            if info.filename == "xl/worksheets/sheet1.xml":
                dst.writestr(info, build_sheet_xml(rows))
            else:
                dst.writestr(info, src.read(info.filename))
    tmp_path.unlink(missing_ok=True)


def sync_putaway() -> None:
    PUTAWAY_PIC.mkdir(parents=True, exist_ok=True)
    for path in PUTAWAY_PIC.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            path.unlink()
    for path in list_images(MOCKUP_DIR):
        if path.name.startswith("_") or SKU in path.name:
            continue
        shutil.copy2(path, PUTAWAY_PIC / path.name)
    PUTAWAY_DATA.mkdir(parents=True, exist_ok=True)
    shutil.copy2(XLSX, PUTAWAY_DATA / XLSX.name)


def sku_set(paths: list[Path]) -> set[str]:
    values = set()
    for path in paths:
        match = re.search(r"BO-\d+", path.name)
        if match:
            values.add(match.group(0))
    return values


def update_progress(remaining_count: int, moved: list[Path]) -> None:
    try:
        text = PROGRESS_FILE.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = PROGRESS_FILE.read_text(encoding="gbk", errors="replace")
    addition = (
        f"\n- {date.today().isoformat()} 按用户要求删除 {SKU} 产品图并同步投放数据；原因：该图案含人的元素（骷髅戒）。"
        f" 当前产品图和投放目录均为 {remaining_count} 张，不含 {SKU}；xlsx 已重写为含表头 {remaining_count + 1} 行。"
        f" 本次只移除产品/投放数据，货号分配进度仍保持到 BO-{END}，下次建议仍从 BO-{END + 1}。\n"
    )
    if moved:
        addition += f"- {SKU} 原产品图已移至 `{moved[0].parent}` 以便追溯。\n"
    marker = "## 后续规则"
    if marker in text:
        text = text.replace(marker, addition + "\n" + marker, 1)
    else:
        text += addition
    PROGRESS_FILE.write_text(text, encoding="utf-8")


def main() -> int:
    moved: list[Path] = []
    for path in list(MOCKUP_DIR.glob(f"*{SKU}*.png")):
        moved.append(safe_move_removed(path))
    for path in list(PUTAWAY_PIC.glob(f"*{SKU}*.png")):
        path.unlink()

    rows = rows_from_mockup_filenames(MOCKUP_DIR)
    if len(rows) != 49:
        raise RuntimeError(f"Expected 49 rows after removing {SKU}, got {len(rows)}")
    if any(row[3] == SKU for row in rows):
        raise RuntimeError(f"{SKU} still present in rows")
    write_xlsx(rows)
    sync_putaway()

    products = [p for p in list_images(MOCKUP_DIR) if not p.name.startswith("_") and SKU not in p.name]
    putaway = [p for p in list_images(PUTAWAY_PIC) if not p.name.startswith("_")]
    if len(products) != 49 or len(putaway) != 49:
        raise RuntimeError(f"Count mismatch: products={len(products)} putaway={len(putaway)}")
    if SKU in sku_set(products) or SKU in sku_set(putaway):
        raise RuntimeError(f"{SKU} still present after sync")
    update_progress(49, moved)
    print(f"removed={len(moved)}")
    print(f"products=49 putaway=49 xlsx={XLSX}")
    print(f"removed_dir={moved[0].parent if moved else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
