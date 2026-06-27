from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoodsListResult:
    total_count: int
    page_size: int
    selected: bool
    skc_ids: list[str]
    copied_to_clipboard: bool
    raw_skc_text: str = ""

    @property
    def skc_count(self) -> int:
        return len(self.skc_ids)


@dataclass(frozen=True)
class SpuIdentifierUploadResult:
    spu_ids: list[str]
    upload_file: str
    imported: bool

    @property
    def spu_count(self) -> int:
        return len(self.spu_ids)


@dataclass(frozen=True)
class InventorySettingUploadResult:
    sku_ids: list[str]
    upload_file: str
    saved: bool

    @property
    def sku_count(self) -> int:
        return len(self.sku_ids)
