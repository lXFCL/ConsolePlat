from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from consoleplat.config import SettingsStore
from consoleplat.config import resolve_project_dir
from consoleplat.paths import default_prints_dir, default_runtime_dir
from consoleplat.services.print_gallery_service import collect_print_gallery


SENDGOODS_DIR = resolve_project_dir("sendgoods") or Path(__file__).resolve().parents[2] / "modules" / "SendGoods"


def main() -> int:
    try:
        summary = export_purchase_sheet()
        _write({"ok": True, "summary": summary})
        return 0
    except Exception as exc:  # noqa: BLE001 - surface worker failure to UI.
        _write({"ok": False, "message": f"{type(exc).__name__}: {exc}"})
        return 1


def export_purchase_sheet() -> dict:
    if not SENDGOODS_DIR.exists():
        raise RuntimeError(f"未找到 SendGoods 项目：{SENDGOODS_DIR}")
    sys.path.insert(0, str(SENDGOODS_DIR))
    for module_name in ("models", "excel_writer", "temu_reader"):
        module = sys.modules.get(module_name)
        module_path = Path(str(getattr(module, "__file__", "") or "")) if module is not None else None
        if module_path is not None and SENDGOODS_DIR not in module_path.parents:
            sys.modules.pop(module_name, None)

    from excel_writer import write_purchase_sheet
    from temu_reader import TemuReader

    settings = SettingsStore().load()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_root = Path(settings.purchase_export_dir or default_runtime_dir("outputs") / "purchase")
    batch_dir = output_root / timestamp
    xlsx_dir = batch_dir / "xlsx"
    print_gallery_dir = batch_dir / "印花图集"
    image_dir = SENDGOODS_DIR / "downloads" / "images"
    output_path = xlsx_dir / f"备货单_{settings.active_shop}_{timestamp}.xlsx"

    logs: list[str] = []
    reader = TemuReader(
        user_data_dir=SENDGOODS_DIR / ".browser-profile",
        cdp_endpoint=settings.cdp_endpoint,
        logger=logs.append,
    )
    records = reader.collect()
    product_skus = sorted({str(record.product_sku or "").strip() for record in records if str(record.product_sku or "").strip()})
    local_gallery_dir = _resolve_print_gallery_local_dir(settings)
    print_summary = collect_print_gallery(
        skus=product_skus,
        source=settings.print_gallery_source,
        local_dir=local_gallery_dir,
        github_raw_base_url=settings.print_gallery_github_raw_base_url,
        target_dir=print_gallery_dir,
    )
    summary = write_purchase_sheet(
        records,
        SENDGOODS_DIR / "1.cleaned.xlsx",
        output_path,
        image_dir,
        logger=logs.append,
    )
    return {
        "batch_dir": str(batch_dir),
        "xlsx_dir": str(xlsx_dir),
        "output_path": summary.output_path,
        "print_gallery_dir": str(print_gallery_dir),
        "print_gallery_copied": print_summary.copied,
        "missing_print_skus": print_summary.missing_skus,
        "print_gallery_warnings": print_summary.warnings,
        "total_records": summary.total_records,
        "black_rows": summary.black_rows,
        "white_rows": summary.white_rows,
        "skipped_records": summary.skipped_records,
        "warnings": summary.warnings,
        "logs": logs[-20:],
    }


def _resolve_print_gallery_local_dir(settings) -> Path:
    configured = str(getattr(settings, "print_gallery_local_dir", "") or "").strip()
    if configured:
        return Path(configured)
    if str(getattr(settings, "posai_gallery_root", "") or "").strip():
        return Path(settings.posai_gallery_root)
    posai_dir = resolve_project_dir("posaiimg")
    if posai_dir:
        return posai_dir / "图库"
    return default_prints_dir()


def _write(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.flush()


if __name__ == "__main__":
    raise SystemExit(main())
