from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from consoleplat.config import SettingsStore
from consoleplat.config import resolve_project_dir
from consoleplat.paths import default_runtime_dir, modules_root
from consoleplat.services.monitor_service import MonitorEvent, MonitorSnapshot


@dataclass(frozen=True)
class SendGoodsAdapter:
    project_dir: Path = resolve_project_dir("sendgoods") or modules_root() / "SendGoods"

    def export_command(self) -> tuple[str, list[str]]:
        return sys.executable, ["-m", "consoleplat.services.sendgoods_export_cli"]

    def export_dir(self, payload: dict[str, Any] | None = None) -> Path:
        summary = (payload or {}).get("summary") or {}
        batch_dir = str(summary.get("batch_dir") or "")
        if batch_dir:
            return Path(batch_dir)
        output_path = str(summary.get("output_path") or "")
        if output_path:
            return Path(output_path).parent
        settings = SettingsStore().load()
        return Path(settings.purchase_export_dir or default_runtime_dir("outputs") / "purchase")

    def apply_export_result(self, snapshot: MonitorSnapshot, payload: dict[str, Any]) -> MonitorSnapshot:
        if not payload.get("ok"):
            message = str(payload.get("message") or "导出备货单失败")
            level = "warn"
        else:
            summary = payload.get("summary") or {}
            total = int(summary.get("total_records") or 0)
            output_path = str(summary.get("output_path") or "")
            skipped = int(summary.get("skipped_records") or 0)
            print_copied = int(summary.get("print_gallery_copied") or 0)
            missing_prints = len(summary.get("missing_print_skus") or [])
            message = (
                f"导出备货单完成：{total} 条，跳过 {skipped} 条，"
                f"印花 {print_copied} 张，缺失 {missing_prints} 个货号，文件 {output_path}"
            )
            level = "ok"
        event = MonitorEvent(datetime.now().strftime("%H:%M:%S"), level, message)
        return MonitorSnapshot(
            shop_name=snapshot.shop_name,
            region=snapshot.region,
            fetched_at=snapshot.fetched_at,
            refresh_interval_seconds=snapshot.refresh_interval_seconds,
            metrics=snapshot.metrics,
            orders=snapshot.orders,
            events=(*snapshot.events[-5:], event),
            source_status=snapshot.source_status,
        )
