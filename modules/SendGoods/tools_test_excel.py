from __future__ import annotations

from datetime import datetime
from pathlib import Path

from excel_writer import write_purchase_sheet
from sample_data import SAMPLE_RECORDS


ROOT = Path(__file__).resolve().parent


def main() -> None:
    output = ROOT / "outputs" / f"sample_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    summary = write_purchase_sheet(
        SAMPLE_RECORDS,
        template_path=ROOT / "1.cleaned.xlsx",
        output_path=output,
        image_dir=ROOT / "downloads" / "images",
        logger=print,
    )
    print(f"生成完成：{summary.output_path}")
    print(f"黑色行数：{summary.black_rows}，白色行数：{summary.white_rows}，跳过：{summary.skipped_records}")
    for warning in summary.warnings:
        print(f"警告：{warning}")


if __name__ == "__main__":
    main()
