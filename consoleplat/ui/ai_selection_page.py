from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from PyQt5.QtCore import QProcess, Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from consoleplat.config import AppSettings, SettingsStore
from consoleplat.runtime import cli_command
from consoleplat.services.ai_selection_service import (
    SelectionCandidate,
    create_batch,
    download_candidate_images,
    export_batch,
    load_batches,
    load_candidates,
    rank_candidates,
)


class AISelectionPage(QWidget):
    def __init__(self, parent: QWidget | None = None, settings: AppSettings | None = None) -> None:
        super().__init__(parent)
        self.store = SettingsStore()
        self.settings = settings or self.store.load()
        self.process: QProcess | None = None
        self._build_ui()
        self._load_history()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)
        content = QWidget()
        scroll.setWidget(content)
        root = QVBoxLayout(content)
        root.setContentsMargins(0, 0, 10, 18)
        root.setSpacing(14)

        header = QFrame()
        header.setObjectName("panel")
        layout = QVBoxLayout(header)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)
        top = QHBoxLayout()
        title = QLabel("销量选品")
        title.setObjectName("sectionTitle")
        self.status_label = QLabel("就绪：仅读取 Temu 搜索结果，不执行站点写入操作")
        self.status_label.setObjectName("statusPill")
        self.status_label.setWordWrap(True)
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(self.status_label)
        layout.addLayout(top)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        controls.addWidget(QLabel("关键词"))
        self.keyword_edit = QPlainTextEdit()
        self.keyword_edit.setObjectName("aiSelectionKeywordEdit")
        self.keyword_edit.setPlainText("\n".join(self.settings.ai_selection_keywords))
        self.keyword_edit.setMaximumHeight(62)
        self.keyword_edit.setPlaceholderText("每行一个关键词")
        controls.addWidget(self.keyword_edit, 1)
        self.start_button = QPushButton("开始选品")
        self.start_button.setObjectName("primaryButton")
        self.start_button.clicked.connect(self.start_selection)
        self.stop_button = QPushButton("停止")
        self.stop_button.setObjectName("ghostButton")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_selection)
        controls.addWidget(self.start_button)
        controls.addWidget(self.stop_button)
        layout.addLayout(controls)

        self.output_label = QLabel("保存目录：--")
        self.output_label.setObjectName("cardSubtitle")
        self.output_label.setWordWrap(True)
        self.output_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.output_label)
        root.addWidget(header)

        results_panel = QFrame()
        results_panel.setObjectName("panel")
        results_layout = QVBoxLayout(results_panel)
        results_layout.setContentsMargins(18, 14, 18, 14)
        results_layout.setSpacing(10)
        result_top = QHBoxLayout()
        result_title = QLabel("选品批次")
        result_title.setObjectName("panelTitle")
        self.batch_combo = QComboBox()
        self.batch_combo.setObjectName("aiSelectionBatchCombo")
        self.batch_combo.currentIndexChanged.connect(self._on_batch_changed)
        self.open_link_button = QPushButton("打开链接")
        self.open_link_button.setObjectName("ghostButton")
        self.open_link_button.clicked.connect(self.open_selected_link)
        self.open_image_button = QPushButton("打开主图")
        self.open_image_button.setObjectName("ghostButton")
        self.open_image_button.clicked.connect(self.open_selected_image)
        self.open_folder_button = QPushButton("打开批次目录")
        self.open_folder_button.setObjectName("ghostButton")
        self.open_folder_button.clicked.connect(self.open_current_batch_folder)
        result_top.addWidget(result_title)
        result_top.addWidget(self.batch_combo, 1)
        result_top.addWidget(self.open_link_button)
        result_top.addWidget(self.open_image_button)
        result_top.addWidget(self.open_folder_button)
        results_layout.addLayout(result_top)

        self.results_table = QTableWidget(0, 8)
        self.results_table.setObjectName("aiSelectionResultsTable")
        self.results_table.setHorizontalHeaderLabels(("排名", "商品标题", "销量", "价格", "关键词", "状态", "主图", "失败原因"))
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setMinimumHeight(280)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        results_layout.addWidget(self.results_table)
        root.addWidget(results_panel)

        log_panel = QFrame()
        log_panel.setObjectName("panel")
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(18, 14, 18, 14)
        log_layout.setSpacing(8)
        log_title = QLabel("任务日志与异常")
        log_title.setObjectName("panelTitle")
        self.log_list = QListWidget()
        self.log_list.setObjectName("eventList")
        self.log_list.setMinimumHeight(150)
        log_layout.addWidget(log_title)
        log_layout.addWidget(self.log_list)
        root.addWidget(log_panel)
        root.addStretch(1)

    def current_keywords(self) -> list[str]:
        keywords = [line.strip() for line in self.keyword_edit.toPlainText().splitlines() if line.strip()]
        return keywords or ["黑白T恤"]

    def reload_settings(self, settings: AppSettings | None = None) -> None:
        if self.process is not None:
            return
        self.settings = settings or self.store.load()
        self.keyword_edit.setPlainText("\n".join(self.settings.ai_selection_keywords))
        self._load_history()

    def start_selection(self) -> None:
        if self.process is not None:
            return
        if not self.settings.program_data_dir.strip():
            self.status_label.setText("请先在设置中配置程序数据目录，AI 选品不会保存到 C 盘")
            return
        self.log_list.clear()
        self.status_label.setText("正在连接 Chrome 并读取 Temu 搜索结果...")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        program, args = cli_command(
            "ai-selection-fetch",
            "--cdp-endpoint",
            self.settings.cdp_endpoint,
            "--keywords",
            *self.current_keywords(),
            unbuffered=True,
        )
        process = QProcess(self)
        process.setProgram(program)
        process.setArguments(args)
        process.finished.connect(self._on_process_finished)
        process.errorOccurred.connect(self._on_process_error)
        self.process = process
        process.start()

    def stop_selection(self) -> None:
        if self.process is None:
            return
        self.process.kill()
        self.process.waitForFinished(1500)
        self.process = None
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("已停止选品任务；未关闭你的 Chrome")

    def _on_process_finished(self, _exit_code: int, _exit_status) -> None:
        process = self.process
        if process is None:
            return
        stdout = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace").strip()
        stderr = bytes(process.readAllStandardError()).decode("utf-8", errors="replace").strip()
        self.process = None
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        try:
            payload = json.loads(stdout)
        except Exception:
            self.status_label.setText(f"选品进程未返回有效结果：{stderr or stdout[-300:]}")
            return
        self.handle_fetch_payload(payload)

    def _on_process_error(self, error) -> None:
        self.process = None
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText(f"选品进程启动失败：{error}")

    def handle_fetch_payload(self, payload: dict) -> None:
        for message in payload.get("logs") or []:
            self.log_list.addItem(str(message))
        if not payload.get("ok"):
            self.status_label.setText(str(payload.get("message") or "选品读取失败"))
            return
        candidates = [self._candidate_from_payload(item) for item in (payload.get("candidates") or []) if isinstance(item, dict)]
        ranked = rank_candidates(candidates, limit=30)
        batch = create_batch(self.settings.program_data_dir, self.current_keywords())
        download_candidate_images(ranked, batch.image_dir)
        failures = [str(item) for item in (payload.get("failures") or [])]
        failures.extend(candidate.error for candidate in ranked if candidate.error)
        result = export_batch(batch, ranked, failures)
        self.status_label.setText(f"选品完成：按销量保留 {len(ranked)} 条，失败 {len(failures)} 条")
        self.output_label.setText(f"保存目录：{result.batch_dir}")
        self._load_history(select_path=result.batch_dir)

    def _candidate_from_payload(self, item: dict) -> SelectionCandidate:
        sales_count = item.get("sales_count")
        return SelectionCandidate(
            title=str(item.get("title") or "未命名商品"),
            sales_text=str(item.get("sales_text") or ""),
            sales_count=int(sales_count) if sales_count is not None else None,
            price=str(item.get("price") or ""),
            product_url=str(item.get("product_url") or ""),
            image_url=str(item.get("image_url") or ""),
            keyword=str(item.get("keyword") or ""),
        )

    def _load_history(self, select_path: Path | None = None) -> None:
        batches = load_batches(self.settings.program_data_dir)
        self.batch_combo.blockSignals(True)
        self.batch_combo.clear()
        for batch in batches:
            self.batch_combo.addItem(batch.batch_dir.name, str(batch.batch_dir))
        self.batch_combo.blockSignals(False)
        if not batches:
            self.results_table.setRowCount(0)
            return
        index = 0
        if select_path is not None:
            found = self.batch_combo.findData(str(select_path))
            index = max(0, found)
        self.batch_combo.setCurrentIndex(index)
        self._load_batch(batches[index])

    def _on_batch_changed(self, index: int) -> None:
        if index < 0:
            return
        path = Path(str(self.batch_combo.itemData(index) or ""))
        if not path.is_dir():
            return
        batch = next((item for item in load_batches(self.settings.program_data_dir) if item.batch_dir == path), None)
        if batch is not None:
            self._load_batch(batch)

    def _load_batch(self, batch) -> None:
        candidates = load_candidates(batch)
        self.output_label.setText(f"保存目录：{batch.batch_dir}")
        self.results_table.setRowCount(len(candidates))
        for row, candidate in enumerate(candidates):
            values = (
                str(candidate.rank),
                candidate.title,
                candidate.sales_text,
                candidate.price,
                candidate.keyword,
                candidate.status,
                Path(candidate.local_image_path).name if candidate.local_image_path else "--",
                candidate.error,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setTextAlignment(Qt.AlignCenter)
                if column == 1:
                    item.setData(Qt.UserRole, candidate.product_url)
                    item.setData(Qt.UserRole + 1, candidate.local_image_path)
                self.results_table.setItem(row, column, item)
        for column, width in enumerate((58, 300, 90, 90, 120, 100, 130)):
            self.results_table.setColumnWidth(column, width)

    def _selected_metadata(self) -> tuple[str, str]:
        row = self.results_table.currentRow()
        if row < 0:
            return "", ""
        title = self.results_table.item(row, 1)
        if title is None:
            return "", ""
        return str(title.data(Qt.UserRole) or ""), str(title.data(Qt.UserRole + 1) or "")

    def open_selected_link(self) -> None:
        link, _image = self._selected_metadata()
        if link:
            QDesktopServices.openUrl(QUrl(link))

    def open_selected_image(self) -> None:
        _link, image = self._selected_metadata()
        if image and Path(image).is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(image))

    def open_current_batch_folder(self) -> None:
        path = str(self.batch_combo.currentData() or "")
        if not path:
            return
        try:
            os.startfile(path)  # noqa: S606 - explicit local-folder action.
        except Exception:
            subprocess.Popen(["explorer", path])

    def closeEvent(self, event) -> None:  # noqa: N802
        self.stop_selection()
        super().closeEvent(event)
