from pathlib import Path

from consoleplat.adapters.sendgoods_adapter import SendGoodsAdapter
from consoleplat.services.monitor_service import MonitorSnapshot


def test_sendgoods_adapter_builds_export_command():
    adapter = SendGoodsAdapter(project_dir=Path("E:/1PythonProject/SendGoods"))

    program, args = adapter.export_command()

    assert program
    assert args == ["-m", "consoleplat.services.sendgoods_export_cli"]


def test_sendgoods_adapter_returns_export_dir_from_settings():
    adapter = SendGoodsAdapter()

    path = adapter.export_dir({"summary": {"output_path": "E:/exports/purchase/备货单.xlsx"}})

    assert str(path).replace("\\", "/") == "E:/exports/purchase"


def test_sendgoods_adapter_formats_finished_event():
    snapshot = MonitorSnapshot.empty(shop_name="YUHOOBO")
    payload = {
        "ok": True,
        "summary": {
            "output_path": "E:/1PythonProject/SendGoods/outputs/purchase.xlsx",
            "total_records": 22,
            "black_rows": 8,
            "white_rows": 4,
            "skipped_records": 1,
            "warnings": ["跳过无法识别颜色的数据：demo"],
        },
    }
    adapter = SendGoodsAdapter()

    updated = adapter.apply_export_result(snapshot, payload)

    assert updated.events[-1].level == "ok"
    assert "导出备货单完成" in updated.events[-1].message
    assert "22 条" in updated.events[-1].message
