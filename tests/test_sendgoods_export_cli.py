from dataclasses import dataclass
from pathlib import Path

from consoleplat.config import AppSettings, SettingsStore
from consoleplat.services import sendgoods_export_cli


def test_sendgoods_export_creates_timestamp_batch_dirs_and_collects_prints(tmp_path, monkeypatch):
    sendgoods_dir = tmp_path / "SendGoods"
    sendgoods_dir.mkdir()
    (sendgoods_dir / "1.cleaned.xlsx").write_bytes(b"template")
    (sendgoods_dir / "temu_reader.py").write_text(
        """
from models import TemuSkuRecord

class TemuReader:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def collect(self):
        return [
            TemuSkuRecord(product_sku='BO-1616', color='黑色', size='M', quantity=1),
            TemuSkuRecord(product_sku='BO-1616', color='白色', size='L', quantity=2),
            TemuSkuRecord(product_sku='BO-9999', color='黑色', size='XL', quantity=1),
        ]
""",
        encoding="utf-8",
    )
    (sendgoods_dir / "excel_writer.py").write_text(
        """
from dataclasses import dataclass

@dataclass
class Summary:
    output_path: str
    total_records: int
    black_rows: int
    white_rows: int
    skipped_records: int
    warnings: list

def write_purchase_sheet(records, template_path, output_path, image_dir, logger=None):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b'xlsx')
    return Summary(str(output_path), len(list(records)), 1, 1, 0, [])
""",
        encoding="utf-8",
    )
    (sendgoods_dir / "models.py").write_text(
        """
from dataclasses import dataclass

@dataclass(frozen=True)
class TemuSkuRecord:
    product_sku: str = ''
    color: str = ''
    size: str = ''
    quantity: int = 0
""",
        encoding="utf-8",
    )

    gallery = tmp_path / "gallery"
    gallery.mkdir()
    (gallery / "BO-1616.png").write_bytes(b"print")
    settings_path = tmp_path / "settings.json"
    SettingsStore(settings_path).save(
        AppSettings(
            active_shop="YUHOOBO",
            purchase_export_dir=str(tmp_path / "exports"),
            print_gallery_source="local",
            print_gallery_local_dir=str(gallery),
        )
    )

    class FixedDateTime:
        @classmethod
        def now(cls):
            return cls()

        def strftime(self, _fmt):
            return "20260627_103000"

    monkeypatch.setattr(sendgoods_export_cli, "SENDGOODS_DIR", sendgoods_dir)
    monkeypatch.setattr(sendgoods_export_cli, "SettingsStore", lambda: SettingsStore(settings_path))
    monkeypatch.setattr(sendgoods_export_cli, "datetime", FixedDateTime)
    monkeypatch.syspath_prepend(str(sendgoods_dir))

    summary = sendgoods_export_cli.export_purchase_sheet()

    assert summary["batch_dir"].replace("\\", "/").endswith("/exports/20260627_103000")
    assert summary["xlsx_dir"].replace("\\", "/").endswith("/exports/20260627_103000/xlsx")
    assert summary["print_gallery_dir"].replace("\\", "/").endswith("/exports/20260627_103000/印花图集")
    assert Path(summary["output_path"]).name == "备货单_YUHOOBO_20260627_103000.xlsx"
    assert Path(summary["output_path"]).exists()
    assert (Path(summary["print_gallery_dir"]) / "BO-1616.png").read_bytes() == b"print"
    assert summary["print_gallery_copied"] == 1
    assert summary["missing_print_skus"] == ["BO-9999"]
