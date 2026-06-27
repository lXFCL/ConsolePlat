from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from tshirt_print_tool import list_images


ROOT = Path(__file__).resolve().parents[1]
SKU = "BO-827"
BATCH = "高街黑白灰金属素描印花_BO-806-BO-855_2026-06-13"
MOCKUP_DIR = ROOT / "批量贴图结果" / f"{BATCH}_随机主图50"
XLSX = ROOT / "衣物对应的xlsx" / "简约200" / f"{BATCH}.xlsx"
PUTAWAY_DATA = Path(r"E:\1PythonProject\PutawayAiRobot\data")
PUTAWAY_PIC = PUTAWAY_DATA / "pic" / "1"


def sku_values(paths: list[Path]) -> list[str]:
    values = []
    for path in paths:
        match = re.search(r"BO-\d+", path.name)
        if match:
            values.append(match.group(0))
    return sorted(values, key=lambda x: int(x.split("-")[1]))


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
    products = [p for p in list_images(MOCKUP_DIR) if not p.name.startswith("_")]
    putaway = [p for p in list_images(PUTAWAY_PIC) if not p.name.startswith("_")]
    product_skus = sku_values(products)
    putaway_skus = sku_values(putaway)
    rows = xlsx_rows(XLSX)
    row_skus = [row[3] for row in rows[1:]]
    header = rows[0]

    require(len(products) == 49, f"product count {len(products)}")
    require(len(putaway) == 49, f"putaway count {len(putaway)}")
    require(len(rows) == 50, f"xlsx rows {len(rows)}")
    require(SKU not in product_skus, "BO-827 still in products")
    require(SKU not in putaway_skus, "BO-827 still in putaway")
    require(SKU not in row_skus, "BO-827 still in xlsx")
    require(product_skus == putaway_skus == row_skus, "products/putaway/xlsx SKU mismatch")
    require(header == ["店铺名称", "产品分类", "产品标题", "产品序列号", "颜色"], f"bad header {header}")
    require((MOCKUP_DIR / "_removed").exists(), "removed backup dir missing")
    require((PUTAWAY_DATA / XLSX.name).exists(), "putaway xlsx missing")

    print(f"products={len(products)} putaway={len(putaway)} xlsx_rows={len(rows)}")
    print(f"removed_sku={SKU}")
    print(f"first={row_skus[0]} last={row_skus[-1]}")
    print(f"header={','.join(header)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
