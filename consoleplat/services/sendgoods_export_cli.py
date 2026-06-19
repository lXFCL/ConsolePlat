from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from consoleplat.config import SettingsStore


SENDGOODS_DIR = Path("E:/1PythonProject/SendGoods")


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

    from excel_writer import write_purchase_sheet
    from temu_reader import TemuReader

    settings = SettingsStore().load()
    output_dir = Path(settings.purchase_export_dir or SENDGOODS_DIR / "outputs")
    image_dir = SENDGOODS_DIR / "downloads" / "images"
    output_path = output_dir / f"备货单_{settings.active_shop}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    logs: list[str] = []
    reader = TemuReader(
        user_data_dir=SENDGOODS_DIR / ".browser-profile",
        cdp_endpoint=settings.cdp_endpoint,
        logger=logs.append,
    )
    records = reader.collect()
    summary = write_purchase_sheet(
        records,
        SENDGOODS_DIR / "1.cleaned.xlsx",
        output_path,
        image_dir,
        logger=logs.append,
    )
    return {
        "output_path": summary.output_path,
        "total_records": summary.total_records,
        "black_rows": summary.black_rows,
        "white_rows": summary.white_rows,
        "skipped_records": summary.skipped_records,
        "warnings": summary.warnings,
        "logs": logs[-20:],
    }


def _write(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.flush()


if __name__ == "__main__":
    raise SystemExit(main())
