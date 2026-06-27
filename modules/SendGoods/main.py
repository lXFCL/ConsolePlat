from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app_paths import resource_path, runtime_root
from excel_writer import write_purchase_sheet
from models import TemuSkuRecord
from temu_reader import TARGET_URL, TemuReader


ROOT = runtime_root()
TEMPLATE_PATH = resource_path("1.cleaned.xlsx")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SendGoods 拿货表生成工具")
        self.resize(1180, 760)
        self.reader = TemuReader(user_data_dir=ROOT / ".browser-profile", logger=self.log)
        self.records: list[TemuSkuRecord] = []

        self.template_edit = QLineEdit(str(TEMPLATE_PATH))
        self.output_edit = QLineEdit(str(ROOT / "outputs" / self.default_output_name()))
        self.cdp_edit = QLineEdit("http://127.0.0.1:9222")
        self.scroll_spin = QSpinBox()
        self.scroll_spin.setRange(1, 300)
        self.scroll_spin.setValue(80)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["颜色", "货号", "尺码", "件数", "SKU货号", "备货单号", "母单号", "图片"])
        self.table.horizontalHeader().setStretchLastSection(True)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumBlockCount(1000)

        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)

        form = QGridLayout()
        form.addWidget(QLabel("模板文件"), 0, 0)
        form.addWidget(self.template_edit, 0, 1)
        browse_template = QPushButton("选择")
        browse_template.clicked.connect(self.choose_template)
        form.addWidget(browse_template, 0, 2)

        form.addWidget(QLabel("输出文件"), 1, 0)
        form.addWidget(self.output_edit, 1, 1)
        browse_output = QPushButton("选择")
        browse_output.clicked.connect(self.choose_output)
        form.addWidget(browse_output, 1, 2)

        form.addWidget(QLabel("Chrome调试地址"), 2, 0)
        form.addWidget(self.cdp_edit, 2, 1)
        form.addWidget(QLabel("最大滚动次数"), 2, 2)
        form.addWidget(self.scroll_spin, 2, 3)
        root.addLayout(form)

        buttons = QHBoxLayout()
        open_btn = QPushButton("打开/连接浏览器")
        open_btn.clicked.connect(self.open_browser)
        collect_btn = QPushButton("采集当前页")
        collect_btn.clicked.connect(self.collect_records)
        export_btn = QPushButton("生成 Excel")
        export_btn.clicked.connect(self.export_excel)
        csv_btn = QPushButton("导出CSV预览")
        csv_btn.clicked.connect(self.export_csv)
        buttons.addWidget(open_btn)
        buttons.addWidget(collect_btn)
        buttons.addWidget(export_btn)
        buttons.addWidget(csv_btn)
        buttons.addStretch(1)
        root.addLayout(buttons)

        hint = QLabel(f"目标页面：{TARGET_URL}")
        hint.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root.addWidget(hint)

        root.addWidget(self.table, stretch=4)
        root.addWidget(QLabel("运行日志"))
        root.addWidget(self.log_box, stretch=1)
        self.setCentralWidget(central)

    def default_output_name(self) -> str:
        return f"sendgoods_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    def choose_template(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择模板文件", str(ROOT), "Excel 文件 (*.xlsx)")
        if path:
            self.template_edit.setText(path)

    def choose_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "选择输出文件", str(ROOT / "outputs" / self.default_output_name()), "Excel 文件 (*.xlsx)")
        if path:
            self.output_edit.setText(path)

    def open_browser(self) -> None:
        try:
            self.reader.cdp_endpoint = self.cdp_edit.text().strip() or "http://127.0.0.1:9222"
            self.reader.open_target_page()
            self.log("浏览器已准备好。若页面要求登录，请先在浏览器完成登录。")
        except Exception as exc:  # noqa: BLE001
            self.show_error("打开浏览器失败", exc)

    def collect_records(self) -> None:
        try:
            self.reader.cdp_endpoint = self.cdp_edit.text().strip() or "http://127.0.0.1:9222"
            self.records = self.reader.collect(max_scrolls=self.scroll_spin.value())
            self.populate_table()
            self.log(f"采集完成：{len(self.records)} 条 SKU 明细。")
        except Exception as exc:  # noqa: BLE001
            self.show_error("采集失败", exc)

    def export_excel(self) -> None:
        if not self.records:
            QMessageBox.warning(self, "没有数据", "请先采集当前页。")
            return
        try:
            summary = write_purchase_sheet(
                self.records,
                template_path=self.template_edit.text().strip(),
                output_path=self.output_edit.text().strip(),
                image_dir=ROOT / "downloads" / "images",
                logger=self.log,
            )
            self.log(f"Excel 已生成：{summary.output_path}")
            self.log(f"黑色行数：{summary.black_rows}，白色行数：{summary.white_rows}，跳过：{summary.skipped_records}")
            for warning in summary.warnings:
                self.log(f"警告：{warning}")
            QMessageBox.information(self, "完成", f"Excel 已生成：\n{summary.output_path}")
        except Exception as exc:  # noqa: BLE001
            self.show_error("生成 Excel 失败", exc)

    def export_csv(self) -> None:
        if not self.records:
            QMessageBox.warning(self, "没有数据", "请先采集当前页。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出CSV预览", str(ROOT / "outputs" / "records_preview.csv"), "CSV 文件 (*.csv)")
        if not path:
            return
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["颜色", "货号", "尺码", "件数", "SKU货号", "备货单号", "母单号", "图片"])
            for record in self.records:
                writer.writerow([
                    record.color,
                    record.product_sku,
                    record.size,
                    record.quantity,
                    record.sku_code,
                    record.beihuo_order,
                    record.parent_order,
                    record.image_url,
                ])
        self.log(f"CSV 已导出：{path}")

    def populate_table(self) -> None:
        self.table.setRowCount(len(self.records))
        for row, record in enumerate(self.records):
            values = [
                record.color,
                record.product_sku,
                record.size,
                str(record.quantity),
                record.sku_code,
                record.beihuo_order,
                record.parent_order,
                record.image_url,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 3:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)
        self.table.resizeColumnsToContents()

    def log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.appendPlainText(f"[{timestamp}] {message}")
        QApplication.processEvents()

    def show_error(self, title: str, exc: Exception) -> None:
        self.log(f"{title}：{exc}")
        QMessageBox.critical(self, title, str(exc))

    def closeEvent(self, event) -> None:  # noqa: N802
        try:
            self.reader.close()
        finally:
            super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
