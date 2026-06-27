from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TemuSkuRecord:
    beihuo_order: str = ""
    parent_order: str = ""
    product_sku: str = ""
    sku_code: str = ""
    sku_id: str = ""
    color: str = ""
    size: str = ""
    quantity: int = 0
    image_url: str = ""
    sku_attr: str = ""

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.beihuo_order, self.product_sku, self.sku_code, self.sku_id)


@dataclass
class WriteSummary:
    output_path: str
    total_records: int
    black_rows: int
    white_rows: int
    skipped_records: int
    warnings: list[str]
