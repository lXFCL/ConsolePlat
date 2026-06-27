from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from tshirt_print_tool import list_images


ROOT = Path(__file__).resolve().parents[1]
START = 906
COUNT = 50
END = START + COUNT - 1
BATCH = f"日系复古自然印花_BO-{START}-BO-{END}_2026-06-14"
PRINT_DIR = ROOT / "印花图_透明底" / BATCH
MOCKUP_DIR = ROOT / "批量贴图结果" / f"{BATCH}_随机主图50"
XLSX = ROOT / "衣物对应的xlsx" / "简约200" / f"{BATCH}.xlsx"
PUTAWAY_DATA = Path(r"E:\1PythonProject\PutawayAiRobot\data")
PUTAWAY_PIC = PUTAWAY_DATA / "pic" / "1"


def sku_numbers(paths: list[Path]) -> list[int]:
    values: list[int] = []
    for path in paths:
        match = re.search(r"BO-(\d+)", path.name)
        if match:
            values.append(int(match.group(1)))
    return sorted(values)


def xlsx_rows(path: Path) -> list[list[str]]:
    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("xl/worksheets/sheet1.xml")
    root = ET.fromstring(xml)
    rows: list[list[str]] = []
    for row in root.findall(".//main:sheetData/main:row", ns):
        rows.append(["".join(cell.itertext()) for cell in row.findall("main:c", ns)])
    return rows


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    expected = list(range(START, END + 1))
    print_files = sorted(p for p in list_images(PRINT_DIR) if re.fullmatch(r"BO-\d+\.png", p.name))
    mockup_files = sorted(p for p in list_images(MOCKUP_DIR) if not p.name.startswith("_"))
    putaway_files = sorted(p for p in list_images(PUTAWAY_PIC) if not p.name.startswith("_"))
    rows = xlsx_rows(XLSX)
    header = rows[0]

    require(len(print_files) == COUNT, f"print count {len(print_files)}")
    require(len(mockup_files) == COUNT, f"mockup count {len(mockup_files)}")
    require(len(putaway_files) == COUNT, f"putaway count {len(putaway_files)}")
    require(sku_numbers(print_files) == expected, "print SKU range mismatch")
    require(sku_numbers(mockup_files) == expected, "mockup SKU range mismatch")
    require(sku_numbers(putaway_files) == expected, "putaway SKU range mismatch")
    require(XLSX.exists(), f"xlsx missing: {XLSX}")
    require((PUTAWAY_DATA / XLSX.name).exists(), "putaway xlsx missing")
    require(header == ["店铺名称", "产品分类", "产品标题", "产品序列号", "颜色"], f"bad header: {header}")
    require(len(rows) == COUNT + 1, f"xlsx rows {len(rows)}")
    require(rows[1][3] == f"BO-{START}", f"first sku {rows[1][3]}")
    require(rows[-1][3] == f"BO-{END}", f"last sku {rows[-1][3]}")
    require(all(row[2] in next(p.stem for p in mockup_files if row[3] in p.name) for row in rows[1:]), "title mismatch")

    print(f"prints={len(print_files)} products={len(mockup_files)} putaway={len(putaway_files)}")
    print(f"range=BO-{START}-BO-{END}")
    print(f"xlsx_rows={len(rows)} header={','.join(header)}")
    print(f"xlsx_first={rows[1][3]} xlsx_last={rows[-1][3]}")
    print(f"putaway_xlsx={(PUTAWAY_DATA / XLSX.name)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
