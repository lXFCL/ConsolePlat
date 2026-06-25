from __future__ import annotations

import copy
import os
import re
import site
import shutil
import subprocess
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QProcess, Qt, QThread, QObject, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSizePolicy,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PIL import Image

from consoleplat.adapters.posaiimg_adapter import AIEditJob, PosAiImgAdapter
from consoleplat.config import AppSettings, SettingsStore
from consoleplat.services.ai_edit_formalize_service import (
    backfill_xlsx_colors_from_transparent_dir,
    build_product_images,
    formalize_ai_edit_outputs,
)
from consoleplat.services.ai_edit_postprocess_service import prepare_ai_edit_print_assets
from consoleplat.services.ai_image_edit_cli import convert_image_to_transparent_background, split_collage_image_with_guides
from consoleplat.services.posai_batch_service import build_batch_paths, suggest_next_start
from consoleplat.services.putaway_sync_service import IMAGE_SUFFIXES, sync_putaway_assets
from consoleplat.services.split_profile_store import SplitProfile, SplitProfileStore
from consoleplat.services.task_store import TaskStore

DEFAULT_SPLIT_X_GUIDES = [428, 805, 1229, 1638]
DEFAULT_SPLIT_Y_GUIDES = [482, 852, 1229, 1587]


class NoWheelSpinBox(QSpinBox):
    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()


class NoWheelComboBox(QComboBox):
    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()


@dataclass
class AIEditTaskRecord:
    task_id: str
    title: str
    job: AIEditJob
    status: str = "等待启动"
    stage_text: str = "等待启动"
    progress_percent: int = 0
    logs: list[str] = field(default_factory=list)
    output_dir: str = ""
    outputs: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    round_sources: list[str] = field(default_factory=list)
    collage_transparent_sources: list[str] = field(default_factory=list)
    active_round_index: int = 0
    final_transparent_dir: str = ""
    final_product_dir: str = ""
    xlsx_path: str = ""
    split_profile: dict[str, object] = field(default_factory=dict)


@dataclass
class BackgroundTaskResult:
    action: str
    task_id: str
    outputs: list[str] = field(default_factory=list)
    round_sources: list[str] = field(default_factory=list)
    final_transparent_dir: str = ""
    final_product_dir: str = ""
    xlsx_path: str = ""
    failed: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)


class AIEditBackgroundWorker(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str, str, str)
    log_message = pyqtSignal(str, str)

    def __init__(self, action: str, record: AIEditTaskRecord, settings: AppSettings) -> None:
        super().__init__()
        self.action = action
        self.record = copy.deepcopy(record)
        self.settings = copy.deepcopy(settings)

    def run(self) -> None:
        try:
            if self.action == "post_process":
                result = self._run_post_process()
            elif self.action == "split_current_round":
                result = self._run_split_current_round()
            elif self.action == "convert_current_round":
                result = self._run_convert_current_round()
            elif self.action == "export_product_images":
                result = self._run_export_product_images()
            elif self.action == "backfill_colors":
                result = self._run_backfill_colors()
            else:
                raise ValueError(f"unsupported background action: {self.action}")
        except Exception as exc:
            self.failed.emit(self.action, self.record.task_id, str(exc))
            return
        self.finished.emit(result)

    def _emit_log(self, text: str) -> None:
        self.log_message.emit(self.record.task_id, text)

    def _run_post_process(self) -> BackgroundTaskResult:
        result = BackgroundTaskResult(action=self.action, task_id=self.record.task_id)
        prepared_assets = prepare_ai_edit_print_assets(
            source_paths=[str(path) for path in self.record.round_sources or self._derive_round_sources_from_outputs(self.record.outputs)],
            final_transparent_dir=self.record.final_transparent_dir or self.record.output_dir,
            prefix=self.record.job.prefix,
            start_number=self.record.job.start_number,
            split_collage=self.record.job.split_collage,
            split_count=self.record.job.split_count,
            x_guides=list(self.record.split_profile.get("x_guides") or []),
            y_guides=list(self.record.split_profile.get("y_guides") or []),
            drop_first_split=bool(self.settings.ai_edit_drop_first_per_round),
        )
        prepared_paths = [str(path) for asset in prepared_assets for path in asset.split_paths]
        transparent_rounds = [str(asset.transparent_path) for asset in prepared_assets if asset.transparent_path]
        result.outputs = prepared_paths or list(self.record.outputs)
        result.round_sources = transparent_rounds or list(self.record.round_sources)
        if prepared_paths:
            result.final_transparent_dir = str(Path(prepared_paths[0]).parent)

        if not self.record.job.test_mode:
            split_paths = [Path(path) for path in result.outputs if Path(path).suffix.lower() == ".png"]
            if not split_paths:
                raise ValueError("未找到可正式入库的切图产物")
            product_title = (
                self.settings.bo_product_title.strip()
                if self.record.job.prefix == "BO"
                else self.settings.szw_product_title.strip()
            )
            formalize_summary = formalize_ai_edit_outputs(
                split_paths=split_paths,
                final_transparent_dir=Path(result.final_transparent_dir or self.record.final_transparent_dir),
                final_product_dir=Path(self.record.final_product_dir),
                xlsx_path=Path(self.record.xlsx_path),
                putaway_data_dir=Path(self.settings.putaway_data_dir),
                model_dir=Path(self.settings.posai_model_root),
                prefix=self.record.job.prefix,
                start_number=self.record.job.start_number,
                product_title=product_title,
                xlsx_batch_start_number=self.record.job.start_number,
                xlsx_batch_count=max(1, len(split_paths)),
                saturation_threshold=self.settings.ai_edit_grayscale_saturation_threshold,
            )
            if not formalize_summary.ok:
                raise ValueError(formalize_summary.message)
            result.outputs = list(formalize_summary.product_outputs or result.outputs)
            result.round_sources = list(formalize_summary.renamed_outputs or result.round_sources)
            result.final_product_dir = self.record.final_product_dir
            result.xlsx_path = formalize_summary.xlsx_path or self.record.xlsx_path
            if formalize_summary.putaway and formalize_summary.putaway.message:
                result.warnings.append(formalize_summary.putaway.message)
            result.logs.append(formalize_summary.message)
        return result

    def _run_split_current_round(self) -> BackgroundTaskResult:
        source_path = self.record.round_sources[0] if self.record.round_sources else ""
        if not source_path:
            raise ValueError("missing split source")
        output_dir = Path(source_path).parent / f"{Path(source_path).stem}_split"
        split_paths = split_collage_image_with_guides(
            source_path,
            output_dir,
            self.record.job.split_count,
            list(self.record.split_profile.get("x_guides") or []),
            list(self.record.split_profile.get("y_guides") or []),
            original_image=self._find_original_round_source(source_path, self.record.outputs),
        )
        final_outputs = self._copy_split_outputs_to_final_gallery(self.record, [Path(path) for path in split_paths])
        return BackgroundTaskResult(
            action=self.action,
            task_id=self.record.task_id,
            outputs=[str(path) for path in (final_outputs or [Path(path) for path in split_paths])],
            round_sources=[source_path],
            final_transparent_dir=self.record.final_transparent_dir,
        )

    def _run_convert_current_round(self) -> BackgroundTaskResult:
        source_path = self.record.round_sources[0] if self.record.round_sources else ""
        if not source_path:
            raise ValueError("missing convert source")
        output = convert_image_to_transparent_background(source_path)
        outputs = list(self.record.outputs)
        if output not in outputs:
            outputs.append(output)
        return BackgroundTaskResult(
            action=self.action,
            task_id=self.record.task_id,
            outputs=outputs,
            round_sources=self._derive_round_sources_from_outputs(outputs),
        )

    def _run_export_product_images(self) -> BackgroundTaskResult:
        final_transparent_dir = Path(self.record.final_transparent_dir) if self.record.final_transparent_dir else None
        final_product_dir = Path(self.record.final_product_dir) if self.record.final_product_dir else None
        xlsx_path = Path(self.record.xlsx_path) if self.record.xlsx_path else None
        if final_transparent_dir is None or not final_transparent_dir.exists():
            raise ValueError(f"最终透明底目录不存在：{self.record.final_transparent_dir or '--'}")
        if final_product_dir is None:
            raise ValueError(f"最终产品图目录不存在：{self.record.final_product_dir or '--'}")
        if xlsx_path is None or not xlsx_path.exists():
            raise ValueError(f"XLSX 不存在：{self.record.xlsx_path or '--'}")
        print_paths = sorted(
            [path for path in final_transparent_dir.iterdir() if path.is_file() and path.suffix.lower() == ".png"],
            key=lambda path: path.name.lower(),
        )
        if not print_paths:
            raise ValueError(f"最终透明底目录为空：{final_transparent_dir}")
        product_title = (
            self.settings.bo_product_title.strip()
            if self.record.job.prefix == "BO"
            else self.settings.szw_product_title.strip()
        )
        self._emit_log(f"开始重贴产品图：{len(print_paths)} 张透明底")
        self._emit_log(f"透明底目录：{final_transparent_dir}")
        product_outputs, _color_assignments = build_product_images(
            print_paths=print_paths,
            final_product_dir=final_product_dir,
            product_title=product_title,
            model_dir=Path(self.settings.posai_model_root),
            saturation_threshold=self.settings.ai_edit_grayscale_saturation_threshold,
        )
        if not product_outputs:
            raise ValueError("产品图生成失败：未生成有效产品图")
        self._emit_log(f"已重贴产品图 {len(product_outputs)} 张到 {final_product_dir}")
        sync_summary = sync_putaway_assets(
            source_images_dir=final_product_dir,
            source_xlsx_path=xlsx_path,
            target_data_dir=Path(self.settings.putaway_data_dir),
            force_replace=True,
        )
        if not sync_summary.ok:
            raise ValueError(f"同步到上架 data 失败：{sync_summary.message}")
        self._emit_log(
            f"已同步到上架 data：图片目录 {sync_summary.images_target_dir}，XLSX {sync_summary.xlsx_target_path}"
        )
        return BackgroundTaskResult(
            action=self.action,
            task_id=self.record.task_id,
            outputs=[str(path) for path in product_outputs],
            final_product_dir=str(final_product_dir),
            xlsx_path=str(xlsx_path),
            logs=[f"导出产品图完成：重贴 {len(product_outputs)} 张"],
        )

    def _run_backfill_colors(self) -> BackgroundTaskResult:
        xlsx_path = Path(self.record.xlsx_path) if self.record.xlsx_path else None
        final_transparent_dir = Path(self.record.final_transparent_dir) if self.record.final_transparent_dir else None
        if xlsx_path is None or final_transparent_dir is None:
            return BackgroundTaskResult(action=self.action, task_id=self.record.task_id)
        updated = backfill_xlsx_colors_from_transparent_dir(
            xlsx_path=xlsx_path,
            final_transparent_dir=final_transparent_dir,
            saturation_threshold=self.settings.ai_edit_grayscale_saturation_threshold,
        )
        logs = [f"已回填 xlsx 颜色 {updated} 行"] if updated else []
        return BackgroundTaskResult(
            action=self.action,
            task_id=self.record.task_id,
            xlsx_path=str(xlsx_path),
            logs=logs,
        )

    def _derive_round_sources_from_outputs(self, outputs: list[str]) -> list[str]:
        non_split = [path for path in outputs if Path(path).suffix.lower() == ".png" and "_part_" not in Path(path).stem.lower()]
        return non_split or [path for path in outputs if Path(path).suffix.lower() == ".png"]

    def _find_original_round_source(self, source_path: str, outputs: list[str]) -> str | None:
        source = Path(source_path)
        candidate_name = source.stem.replace("_transparent", "")
        candidate = source.with_name(f"{candidate_name}{source.suffix}")
        if candidate.exists():
            return str(candidate)
        for output in outputs:
            output_path = Path(output)
            if output_path == source:
                continue
            if output_path.stem == candidate_name and output_path.suffix.lower() == source.suffix.lower() and output_path.exists():
                return str(output_path)
        return None

    def _copy_split_outputs_to_final_gallery(self, record: AIEditTaskRecord, split_paths: list[Path]) -> list[Path]:
        split_paths = [path for path in split_paths if "_part_" in path.stem.lower()]
        if not split_paths:
            return []
        target_root = Path(record.final_transparent_dir) if record.final_transparent_dir else Path(record.output_dir)
        target_root.mkdir(parents=True, exist_ok=True)
        outputs: list[Path] = []
        current_number = record.job.start_number
        for source in split_paths:
            target = target_root / f"{record.job.prefix}-{current_number}.png"
            target.write_bytes(source.read_bytes())
            outputs.append(target)
            current_number += 1
        record.final_transparent_dir = str(target_root)
        return outputs


def _best_grid_for_count(count: int) -> tuple[int, int]:
    count = max(1, int(count or 1))
    columns = min(5, count)
    rows = (count + columns - 1) // columns
    return columns, rows


def _default_split_profile(split_count: int) -> dict[str, object]:
    columns = len(DEFAULT_SPLIT_X_GUIDES) + 1
    rows = len(DEFAULT_SPLIT_Y_GUIDES) + 1
    return {
        "split_count": max(1, int(split_count or columns * rows)),
        "columns": columns,
        "rows": rows,
        "x_guides": list(DEFAULT_SPLIT_X_GUIDES),
        "y_guides": list(DEFAULT_SPLIT_Y_GUIDES),
    }


def _format_split_count_hint(count: int) -> str:
    columns, rows = _best_grid_for_count(count)
    return f"{max(1, int(count or 1))} 张 ({columns} x {rows})"


def _legacy_round_sources_from_batch_dirs(
    *,
    output_dir: str,
    final_transparent_dir: str,
) -> list[str]:
    candidates: list[Path] = []
    output_path = Path(output_dir) if output_dir else None
    final_transparent_path = Path(final_transparent_dir) if final_transparent_dir else None
    if output_path:
        candidates.append(output_path)
    if final_transparent_path and final_transparent_path.parent not in candidates:
        candidates.append(final_transparent_path.parent)

    round_paths: list[Path] = []
    seen: set[str] = set()
    for base in candidates:
        if not base.exists():
            continue
        transparent_rounds: list[Path] = []
        fallback_rounds: list[Path] = []
        for path in sorted(base.glob("edited_round_*.png"), key=lambda item: item.name.lower()):
            stem = path.stem.lower()
            if "_part_" in stem or stem.endswith(".prompt"):
                continue
            if stem.endswith("_transparent"):
                transparent_rounds.append(path)
            else:
                fallback_rounds.append(path)
        selected = transparent_rounds or fallback_rounds
        for path in selected:
            key = str(path.resolve())
            if key in seen:
                continue
            seen.add(key)
            round_paths.append(path)
    return [str(path) for path in round_paths]


def _expected_round_count(record: AIEditTaskRecord) -> int:
    try:
        return max(1, int(record.job.total_return_count or 1))
    except (TypeError, ValueError):
        return 1


def _path_key(path_text: str) -> str:
    path = Path(path_text)
    try:
        return str(path.resolve(strict=False)).lower()
    except (OSError, RuntimeError):
        return str(path).lower()


def _round_index_from_source_name(source_path: str) -> int | None:
    match = re.search(r"edited_round_(\d+)", Path(source_path).stem, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return max(0, int(match.group(1)) - 1)
    except ValueError:
        return None


def _looks_like_final_transparent_round_sources(round_sources: list[str], final_transparent_dir: str) -> bool:
    if not round_sources or not final_transparent_dir:
        return False
    final_dir = Path(final_transparent_dir)
    if not final_dir.exists():
        return False
    normalized_final_dir = str(final_dir.resolve(strict=False)).lower()
    for path_text in round_sources:
        path = Path(path_text)
        if path.suffix.lower() != ".png":
            return False
        try:
            parent_text = str(path.parent.resolve(strict=False)).lower()
        except OSError:
            parent_text = str(path.parent).lower()
        if parent_text != normalized_final_dir:
            return False
        stem = path.stem.lower()
        if stem.startswith("edited_round_"):
            return False
    return True


def _format_task_timestamp(value: str) -> str:
    clean = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(clean) >= 14:
        clean = clean[:14]
        return f"{clean[:4]}.{clean[4:8]}.{clean[8:12]}.{clean[12:14]}"
    if len(clean) == 12:
        return f"{clean[:4]}.{clean[4:8]}.{clean[8:12]}"
    return str(value or "")


def _progress_from_text(text: str) -> int | None:
    matches: list[int] = []
    for token in str(text or "").replace("，", " ").replace(",", " ").split():
        if token.endswith("%"):
            number = token[:-1]
            if number.isdigit():
                matches.append(int(number))
    if not matches:
        return None
    return max(0, min(100, matches[-1]))


class AIEditTaskDetailDialog(QDialog):
    def __init__(self, record: AIEditTaskRecord, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.record = record
        self._page = parent
        self._active_source_index = 0
        self.setWindowTitle(f"任务详情 - {record.title}")
        self.resize(920, 680)

        layout = QVBoxLayout(self)
        title = QLabel(record.title)
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.meta_label = QLabel()
        layout.addWidget(self.meta_label)

        self.path_panel = QFrame()
        self.path_panel.setObjectName("subPanel")
        path_layout = QGridLayout(self.path_panel)
        path_layout.setContentsMargins(12, 12, 12, 12)
        path_layout.setHorizontalSpacing(10)
        path_layout.setVerticalSpacing(8)
        self.batch_path_button = QPushButton("--")
        self.batch_path_button.setObjectName("ghostButton")
        self.batch_path_button.clicked.connect(lambda: self.open_path(self.batch_path_button.text()))
        self.transparent_path_button = QPushButton("--")
        self.transparent_path_button.setObjectName("ghostButton")
        self.transparent_path_button.clicked.connect(lambda: self.open_path(self.transparent_path_button.text()))
        self.product_path_button = QPushButton("--")
        self.product_path_button.setObjectName("ghostButton")
        self.product_path_button.clicked.connect(lambda: self.open_path(self.product_path_button.text()))
        self.xlsx_path_button = QPushButton("--")
        self.xlsx_path_button.setObjectName("ghostButton")
        self.xlsx_path_button.clicked.connect(lambda: self.open_path(self.xlsx_path_button.text()))
        path_layout.addWidget(QLabel("任务目录"), 0, 0)
        path_layout.addWidget(self.batch_path_button, 0, 1)
        path_layout.addWidget(QLabel("最终透明底"), 1, 0)
        path_layout.addWidget(self.transparent_path_button, 1, 1)
        path_layout.addWidget(QLabel("最终产品图"), 2, 0)
        path_layout.addWidget(self.product_path_button, 2, 1)
        path_layout.addWidget(QLabel("XLSX"), 3, 0)
        path_layout.addWidget(self.xlsx_path_button, 3, 1)
        layout.addWidget(self.path_panel)

        self.round_index_label = QLabel()
        self.source_path_label = QLabel("--")
        self.source_path_label.setWordWrap(True)
        layout.addWidget(self.round_index_label)
        layout.addWidget(self.source_path_label)

        row_one = QHBoxLayout()
        self.prev_round_button = QPushButton("上一轮")
        self.prev_round_button.clicked.connect(self.show_previous_round)
        self.next_round_button = QPushButton("下一轮")
        self.next_round_button.clicked.connect(self.show_next_round)
        self.convert_transparent_button = QPushButton("转透明底")
        self.convert_transparent_button.clicked.connect(self.convert_current_round)
        row_one.addWidget(self.prev_round_button)
        row_one.addWidget(self.next_round_button)
        row_one.addWidget(self.convert_transparent_button)
        row_one.addStretch(1)

        row_two = QHBoxLayout()
        self.start_split_button = QPushButton("直接切割")
        self.start_split_button.clicked.connect(self.split_current_round)
        self.edit_split_profile_button = QPushButton("手动切线")
        self.edit_split_profile_button.clicked.connect(self.edit_split_profile)
        self.export_product_button = QPushButton("导出产品图")
        self.export_product_button.clicked.connect(self.export_product_images)
        self.export_xlsx_button = QPushButton("导出 xlsx")
        self.export_xlsx_button.clicked.connect(self.export_xlsx)
        self.sync_putaway_button = QPushButton("同步到上架 data")
        self.sync_putaway_button.clicked.connect(self.sync_to_putaway_data)
        row_two.addWidget(self.start_split_button)
        row_two.addWidget(self.edit_split_profile_button)
        row_two.addWidget(self.export_product_button)
        row_two.addWidget(self.export_xlsx_button)
        row_two.addWidget(self.sync_putaway_button)
        row_two.addStretch(1)
        layout.addLayout(row_one)
        layout.addLayout(row_two)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log, stretch=1)

        self.refresh(record)

    def refresh(self, record: AIEditTaskRecord) -> None:
        self.record = record
        self.meta_label.setText(
            f"状态: {record.status}    阶段: {record.stage_text}    前缀: {record.job.prefix}    起始: {record.job.start_number}    轮数: {record.job.total_return_count}"
        )
        self._set_path_button(self.batch_path_button, record.output_dir)
        self._set_path_button(self.transparent_path_button, record.final_transparent_dir)
        self._set_path_button(self.product_path_button, record.final_product_dir)
        self._set_path_button(self.xlsx_path_button, record.xlsx_path)
        sections: list[str] = []
        if record.failed:
            sections.append("失败项:\n" + "\n".join(str(item) for item in record.failed))
        if record.warnings:
            sections.append("警告:\n" + "\n".join(str(item) for item in record.warnings))
        if record.logs:
            sections.append("日志:\n" + "\n".join(record.logs))
        self.log.setPlainText("\n\n".join(sections))
        self._refresh_round_view()

    def _derive_round_sources(self, record: AIEditTaskRecord) -> list[str]:
        if record.round_sources:
            return list(record.round_sources)
        outputs = [path for path in record.outputs if path.lower().endswith(".png")]
        transparent = [
            path
            for path in outputs
            if "transparent" in Path(path).stem.lower() and "_part_" not in Path(path).stem.lower()
        ]
        if transparent:
            return transparent
        non_split = [path for path in outputs if "_part_" not in Path(path).stem.lower()]
        return non_split or outputs

    def _find_split_source(self, record: AIEditTaskRecord) -> str:
        sources = self._derive_round_sources(record)
        if not sources:
            return ""
        return sources[min(self._active_source_index, len(sources) - 1)]

    def _refresh_round_view(self) -> None:
        sources = self._derive_round_sources(self.record)
        if not sources:
            self.round_index_label.setText("--")
            self.source_path_label.setText("--")
            self.prev_round_button.setEnabled(False)
            self.next_round_button.setEnabled(False)
            self.convert_transparent_button.setEnabled(False)
            self.start_split_button.setEnabled(False)
            self.edit_split_profile_button.setEnabled(False)
            self.export_product_button.setEnabled(False)
            self.export_xlsx_button.setEnabled(False)
            self.sync_putaway_button.setEnabled(False)
            return
        self._active_source_index = max(0, min(self._active_source_index, len(sources) - 1))
        self.round_index_label.setText(f"{self._active_source_index + 1}/{len(sources)}")
        self.source_path_label.setText(sources[self._active_source_index])
        self.prev_round_button.setEnabled(self._active_source_index > 0)
        self.next_round_button.setEnabled(self._active_source_index < len(sources) - 1)
        self.convert_transparent_button.setEnabled(True)
        self.start_split_button.setEnabled(True)
        self.edit_split_profile_button.setEnabled(True)
        has_products = self._has_product_outputs()
        has_xlsx = bool(self.record.xlsx_path and Path(self.record.xlsx_path).exists())
        self.export_product_button.setEnabled(has_products)
        self.export_xlsx_button.setEnabled(has_xlsx)
        self.sync_putaway_button.setEnabled(has_products and has_xlsx)

    def _has_product_outputs(self) -> bool:
        if not self.record.final_product_dir:
            return False
        directory = Path(self.record.final_product_dir)
        if not directory.exists() or not directory.is_dir():
            return False
        return any(path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES for path in directory.iterdir())

    def show_previous_round(self) -> None:
        if self._active_source_index > 0:
            self._active_source_index -= 1
            self._refresh_round_view()

    def show_next_round(self) -> None:
        sources = self._derive_round_sources(self.record)
        if self._active_source_index < len(sources) - 1:
            self._active_source_index += 1
            self._refresh_round_view()

    def _set_path_button(self, button: QPushButton, path: str) -> None:
        text = str(path or "--")
        button.setText(text)
        button.setToolTip(text)
        button.setEnabled(bool(path))

    def open_path(self, path_text: str) -> None:
        path = path_text if path_text and path_text != "--" else ""
        if not path:
            return
        target = Path(path)
        folder = target if target.is_dir() else target.parent
        try:
            os.startfile(str(folder))  # noqa: S606
        except Exception:
            subprocess.Popen(["explorer", str(folder)])

    def convert_current_round(self) -> None:
        if self._page is not None:
            self._page.convert_current_round(self.record, self._find_split_source(self.record))

    def split_current_round(self) -> None:
        if self._page is not None:
            self._page.split_current_round(self.record, self._find_split_source(self.record))

    def edit_split_profile(self) -> None:
        if self._page is not None:
            self._page.edit_split_profile(self.record, self._find_split_source(self.record))

    def export_product_images(self) -> None:
        if self._page is not None:
            self._page.export_task_product_images(self.record)

    def export_xlsx(self) -> None:
        if self._page is not None:
            self._page.export_task_xlsx(self.record)

    def sync_to_putaway_data(self) -> None:
        if self._page is not None:
            self._page.sync_task_to_putaway_data(self.record)


class AIEditTaskDetailDialog(QDialog):
    def __init__(self, record: AIEditTaskRecord, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.record = record
        self._page = parent
        self._active_source_index = 0
        self.setWindowTitle(f"任务详情 - {record.title}")
        self.resize(920, 680)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel(record.title)
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.meta_label = QLabel()
        self.meta_label.setWordWrap(True)
        layout.addWidget(self.meta_label)

        self.path_panel = QFrame()
        self.path_panel.setObjectName("panel")
        path_layout = QGridLayout(self.path_panel)
        path_layout.setContentsMargins(16, 14, 16, 14)
        path_layout.setHorizontalSpacing(10)
        path_layout.setVerticalSpacing(10)
        self.batch_path_button = QPushButton("--")
        self.batch_path_button.setObjectName("ghostButton")
        self.batch_path_button.clicked.connect(lambda: self.open_path(self.batch_path_button.text()))
        self.transparent_path_button = QPushButton("--")
        self.transparent_path_button.setObjectName("ghostButton")
        self.transparent_path_button.clicked.connect(lambda: self.open_path(self.transparent_path_button.text()))
        self.product_path_button = QPushButton("--")
        self.product_path_button.setObjectName("ghostButton")
        self.product_path_button.clicked.connect(lambda: self.open_path(self.product_path_button.text()))
        self.xlsx_path_button = QPushButton("--")
        self.xlsx_path_button.setObjectName("ghostButton")
        self.xlsx_path_button.clicked.connect(lambda: self.open_path(self.xlsx_path_button.text()))
        path_layout.addWidget(QLabel("任务目录"), 0, 0)
        path_layout.addWidget(self.batch_path_button, 0, 1)
        path_layout.addWidget(QLabel("最终透明底"), 1, 0)
        path_layout.addWidget(self.transparent_path_button, 1, 1)
        path_layout.addWidget(QLabel("最终产品图"), 2, 0)
        path_layout.addWidget(self.product_path_button, 2, 1)
        path_layout.addWidget(QLabel("XLSX"), 3, 0)
        path_layout.addWidget(self.xlsx_path_button, 3, 1)
        layout.addWidget(self.path_panel)

        self.round_index_label = QLabel()
        self.round_index_label.setObjectName("panelTitle")
        self.source_path_label = QLabel("--")
        self.source_path_label.setWordWrap(True)
        layout.addWidget(self.round_index_label)
        layout.addWidget(self.source_path_label)

        self.prev_round_button = QPushButton("上一轮")
        self.prev_round_button.clicked.connect(self.show_previous_round)
        self.next_round_button = QPushButton("下一轮")
        self.next_round_button.clicked.connect(self.show_next_round)
        self.convert_transparent_button = QPushButton("转透明底")
        self.convert_transparent_button.clicked.connect(self.convert_current_round)
        self.start_split_button = QPushButton("直接切割")
        self.start_split_button.clicked.connect(self.split_current_round)
        self.edit_split_profile_button = QPushButton("手动切线")
        self.edit_split_profile_button.clicked.connect(self.edit_split_profile)
        self.export_product_button = QPushButton("导出产品图")
        self.export_product_button.clicked.connect(self.export_product_images)
        self.export_xlsx_button = QPushButton("导出 xlsx")
        self.export_xlsx_button.clicked.connect(self.export_xlsx)
        self.sync_putaway_button = QPushButton("同步到上架 data")
        self.sync_putaway_button.clicked.connect(self.sync_to_putaway_data)

        self.action_grid = QGridLayout()
        self.action_grid.setHorizontalSpacing(10)
        self.action_grid.setVerticalSpacing(10)
        action_buttons = [
            self.prev_round_button,
            self.next_round_button,
            self.convert_transparent_button,
            self.start_split_button,
            self.edit_split_profile_button,
            self.export_product_button,
            self.export_xlsx_button,
            self.sync_putaway_button,
        ]
        for index, button in enumerate(action_buttons):
            button.setObjectName("ghostButton")
            button.setMinimumHeight(36)
            self.action_grid.addWidget(button, index // 4, index % 4)
        layout.addLayout(self.action_grid)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log, stretch=1)

        self.refresh(record)

    def refresh(self, record: AIEditTaskRecord) -> None:
        self.record = record
        self.meta_label.setText(
            f"状态: {record.status}    阶段: {record.stage_text}    前缀: {record.job.prefix}    起始: {record.job.start_number}    轮数: {record.job.total_return_count}"
        )
        self._set_path_button(self.batch_path_button, record.output_dir)
        self._set_path_button(self.transparent_path_button, record.final_transparent_dir)
        self._set_path_button(self.product_path_button, record.final_product_dir)
        self._set_path_button(self.xlsx_path_button, record.xlsx_path)
        sections: list[str] = []
        if record.failed:
            sections.append("失败项:\n" + "\n".join(str(item) for item in record.failed))
        if record.warnings:
            sections.append("警告:\n" + "\n".join(str(item) for item in record.warnings))
        if record.logs:
            sections.append("日志:\n" + "\n".join(record.logs))
        self.log.setPlainText("\n\n".join(sections))
        self._refresh_round_view()

    def _derive_round_sources(self, record: AIEditTaskRecord) -> list[str]:
        if record.round_sources:
            return list(record.round_sources)
        outputs = [path for path in record.outputs if path.lower().endswith(".png")]
        transparent = [
            path
            for path in outputs
            if "transparent" in Path(path).stem.lower() and "_part_" not in Path(path).stem.lower()
        ]
        if transparent:
            return transparent
        non_split = [path for path in outputs if "_part_" not in Path(path).stem.lower()]
        return non_split or outputs

    def _find_split_source(self, record: AIEditTaskRecord) -> str:
        sources = self._derive_round_sources(record)
        if not sources:
            return ""
        return sources[min(self._active_source_index, len(sources) - 1)]

    def _refresh_round_view(self) -> None:
        sources = self._derive_round_sources(self.record)
        if not sources:
            self.round_index_label.setText("--")
            self.source_path_label.setText("--")
            self.prev_round_button.setEnabled(False)
            self.next_round_button.setEnabled(False)
            self.convert_transparent_button.setEnabled(False)
            self.start_split_button.setEnabled(False)
            self.edit_split_profile_button.setEnabled(False)
            self.export_product_button.setEnabled(False)
            self.export_xlsx_button.setEnabled(False)
            self.sync_putaway_button.setEnabled(False)
            return
        self._active_source_index = max(0, min(self._active_source_index, len(sources) - 1))
        self.round_index_label.setText(f"{self._active_source_index + 1}/{len(sources)}")
        self.source_path_label.setText(sources[self._active_source_index])
        self.prev_round_button.setEnabled(self._active_source_index > 0)
        self.next_round_button.setEnabled(self._active_source_index < len(sources) - 1)
        self.convert_transparent_button.setEnabled(True)
        self.start_split_button.setEnabled(True)
        self.edit_split_profile_button.setEnabled(True)
        has_products = self._has_product_outputs()
        has_xlsx = bool(self.record.xlsx_path and Path(self.record.xlsx_path).exists())
        self.export_product_button.setEnabled(has_products)
        self.export_xlsx_button.setEnabled(has_xlsx)
        self.sync_putaway_button.setEnabled(has_products and has_xlsx)

    def _has_product_outputs(self) -> bool:
        if not self.record.final_product_dir:
            return False
        directory = Path(self.record.final_product_dir)
        if not directory.exists() or not directory.is_dir():
            return False
        return any(path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES for path in directory.iterdir())

    def show_previous_round(self) -> None:
        if self._active_source_index > 0:
            self._active_source_index -= 1
            self._refresh_round_view()

    def show_next_round(self) -> None:
        sources = self._derive_round_sources(self.record)
        if self._active_source_index < len(sources) - 1:
            self._active_source_index += 1
            self._refresh_round_view()

    def _set_path_button(self, button: QPushButton, path: str) -> None:
        text = str(path or "--")
        button.setText(text)
        button.setToolTip(text)
        button.setEnabled(bool(path))

    def open_path(self, path_text: str) -> None:
        path = path_text if path_text and path_text != "--" else ""
        if not path:
            return
        target = Path(path)
        folder = target if target.is_dir() else target.parent
        try:
            os.startfile(str(folder))  # noqa: S606
        except Exception:
            subprocess.Popen(["explorer", str(folder)])

    def convert_current_round(self) -> None:
        if self._page is not None:
            self._page.convert_current_round(self.record, self._find_split_source(self.record))

    def split_current_round(self) -> None:
        if self._page is not None:
            self._page.split_current_round(self.record, self._find_split_source(self.record))

    def edit_split_profile(self) -> None:
        if self._page is not None:
            self._page.edit_split_profile(self.record, self._find_split_source(self.record))

    def export_product_images(self) -> None:
        if self._page is not None:
            self._page.export_task_product_images(self.record)

    def export_xlsx(self) -> None:
        if self._page is not None:
            self._page.export_task_xlsx(self.record)

    def sync_to_putaway_data(self) -> None:
        if self._page is not None:
            self._page.sync_task_to_putaway_data(self.record)


class SplitProfileEditorDialog(QDialog):
    def __init__(self, record: AIEditTaskRecord, source_path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.record = record
        self.source_path = source_path
        self._image_size = self._load_image_size(source_path)
        self._syncing_fields = False
        self.setWindowTitle("手动切割线")
        self.resize(980, 720)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(source_path))

        default_x_guides, default_y_guides = self._default_guides()
        x_guides = list(record.split_profile.get("x_guides") or default_x_guides)
        y_guides = list(record.split_profile.get("y_guides") or default_y_guides)

        splitter = QSplitter(Qt.Horizontal)
        self.preview = SplitGuidePreviewWidget(source_path, x_guides, y_guides, self)
        splitter.addWidget(self.preview)

        side_panel = QWidget(self)
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(10)

        self.stats_label = QLabel(self._stats_text(x_guides, y_guides))
        self.stats_label.setWordWrap(True)
        side_layout.addWidget(self.stats_label)

        form = QFormLayout()
        self.x_guides_edit = QLineEdit(",".join(str(value) for value in x_guides))
        self.y_guides_edit = QLineEdit(",".join(str(value) for value in y_guides))
        form.addRow("纵向分割线", self.x_guides_edit)
        form.addRow("横向分割线", self.y_guides_edit)
        side_layout.addLayout(form)

        hint = QLabel("输入像素位置，多个值用半角逗号分隔，例如：240,480,720")
        hint.setWordWrap(True)
        side_layout.addWidget(hint)
        side_layout.addStretch(1)
        splitter.addWidget(side_panel)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, stretch=1)

        self.preview.guidesChanged.connect(self._sync_guide_fields)
        self.x_guides_edit.editingFinished.connect(self._apply_text_guides_to_preview)
        self.y_guides_edit.editingFinished.connect(self._apply_text_guides_to_preview)

        actions = QHBoxLayout()
        self.reset_button = QPushButton("恢复默认 5x5")
        self.save_button = QPushButton("保存并重切")
        self.cancel_button = QPushButton("取消")
        self.reset_button.clicked.connect(self.reset_guides)
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        actions.addStretch(1)
        actions.addWidget(self.reset_button)
        actions.addWidget(self.save_button)
        actions.addWidget(self.cancel_button)
        layout.addLayout(actions)

    def _load_image_size(self, source_path: str) -> tuple[int, int]:
        try:
            with Image.open(source_path) as image:
                return image.size
        except Exception:
            return (1000, 1000)

    def _default_guides(self) -> tuple[list[int], list[int]]:
        return list(DEFAULT_SPLIT_X_GUIDES), list(DEFAULT_SPLIT_Y_GUIDES)

    def _stats_text(self, x_guides: list[int], y_guides: list[int]) -> str:
        width, height = self._image_size
        return f"图片尺寸: {width} x {height}\n当前列数: {len(x_guides) + 1}\n当前行数: {len(y_guides) + 1}"

    def _parse_guide_text(self, text: str) -> list[int]:
        values: list[int] = []
        for token in str(text or "").replace("，", ",").split(","):
            stripped = token.strip()
            if stripped.isdigit():
                values.append(int(stripped))
        return sorted(set(values))

    def _sync_guide_fields(self, x_guides: list[int], y_guides: list[int]) -> None:
        self._syncing_fields = True
        self.x_guides_edit.setText(",".join(str(value) for value in x_guides))
        self.y_guides_edit.setText(",".join(str(value) for value in y_guides))
        self.stats_label.setText(self._stats_text(x_guides, y_guides))
        self._syncing_fields = False

    def _apply_text_guides_to_preview(self) -> None:
        if self._syncing_fields:
            return
        self.preview.set_guides(
            self._parse_guide_text(self.x_guides_edit.text()),
            self._parse_guide_text(self.y_guides_edit.text()),
        )

    def reset_guides(self) -> None:
        x_guides, y_guides = self._default_guides()
        self.preview.set_guides(x_guides, y_guides)

    def parsed_guides(self) -> tuple[list[int], list[int]]:
        self._apply_text_guides_to_preview()
        return self.preview.guides()


class SplitGuidePreviewWidget(QWidget):
    guidesChanged = pyqtSignal(list, list)

    def __init__(self, source_path: str, x_guides: list[int], y_guides: list[int], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pixmap = QPixmap(source_path)
        self._x_guides: list[int] = []
        self._y_guides: list[int] = []
        self._selected_axis: str | None = None
        self._selected_index: int = -1
        self._dragging = False
        self.setMinimumSize(480, 480)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.set_guides(x_guides, y_guides)

    def set_guides(self, x_guides: list[int], y_guides: list[int]) -> None:
        self._x_guides = sorted(set(int(value) for value in x_guides))
        self._y_guides = sorted(set(int(value) for value in y_guides))
        self.guidesChanged.emit(list(self._x_guides), list(self._y_guides))
        self.update()

    def guides(self) -> tuple[list[int], list[int]]:
        return list(self._x_guides), list(self._y_guides)

    def move_guide(self, axis: str, index: int, value: int) -> None:
        guides = self._x_guides if axis == "x" else self._y_guides
        limit = max(1, self._pixmap.width() - 1) if axis == "x" else max(1, self._pixmap.height() - 1)
        if index < 0 or index >= len(guides):
            return
        guides[index] = max(1, min(limit, int(value)))
        guides.sort()
        self.guidesChanged.emit(list(self._x_guides), list(self._y_guides))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#101723"))
        if self._pixmap.isNull():
            painter.setPen(QColor("#d8e1ea"))
            painter.drawText(self.rect(), Qt.AlignCenter, "预览不可用")
            return

        target_rect = self._target_rect()
        painter.drawPixmap(target_rect, self._pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        x_scale, y_scale = self._scale_factors(target_rect)
        vertical_pen = QPen(QColor("#5bb6ff"), 2)
        horizontal_pen = QPen(QColor("#ff8a5b"), 2)

        for index, x in enumerate(self._x_guides):
            painter.setPen(self._guide_pen("x", index, vertical_pen))
            draw_x = round(target_rect.left() + x * x_scale)
            painter.drawLine(draw_x, target_rect.top(), draw_x, target_rect.bottom())
        for index, y in enumerate(self._y_guides):
            painter.setPen(self._guide_pen("y", index, horizontal_pen))
            draw_y = round(target_rect.top() + y * y_scale)
            painter.drawLine(target_rect.left(), draw_y, target_rect.right(), draw_y)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        axis, index = self._hit_test(event.pos())
        self._selected_axis = axis
        self._selected_index = index
        self._dragging = axis is not None and index >= 0
        self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if not self._dragging or self._selected_axis is None or self._selected_index < 0:
            return
        image_x, image_y = self._widget_to_image(event.pos())
        if self._selected_axis == "x":
            self.move_guide("x", self._selected_index, image_x)
        else:
            self.move_guide("y", self._selected_index, image_y)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._dragging = False

    def _target_rect(self):
        margin = 16
        area = self.rect().adjusted(margin, margin, -margin, -margin)
        if self._pixmap.isNull():
            return area
        scaled = self._pixmap.scaled(area.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        x = area.left() + (area.width() - scaled.width()) // 2
        y = area.top() + (area.height() - scaled.height()) // 2
        return scaled.rect().translated(x, y)

    def _scale_factors(self, target_rect) -> tuple[float, float]:
        width = max(1, self._pixmap.width())
        height = max(1, self._pixmap.height())
        return target_rect.width() / width, target_rect.height() / height

    def _guide_pen(self, axis: str, index: int, default_pen: QPen) -> QPen:
        if self._selected_axis == axis and self._selected_index == index:
            return QPen(QColor("#f8f871"), 3)
        return default_pen

    def _hit_test(self, pos) -> tuple[str | None, int]:
        target_rect = self._target_rect()
        if self._pixmap.isNull() or not target_rect.contains(pos):
            return None, -1
        x_scale, y_scale = self._scale_factors(target_rect)
        tolerance = 8
        for index, x in enumerate(self._x_guides):
            draw_x = round(target_rect.left() + x * x_scale)
            if abs(pos.x() - draw_x) <= tolerance:
                return "x", index
        for index, y in enumerate(self._y_guides):
            draw_y = round(target_rect.top() + y * y_scale)
            if abs(pos.y() - draw_y) <= tolerance:
                return "y", index
        return None, -1

    def _widget_to_image(self, pos) -> tuple[int, int]:
        target_rect = self._target_rect()
        x_scale, y_scale = self._scale_factors(target_rect)
        image_x = round((pos.x() - target_rect.left()) / max(x_scale, 1e-6))
        image_y = round((pos.y() - target_rect.top()) / max(y_scale, 1e-6))
        return image_x, image_y


class AIEditPage(QWidget):
    def _format_task_timestamp(self, value: str) -> str:
        return _format_task_timestamp(value)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings_store = SettingsStore()
        self.adapter = PosAiImgAdapter()
        self.task_store: TaskStore | None = None
        self.split_profile_store: SplitProfileStore | None = None
        self.process: QProcess | None = None
        self.task_detail_dialog: AIEditTaskDetailDialog | None = None
        self.current_task: AIEditTaskRecord | None = None
        self.tasks: list[AIEditTaskRecord] = []
        self._background_threads: list[QThread] = []
        self._background_workers: list[AIEditBackgroundWorker] = []
        self._stdout_buffer = ""
        self._stderr_buffer = ""
        self._loading_preferences = False
        self.gallery_root = ""
        self.mockup_root = ""
        self.xlsx_root = ""
        self._tasks_file_mtime: float | None = None
        self._dirty_task_ids: set[str] = set()
        self._persist_timer = QTimer(self)
        self._persist_timer.setSingleShot(True)
        self._persist_timer.setInterval(500)
        self._persist_timer.timeout.connect(self._flush_persist)

        self._build_ui()
        self._load_preferences()
        self._load_task_history()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 10, 18)
        root.setSpacing(14)

        header = QFrame()
        header.setObjectName("panel")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 18, 22, 18)
        title = QLabel("AI 改图")
        title.setObjectName("sectionTitle")
        header_layout.addWidget(title)
        root.addWidget(header)

        body = QHBoxLayout()
        body.setSpacing(14)
        self.body_layout = body
        self.config_panel = self._build_config_panel()
        self.task_panel = self._build_task_panel()
        body.addWidget(self.config_panel, 0)
        body.addWidget(self.task_panel, 1)
        root.addLayout(body, stretch=1)
        self._sync_responsive_layout()

    def _build_config_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setMinimumWidth(380)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)

        self.prefix_combo = NoWheelComboBox()
        self.prefix_combo.addItems(["BO", "SZW"])
        self.prefix_combo.currentTextChanged.connect(self._refresh_start_number)
        self.prefix_combo.currentTextChanged.connect(self._save_preferences)

        self.start_spin = NoWheelSpinBox()
        self.start_spin.setRange(1, 999999)
        self.start_spin.valueChanged.connect(self._save_preferences)

        self.total_return_count_spin = NoWheelSpinBox()
        self.total_return_count_spin.setRange(1, 500)
        self.total_return_count_spin.setSuffix(" 轮")
        self.total_return_count_spin.valueChanged.connect(self._save_preferences)

        self.split_collage_check = QCheckBox("自动切割")
        self.split_collage_check.toggled.connect(self._save_preferences)

        self.split_count_spin = NoWheelSpinBox()
        self.split_count_spin.setRange(1, 200)
        self.split_count_spin.valueChanged.connect(self._save_preferences)
        self.split_count_spin.valueChanged.connect(self._update_split_count_hint)
        self.split_count_hint_label = QLabel()

        self.test_mode_check = QCheckBox("测试模式")
        self.test_mode_check.toggled.connect(self._save_preferences)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.addRow("店铺前缀", self.prefix_combo)
        form.addRow("本次对话生成", self.total_return_count_spin)
        form.addRow("起始货号", self.start_spin)
        layout.addLayout(form)

        self.batch_row_layout = QHBoxLayout()
        self.batch_row_layout.addWidget(self.split_collage_check)
        self.batch_row_layout.addWidget(self.test_mode_check)
        layout.addLayout(self.batch_row_layout)

        self.split_row_layout = QHBoxLayout()
        self.split_row_layout.addWidget(self.split_count_spin)
        self.split_row_layout.addWidget(self.split_count_hint_label)
        layout.addLayout(self.split_row_layout)

        self.image_panel = QFrame()
        self.image_panel.setObjectName("subPanel")
        image_layout = QVBoxLayout(self.image_panel)
        image_layout.addWidget(QLabel("参考图片"))
        self.selected_image_path_label = QLabel("--")
        self.selected_image_path_label.setWordWrap(True)
        image_layout.addWidget(self.selected_image_path_label)
        self.image_actions_widget = QWidget()
        image_actions_layout = QHBoxLayout(self.image_actions_widget)
        image_actions_layout.setContentsMargins(0, 0, 0, 0)
        self.clear_images_button = QPushButton("清空参考图")
        self.clear_images_button.setObjectName("ghostButton")
        self.clear_images_button.clicked.connect(self.clear_reference_images)
        self.image_list = QListWidget()
        self.image_list.currentItemChanged.connect(self._on_image_selection_changed)
        image_actions_layout.addWidget(self.clear_images_button)
        image_layout.addWidget(self.image_actions_widget)
        image_layout.addWidget(self.image_list, stretch=1)
        layout.addWidget(self.image_panel)

        self.request_panel = QFrame()
        self.request_panel.setObjectName("subPanel")
        request_layout = QVBoxLayout(self.request_panel)
        request_layout.addWidget(QLabel("改图要求"))
        self.prompt_edit = QTextEdit()
        self.prompt_edit.textChanged.connect(self._save_preferences)
        request_layout.addWidget(self.prompt_edit)
        layout.addWidget(self.request_panel)

        self.config_actions_widget = QWidget()
        actions = QHBoxLayout(self.config_actions_widget)
        actions.setContentsMargins(0, 0, 0, 0)
        self.add_image_button = QPushButton("添加图片")
        self.add_image_button.setObjectName("ghostButton")
        self.add_image_button.clicked.connect(self.add_images)
        self.start_button = QPushButton("开始改图")
        self.start_button.setObjectName("primaryButton")
        self.start_button.clicked.connect(self.start_job)
        self.stop_button = QPushButton("停止任务")
        self.stop_button.setObjectName("ghostButton")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_job)
        actions.addWidget(self.add_image_button)
        actions.addWidget(self.start_button)
        actions.addWidget(self.stop_button)
        layout.addWidget(self.config_actions_widget)
        return panel

    def _build_task_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)

        top = QHBoxLayout()
        self.delete_failed_button = QPushButton("删除失败任务")
        self.delete_failed_button.setObjectName("ghostButton")
        self.delete_failed_button.clicked.connect(self.delete_failed_tasks)
        self.task_sort_combo = NoWheelComboBox()
        self.task_sort_combo.addItems(["按时间（新到旧）", "按时间（旧到新）"])
        self.task_sort_combo.currentTextChanged.connect(self._on_task_sort_changed)
        self.status_label = QLabel("等待启动")
        self.status_label.setObjectName("statusPill")
        top.addWidget(self.delete_failed_button)
        top.addWidget(self.task_sort_combo)
        top.addStretch(1)
        top.addWidget(self.status_label)
        layout.addLayout(top)

        self.task_list = QListWidget()
        self.task_list.itemClicked.connect(self.show_task_detail)
        self.task_list.itemDoubleClicked.connect(self.show_task_detail)
        layout.addWidget(self.task_list, stretch=1)
        return panel

    def _sync_responsive_layout(self) -> None:
        self.image_list.setMinimumHeight(0)
        self.image_actions_widget.setMinimumHeight(0)

    def _load_preferences(self) -> None:
        self._loading_preferences = True
        settings = self.settings_store.load()
        self.gallery_root = settings.posai_gallery_root
        self.mockup_root = settings.posai_mockup_root
        self.xlsx_root = settings.posai_xlsx_root
        self.split_collage_check.setChecked(settings.ai_edit_split_collage)
        self.split_count_spin.setValue(settings.ai_edit_split_count)
        self.total_return_count_spin.setValue(settings.ai_edit_total_return_count)
        self.test_mode_check.setChecked(settings.local_image_test_mode)
        self.prefix_combo.setCurrentText(settings.publish_prefix or "BO")
        self.start_spin.setValue(self._suggest_start_number(self.prefix_combo.currentText(), 1421))
        self.prompt_edit.setPlainText(settings.ai_edit_prompt)
        self._update_split_count_hint(self.split_count_spin.value())
        self.task_store = self._build_task_store(settings.program_data_dir)
        self.split_profile_store = self._build_split_profile_store(settings.program_data_dir)
        self._loading_preferences = False

    def _build_task_store(self, program_data_dir: str) -> TaskStore | None:
        base_dir = (program_data_dir or "").strip()
        if not base_dir:
            return None
        return TaskStore(base_dir, "ai_edit_tasks")

    def _build_split_profile_store(self, program_data_dir: str) -> SplitProfileStore | None:
        base_dir = (program_data_dir or "").strip()
        if not base_dir:
            return None
        return SplitProfileStore(base_dir)

    def _save_preferences(self, *_args) -> None:
        if self._loading_preferences:
            return
        settings = self.settings_store.load()
        settings.publish_prefix = self.prefix_combo.currentText()
        settings.publish_start_number = self.start_spin.value()
        settings.ai_edit_split_collage = self.split_collage_check.isChecked()
        settings.ai_edit_split_count = self.split_count_spin.value()
        settings.ai_edit_total_return_count = self.total_return_count_spin.value()
        settings.local_image_test_mode = self.test_mode_check.isChecked()
        settings.ai_edit_prompt = self.prompt_edit.toPlainText().strip() or settings.ai_edit_prompt
        selected_images = self._selected_images()
        settings.ai_edit_reference_dir = str(selected_images[-1].parent) if selected_images else ""
        self.settings_store.save(settings)

    def _update_split_count_hint(self, value: int) -> None:
        self.split_count_hint_label.setText(_format_split_count_hint(value))

    def _suggest_start_number(self, prefix: str, fallback: int) -> int:
        settings = self.settings_store.load()
        return suggest_next_start(prefix, settings.posai_gallery_root or self.gallery_root or "", fallback)

    def _refresh_start_number(self, prefix: str) -> None:
        if self._loading_preferences:
            return
        fallback = self.start_spin.value() or (1421 if prefix == "BO" else 3113)
        self.start_spin.setValue(self._suggest_start_number(prefix, fallback))

    def add_images(self) -> None:
        settings = self.settings_store.load()
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择参考图片",
            settings.ai_edit_reference_dir or "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        for file_path in files:
            self._add_image_item(file_path)

    def clear_reference_images(self) -> None:
        if self.image_list.count() == 0:
            self.selected_image_path_label.setText("--")
            return
        self.image_list.clear()
        self.selected_image_path_label.setText("--")
        self._save_preferences()

    def _add_image_item(self, image_path: str) -> None:
        path = Path(image_path)
        item = QListWidgetItem(path.name)
        item.setData(Qt.UserRole, str(path))
        item.setToolTip(str(path))
        self.image_list.addItem(item)
        self.image_list.setCurrentItem(item)
        self.selected_image_path_label.setText(str(path))
        self._save_preferences()

    def _on_image_selection_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if current is None:
            self.selected_image_path_label.setText("--")
            return
        self.selected_image_path_label.setText(str(current.data(Qt.UserRole) or "--"))

    def _selected_images(self) -> list[Path]:
        items: list[Path] = []
        for index in range(self.image_list.count()):
            data = self.image_list.item(index).data(Qt.UserRole)
            if data:
                items.append(Path(str(data)))
        return items

    def build_job(self) -> AIEditJob:
        settings = self.settings_store.load()
        provider = settings.default_ai_provider()
        return AIEditJob(
            images=self._selected_images(),
            prompt=self.prompt_edit.toPlainText().strip(),
            api_key=provider.api_key,
            api_base=provider.api_base,
            model=provider.model,
            output_dir=self._build_output_dir(settings),
            size=provider.size,
            split_collage=self.split_collage_check.isChecked(),
            split_count=self.split_count_spin.value(),
            total_return_count=self.total_return_count_spin.value(),
            prefix=self.prefix_combo.currentText(),
            start_number=self.start_spin.value(),
            test_mode=self.test_mode_check.isChecked(),
            gallery_root=self.gallery_root,
            mockup_root=self.mockup_root,
            xlsx_root=self.xlsx_root,
        )

    def _build_output_dir(self, settings: AppSettings) -> Path:
        batch_count = 1 if self.test_mode_check.isChecked() else max(1, self.total_return_count_spin.value())
        batch = build_batch_paths(
            prefix=self.prefix_combo.currentText(),
            start_number=self.start_spin.value(),
            count=batch_count,
            style_name="AI改图",
            gallery_root=settings.posai_gallery_root or self.gallery_root,
            mockup_root=settings.posai_mockup_root or self.mockup_root,
            xlsx_root=settings.posai_xlsx_root or self.xlsx_root,
            stamp=datetime.now().strftime("%Y.%m%d.%H%M.%S"),
        )
        return batch.gallery_batch_dir / "临时输出"

    def _set_process_env(self, process: QProcess) -> None:
        env = process.processEnvironment()
        env.insert("PYTHONUTF8", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        if self.current_task is not None and self.current_task.job.api_key:
            env.insert("CONSOLEPLAT_AI_IMAGE_API_KEY", self.current_task.job.api_key)
        pythonpath = env.value("PYTHONPATH", "")
        user_site = site.getusersitepackages()
        if user_site and user_site not in pythonpath:
            pythonpath = os.pathsep.join([part for part in [pythonpath, user_site] if part])
        env.insert("PYTHONPATH", pythonpath)
        process.setProcessEnvironment(env)

    def _load_split_profile_for_job(self, job: AIEditJob) -> dict[str, object]:
        fallback = _default_split_profile(job.split_count)
        if self.split_profile_store is None or not job.images:
            return fallback
        profile = self.split_profile_store.load(str(job.images[0]))
        return fallback if profile is None else {
            "source_image": profile.source_image,
            "split_count": profile.split_count,
            "columns": profile.columns,
            "rows": profile.rows,
            "x_guides": list(profile.x_guides or []),
            "y_guides": list(profile.y_guides or []),
            "updated_at": profile.updated_at,
        }

    def _create_task_record(self, job: AIEditJob) -> AIEditTaskRecord:
        batch_count = 1 if job.test_mode else max(1, job.total_return_count)
        batch = build_batch_paths(
            prefix=job.prefix,
            start_number=job.start_number,
            count=batch_count,
            style_name="AI改图",
            gallery_root=job.gallery_root,
            mockup_root=job.mockup_root,
            xlsx_root=job.xlsx_root,
            stamp=datetime.now().strftime("%Y.%m%d.%H%M.%S"),
        )
        record = AIEditTaskRecord(
            task_id=datetime.now().strftime("%Y%m%d%H%M%S"),
            title=f"AI 改图 {job.prefix}-{job.start_number}\n{job.total_return_count} 轮 · {('测试模式' if job.test_mode else '正式模式')}",
            job=job,
            output_dir=str(batch.gallery_batch_dir),
            final_transparent_dir=str(batch.gallery_final_dir),
            final_product_dir=str(batch.mockup_final_dir),
            xlsx_path=str(batch.xlsx_path),
            split_profile=self._load_split_profile_for_job(job),
        )
        self.tasks.append(record)
        self._rebuild_task_list()
        self._save_task_history()
        self._refresh_task_detail_dialog()
        return record

    def start_job(self) -> None:
        if self.process is not None:
            return
        job = self.build_job()
        if not job.images:
            self.status_label.setText("请先添加参考图")
            return
        if not job.prompt:
            self.status_label.setText("请先填写改图要求")
            return
        if not job.api_key:
            self.status_label.setText("请先配置 API Key")
            return
        self.current_task = self._create_task_record(job)
        self._append_log(f"启动任务：{self.current_task.title}")
        self._append_log(f"当前 AI 接口：{job.api_base}")
        program, args, cwd = self.adapter.ai_edit_command(job)
        process = QProcess(self)
        process.setProgram(program)
        process.setArguments(args)
        process.setWorkingDirectory(str(cwd))
        process.readyReadStandardOutput.connect(self._read_stdout)
        process.readyReadStandardError.connect(self._read_stderr)
        process.finished.connect(self._on_process_finished)
        process.errorOccurred.connect(self._on_process_error)
        self.process = process
        self._stdout_buffer = ""
        self._stderr_buffer = ""
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("运行中")
        self._update_current_task(status="运行中", stage_text="准备启动", progress_percent=5)
        self._set_process_env(process)
        process.start()

    def stop_job(self) -> None:
        if self.process is None:
            return
        self._append_log("正在停止任务...")
        self.process.kill()

    def _read_stdout(self) -> None:
        if self.process is None:
            return
        text = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._stdout_buffer += text
        self._append_log(text.rstrip())

    def _read_stderr(self) -> None:
        if self.process is None:
            return
        text = bytes(self.process.readAllStandardError()).decode("utf-8", errors="replace")
        self._stderr_buffer += text
        self._append_log(text.rstrip())

    def _on_process_finished(self, exit_code: int, _exit_status) -> None:
        if self.process is None or self.current_task is None:
            return
        stdout = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        stderr = bytes(self.process.readAllStandardError()).decode("utf-8", errors="replace")
        if stdout.strip():
            self._stdout_buffer += stdout
            self._append_log(stdout.rstrip())
        if stderr.strip():
            self._stderr_buffer += stderr
            self._append_log(stderr.rstrip())
        self.process = None
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        summary = self.adapter.parse_ai_edit_result(self._stdout_buffer)
        self._finalize_task(summary, exit_code)
        return
        self._update_current_task(
            status="完成" if summary.ok and exit_code == 0 else "失败",
            stage_text="已完成" if summary.ok and exit_code == 0 else "失败",
            progress_percent=100 if summary.ok and exit_code == 0 else 0,
            output_dir=summary.output_dir or self.current_task.output_dir,
        )
        self.current_task.outputs = list(summary.outputs or [])
        self.current_task.failed = list(summary.failed or [])
        self.current_task.warnings = list(summary.warnings or [])
        self.current_task.round_sources = self._derive_round_sources_from_outputs(self.current_task.outputs)
        self.status_label.setText(self.current_task.status)
        self._save_task_history()
        self._append_log(summary.message)

    def _on_process_error(self, error) -> None:
        self.process = None
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("启动失败")
        self._update_current_task(status="启动失败", stage_text="启动失败", progress_percent=0)
        self._append_log(f"AI 改图进程启动失败：{error}")

    def _finalize_task(self, summary, exit_code: int) -> None:
        if self.current_task is None:
            return
        is_ok = bool(summary.ok and exit_code == 0)
        self._update_current_task(
            status="完成" if is_ok else "失败",
            stage_text="已完成" if is_ok else "失败",
            progress_percent=100 if is_ok else 0,
            output_dir=summary.output_dir or self.current_task.output_dir,
        )
        self.current_task.outputs = list(summary.outputs or self.current_task.outputs)
        self.current_task.failed = list(summary.failed or [])
        self.current_task.warnings = list(summary.warnings or [])
        self.current_task.round_sources = self._derive_round_sources_from_outputs(self.current_task.outputs)
        if is_ok:
            self._append_log("开始后台处理 AI 改图结果...")
            self._start_post_process_job(self.current_task)
        self.status_label.setText(self.current_task.status)
        self._save_task_history()
        self._append_log(summary.message)

    def _start_post_process_job(self, record: AIEditTaskRecord) -> None:
        self._start_background_job("post_process", record)

    def _start_background_job(self, action: str, record: AIEditTaskRecord) -> None:
        thread = QThread(self)
        worker = AIEditBackgroundWorker(action, record, self.settings_store.load())
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.log_message.connect(self._append_task_log)
        worker.finished.connect(self._on_background_job_finished)
        worker.failed.connect(self._on_background_job_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._cleanup_background_job(thread, worker))
        self._background_threads.append(thread)
        self._background_workers.append(worker)
        thread.start()

    def _cleanup_background_job(self, thread: QThread, worker: AIEditBackgroundWorker) -> None:
        self._background_threads = [item for item in self._background_threads if item is not thread]
        self._background_workers = [item for item in self._background_workers if item is not worker]

    def _find_task_by_id(self, task_id: str) -> AIEditTaskRecord | None:
        for record in self.tasks:
            if record.task_id == task_id:
                return record
        return None

    def _append_task_log(self, task_id: str, text: str) -> None:
        record = self._find_task_by_id(task_id)
        if record is None and self.current_task is not None and self.current_task.task_id == task_id:
            record = self.current_task
        if record is None:
            return
        self._append_log_to_record(record, text)
        self.status_label.setText(record.status)

    def _on_background_job_finished(self, result: BackgroundTaskResult) -> None:
        record = self._find_task_by_id(result.task_id)
        if record is None:
            return
        if result.outputs:
            record.outputs = list(result.outputs)
        if result.round_sources and result.action != "split_current_round":
            record.round_sources = list(result.round_sources)
        if result.final_transparent_dir:
            record.final_transparent_dir = result.final_transparent_dir
        if result.final_product_dir:
            record.final_product_dir = result.final_product_dir
        if result.xlsx_path:
            record.xlsx_path = result.xlsx_path
        if result.failed:
            record.failed = list(record.failed) + list(result.failed)
            record.status = "失败"
            record.stage_text = "失败"
        if result.warnings:
            record.warnings = list(record.warnings) + list(result.warnings)
        if result.action == "split_current_round":
            source_path = result.round_sources[0] if result.round_sources else ""
            final_outputs = self._copy_split_outputs_to_final_gallery(
                record,
                [Path(path) for path in result.outputs or record.outputs],
                start_number=self._start_number_for_round_source(record, source_path),
            )
            if final_outputs:
                record.outputs = [str(path) for path in final_outputs]
        for line in result.logs:
            self._append_log(line)
        self.status_label.setText(record.status)
        self._save_task_history()
        self._refresh_task_detail_dialog()

    def _on_background_job_failed(self, action: str, task_id: str, error_text: str) -> None:
        record = self._find_task_by_id(task_id)
        if record is None:
            return
        record.failed = list(record.failed) + [error_text]
        record.status = "失败"
        record.stage_text = "失败"
        self.status_label.setText(record.status)
        self._append_log(f"{action} 后台任务失败：{error_text}")
        self._save_task_history()
        self._refresh_task_detail_dialog()

    def _run_prepare_post_process(self) -> None:
        if self.current_task is None:
            return
        prepared_assets = prepare_ai_edit_print_assets(
            source_paths=self._derive_round_sources_from_outputs(self.current_task.outputs),
            final_transparent_dir=self.current_task.final_transparent_dir or self.current_task.output_dir,
            prefix=self.current_task.job.prefix,
            start_number=self.current_task.job.start_number,
            split_collage=self.current_task.job.split_collage,
            split_count=self.current_task.job.split_count,
            x_guides=list(self.current_task.split_profile.get("x_guides") or []),
            y_guides=list(self.current_task.split_profile.get("y_guides") or []),
            drop_first_split=bool(self.settings_store.load().ai_edit_drop_first_per_round),
        )
        prepared_paths = [path for asset in prepared_assets for path in asset.split_paths]
        if not prepared_paths:
            return
        self.current_task.outputs = [str(path) for path in prepared_paths]
        transparent_rounds = [str(asset.transparent_path) for asset in prepared_assets if asset.transparent_path]
        if transparent_rounds:
            self.current_task.round_sources = transparent_rounds
        self.current_task.final_transparent_dir = str(Path(prepared_paths[0]).parent)

    def _run_formalize_post_process(self) -> None:
        if self.current_task is None:
            return
        settings = self.settings_store.load()
        product_title = (
            settings.bo_product_title.strip()
            if self.current_task.job.prefix == "BO"
            else settings.szw_product_title.strip()
        )
        split_paths = self._collect_formalize_input_paths()
        if not split_paths:
            self._update_current_task(status="失败", stage_text="后处理失败", progress_percent=0)
            self.current_task.failed = list(self.current_task.failed) + ["未找到可正式入库的切图产物"]
            self._append_log("正式模式后处理失败：未找到可正式入库的切图产物")
            return
        try:
            formalize_summary = formalize_ai_edit_outputs(
                split_paths=split_paths,
                final_transparent_dir=Path(self.current_task.final_transparent_dir),
                final_product_dir=Path(self.current_task.final_product_dir),
                xlsx_path=Path(self.current_task.xlsx_path),
                putaway_data_dir=Path(settings.putaway_data_dir),
                model_dir=Path(settings.posai_model_root),
                prefix=self.current_task.job.prefix,
                start_number=self.current_task.job.start_number,
                product_title=product_title,
                xlsx_batch_start_number=self.current_task.job.start_number,
                xlsx_batch_count=max(1, len(split_paths)),
                saturation_threshold=settings.ai_edit_grayscale_saturation_threshold,
            )
        except Exception as exc:
            self._update_current_task(status="失败", stage_text="后处理失败", progress_percent=0)
            self.current_task.failed = list(self.current_task.failed) + [str(exc)]
            self._append_log(f"正式模式后处理失败：{exc}")
            return
        if not formalize_summary.ok:
            self._update_current_task(status="失败", stage_text="后处理失败", progress_percent=0)
            if formalize_summary.putaway and formalize_summary.putaway.message:
                self.current_task.warnings = list(self.current_task.warnings) + [formalize_summary.putaway.message]
            self._append_log(formalize_summary.message)
            return
        self.current_task.xlsx_path = formalize_summary.xlsx_path or self.current_task.xlsx_path
        self.current_task.outputs = list(formalize_summary.product_outputs or self.current_task.outputs)
        self.current_task.round_sources = list(formalize_summary.renamed_outputs or self.current_task.round_sources)
        if formalize_summary.putaway and formalize_summary.putaway.message:
            self.current_task.warnings = list(self.current_task.warnings) + [formalize_summary.putaway.message]
        self._append_log(formalize_summary.message)

    def _collect_formalize_input_paths(self) -> list[Path]:
        if self.current_task is None:
            return []
        png_paths = [Path(path) for path in self.current_task.outputs if Path(path).suffix.lower() == ".png"]
        split_paths = [path for path in png_paths if "_part_" in path.stem.lower()]
        if split_paths:
            return split_paths
        return png_paths

    def _prepare_formalize_input_paths(self) -> list[Path]:
        if self.current_task is None:
            return []
        prepared: list[Path] = []
        sources = self._derive_round_sources_from_outputs(self.current_task.outputs)
        for source_text in sources:
            source = Path(source_text)
            if source.suffix.lower() != ".png" or not source.exists():
                continue
            source_for_split = source
            if "transparent" not in source.stem.lower():
                source_for_split = Path(convert_image_to_transparent_background(source))
                prepared.append(source_for_split)
            if self.current_task.job.split_collage:
                split_output_dir = self._build_output_path_for_source(str(source_for_split))
                split_results = [
                    Path(path)
                    for path in split_collage_image_with_guides(
                        source_for_split,
                        split_output_dir,
                        self.current_task.job.split_count,
                        list(self.current_task.split_profile.get("x_guides") or []),
                        list(self.current_task.split_profile.get("y_guides") or []),
                    )
                ]
                prepared.extend(split_results)
            else:
                prepared.append(source_for_split)
        unique: list[Path] = []
        seen: set[str] = set()
        for path in prepared:
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            unique.append(path)
        return unique

    def _derive_round_sources_from_outputs(self, outputs: list[str]) -> list[str]:
        non_split = [path for path in outputs if Path(path).suffix.lower() == ".png" and "_part_" not in Path(path).stem.lower()]
        return non_split or [path for path in outputs if Path(path).suffix.lower() == ".png"]

    def _append_log(self, text: str) -> None:
        if not text or self.current_task is None:
            return
        self._append_log_to_record(self.current_task, text)

    def _append_log_to_record(self, record: AIEditTaskRecord, text: str) -> None:
        if not text:
            return
        time_text = datetime.now().strftime("%H:%M:%S")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                record.logs.append(f"{time_text}  {stripped}")
                progress = _progress_from_text(stripped)
                if progress is not None:
                    record.progress_percent = progress
        self._touch_task(record)
        self._refresh_task_detail_dialog()

    def _update_current_task(
        self,
        *,
        status: str,
        stage_text: str,
        progress_percent: int,
        output_dir: str | None = None,
    ) -> None:
        if self.current_task is None:
            return
        self.current_task.status = status
        self.current_task.stage_text = stage_text
        self.current_task.progress_percent = progress_percent
        if output_dir:
            self.current_task.output_dir = output_dir
        self._touch_task(self.current_task)
        self._refresh_task_detail_dialog()

    def _build_output_path_for_source(self, source_path: str) -> Path:
        source = Path(source_path)
        return source.parent / f"{source.stem}_split"

    def _copy_split_outputs_to_final_gallery(
        self,
        record: AIEditTaskRecord,
        split_paths: list[Path],
        *,
        start_number: int | None = None,
    ) -> list[Path]:
        split_paths = [path for path in split_paths if "_part_" in path.stem.lower()]
        if not split_paths:
            return []
        target_root = Path(record.final_transparent_dir) if record.final_transparent_dir else Path(record.output_dir)
        target_root.mkdir(parents=True, exist_ok=True)
        outputs: list[Path] = []
        current_number = int(start_number if start_number is not None else record.job.start_number)
        for source in split_paths:
            target = target_root / f"{record.job.prefix}-{current_number}.png"
            target.write_bytes(source.read_bytes())
            outputs.append(target)
            current_number += 1
        if record.final_transparent_dir:
            record.final_transparent_dir = str(target_root)
        elif not record.final_transparent_dir:
            record.final_transparent_dir = str(target_root)
        return outputs

    def _image_files_in_dir(self, folder: Path) -> list[Path]:
        if not folder.exists() or not folder.is_dir():
            return []
        return sorted(
            [path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES],
            key=lambda path: path.name.lower(),
        )

    def export_task_product_images(self, record: AIEditTaskRecord) -> None:
        final_transparent_dir = Path(record.final_transparent_dir) if record.final_transparent_dir else None
        if final_transparent_dir is None or not final_transparent_dir.exists():
            self._append_task_log(record.task_id, f"导出产品图失败：最终透明底目录不存在 {record.final_transparent_dir or '--'}")
            return
        if not any(path.is_file() and path.suffix.lower() == ".png" for path in final_transparent_dir.iterdir()):
            self._append_task_log(record.task_id, f"导出产品图失败：最终透明底目录为空 {final_transparent_dir}")
            return
        final_product_dir = Path(record.final_product_dir) if record.final_product_dir else None
        if final_product_dir is None:
            self._append_task_log(record.task_id, f"导出产品图失败：最终产品图目录不存在 {record.final_product_dir or '--'}")
            return
        if not record.xlsx_path or not Path(record.xlsx_path).exists():
            self._append_task_log(record.task_id, f"导出产品图失败：XLSX 不存在 {record.xlsx_path or '--'}")
            return
        self._append_task_log(record.task_id, f"开始后台重贴产品图：目标目录 {final_product_dir}")
        self._start_background_job("export_product_images", record)

    def export_task_xlsx(self, record: AIEditTaskRecord) -> None:
        source_path = Path(record.xlsx_path) if record.xlsx_path else None
        if source_path is None or not source_path.exists():
            self._append_log(f"导出 xlsx 失败：XLSX 不存在 {record.xlsx_path or '--'}")
            return
        target_dir = Path(record.output_dir) / "导出xlsx"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / source_path.name
        replaced = target_path.exists()
        shutil.copy2(source_path, target_path)
        replace_text = "，已覆盖同名文件" if replaced else ""
        self._append_log(f"已导出 xlsx 到 {target_path}{replace_text}")
        self._refresh_task_detail_dialog()

    def sync_task_to_putaway_data(self, record: AIEditTaskRecord) -> None:
        source_images_dir = Path(record.final_product_dir) if record.final_product_dir else None
        source_xlsx_path = Path(record.xlsx_path) if record.xlsx_path else None
        settings = self.settings_store.load()
        if source_images_dir is None or not source_images_dir.exists():
            message = f"同步到上架 data 失败：最终产品图目录不存在 {record.final_product_dir or '--'}"
            record.failed = list(record.failed) + [message]
            self._append_log(message)
            self._save_task_history()
            self._refresh_task_detail_dialog()
            return
        if source_xlsx_path is None or not source_xlsx_path.exists():
            message = f"同步到上架 data 失败：XLSX 不存在 {record.xlsx_path or '--'}"
            record.failed = list(record.failed) + [message]
            self._append_log(message)
            self._save_task_history()
            self._refresh_task_detail_dialog()
            return
        summary = sync_putaway_assets(
            source_images_dir=source_images_dir,
            source_xlsx_path=source_xlsx_path,
            target_data_dir=Path(settings.putaway_data_dir),
            force_replace=True,
        )
        if not summary.ok:
            record.failed = list(record.failed) + [summary.message]
            self._append_log(f"同步到上架 data 失败：{summary.message}")
        else:
            self._append_log(
                f"已同步到上架 data：图片目录 {summary.images_target_dir}，XLSX {summary.xlsx_target_path}"
            )
        self._save_task_history()
        self._refresh_task_detail_dialog()

    def _replace_split_outputs(self, record: AIEditTaskRecord, source_path: str, new_split_paths: list[str]) -> None:
        if source_path not in record.outputs:
            record.outputs = list(record.outputs) + list(new_split_paths)
            return
        index = record.outputs.index(source_path)
        existing = [path for path in record.outputs if path not in new_split_paths]
        record.outputs = existing[: index + 1] + list(new_split_paths) + existing[index + 1 :]

    def _round_source_index(self, record: AIEditTaskRecord, source_path: str) -> int:
        if not source_path:
            return 0
        source_key = _path_key(source_path)
        recovered_round_sources = _legacy_round_sources_from_batch_dirs(
            output_dir=record.output_dir,
            final_transparent_dir=record.final_transparent_dir,
        )
        source_groups = []
        if len(recovered_round_sources) >= _expected_round_count(record):
            source_groups.append(recovered_round_sources)
        source_groups.append(record.round_sources)
        for sources in source_groups:
            for index, candidate in enumerate(sources):
                if _path_key(candidate) == source_key:
                    return index
        inferred_index = _round_index_from_source_name(source_path)
        if inferred_index is not None:
            return inferred_index
        return 0

    def _effective_count_per_round(self, record: AIEditTaskRecord) -> int:
        split_count = max(1, int(record.job.split_count or 1))
        if (
            record.job.split_collage
            and self.settings_store.load().ai_edit_drop_first_per_round
            and split_count > 1
        ):
            return split_count - 1
        return split_count

    def _start_number_for_round_source(self, record: AIEditTaskRecord, source_path: str) -> int:
        effective_count = self._effective_count_per_round(record)
        return int(record.job.start_number) + self._round_source_index(record, source_path) * effective_count

    def _background_record_for_current_round(self, record: AIEditTaskRecord, source_path: str) -> AIEditTaskRecord:
        current_record = copy.deepcopy(record)
        current_record.round_sources = [source_path]
        current_record.active_round_index = 0
        current_record.job = replace(
            current_record.job,
            start_number=self._start_number_for_round_source(record, source_path),
        )
        return current_record

    def convert_current_round(self, record: AIEditTaskRecord, source_path: str) -> None:
        if not source_path:
            return
        self._append_log("开始后台转透明底...")
        self._start_background_job("convert_current_round", self._background_record_for_current_round(record, source_path))

    def split_current_round(self, record: AIEditTaskRecord, source_path: str) -> None:
        if not source_path:
            return
        self._append_log("开始后台切割当前轮...")
        self._start_background_job("split_current_round", self._background_record_for_current_round(record, source_path))

    def _find_original_round_source(self, record: AIEditTaskRecord, source_path: str) -> str | None:
        source = Path(source_path)
        candidate_name = source.stem.replace("_transparent", "")
        candidate = source.with_name(f"{candidate_name}{source.suffix}")
        if candidate.exists():
            return str(candidate)
        for output in record.outputs:
            output_path = Path(output)
            if output_path == source:
                continue
            if output_path.stem == candidate_name and output_path.suffix.lower() == source.suffix.lower() and output_path.exists():
                return str(output_path)
        return None

    def edit_split_profile(self, record: AIEditTaskRecord, source_path: str) -> None:
        if self.split_profile_store is None or not source_path:
            return
        columns, rows = _best_grid_for_count(record.job.split_count)
        dialog = SplitProfileEditorDialog(record, source_path, self)
        if dialog.exec_() != QDialog.Accepted:
            return
        x_guides, y_guides = dialog.parsed_guides()
        profile = SplitProfile(
            source_image=source_path,
            split_count=record.job.split_count,
            columns=columns,
            rows=rows,
            x_guides=x_guides,
            y_guides=y_guides,
            updated_at=datetime.now().isoformat(timespec="seconds"),
        )
        self.split_profile_store.save(profile)
        record.split_profile = {
            "x_guides": list(profile.x_guides or []),
            "y_guides": list(profile.y_guides or []),
            "split_count": profile.split_count,
            "columns": profile.columns,
            "rows": profile.rows,
            "updated_at": profile.updated_at,
        }
        self.split_current_round(record, source_path)
        record.split_profile = {
            "source_image": profile.source_image,
            "split_count": profile.split_count,
            "columns": profile.columns,
            "rows": profile.rows,
            "x_guides": profile.x_guides,
            "y_guides": profile.y_guides,
            "updated_at": profile.updated_at,
        }
        self._save_task_history()

    def show_task_detail(self, item: QListWidgetItem) -> None:
        index = self.task_list.row(item)
        ordered_tasks = self._ordered_tasks()
        if index < 0 or index >= len(ordered_tasks):
            return
        record = ordered_tasks[index]
        self._start_background_job("backfill_colors", record)
        dialog = AIEditTaskDetailDialog(record, self)
        self.task_detail_dialog = dialog
        dialog.exec_()
        if self.task_detail_dialog is dialog:
            self.task_detail_dialog = None

    def delete_failed_tasks(self) -> None:
        self.tasks = [record for record in self.tasks if record.status != "失败"]
        self._rebuild_task_list()
        self._save_task_history()

    def _ordered_tasks(self) -> list[AIEditTaskRecord]:
        reverse = self.task_sort_combo.currentText() != "按时间（旧到新）" if hasattr(self, "task_sort_combo") else True
        return sorted(self.tasks, key=lambda record: record.task_id, reverse=reverse)

    def _rebuild_task_list(self) -> None:
        self.task_list.clear()
        for record in self._ordered_tasks():
            item = QListWidgetItem(
                f"{_format_task_timestamp(record.task_id)}  {record.title}\n"
                f"{record.status} · {record.stage_text} {record.progress_percent}%"
            )
            item.setData(Qt.UserRole, record.task_id)
            self.task_list.addItem(item)

    def _refresh_task_item(self, record: AIEditTaskRecord) -> None:
        item = self._task_item(record)
        if item is None:
            self._rebuild_task_list()
            return
        item.setText(
            f"{_format_task_timestamp(record.task_id)}  {record.title}\n"
            f"{record.status} · {record.stage_text} {record.progress_percent}%"
        )

    def _task_item(self, record: AIEditTaskRecord) -> QListWidgetItem | None:
        for index in range(self.task_list.count()):
            item = self.task_list.item(index)
            if item is not None and item.data(Qt.UserRole) == record.task_id:
                return item
        return None

    def _touch_task(self, record: AIEditTaskRecord | None) -> None:
        if record is None:
            return
        self._dirty_task_ids.add(record.task_id)
        self._refresh_task_item(record)
        self._persist_timer.start()

    def _flush_persist(self) -> None:
        if not self._dirty_task_ids and self.task_store is not None:
            return
        self._persist_timer.stop()
        self._dirty_task_ids.clear()
        self._save_task_history()
        self._remember_tasks_file_mtime()

    def _on_task_sort_changed(self, _text: str) -> None:
        self._rebuild_task_list()

    def _refresh_task_detail_dialog(self) -> None:
        if self.task_detail_dialog is not None:
            record = self._find_task_by_id(self.task_detail_dialog.record.task_id)
            if (
                record is None
                and self.current_task is not None
                and self.current_task.task_id == self.task_detail_dialog.record.task_id
            ):
                record = self.current_task
            if record is not None:
                self.task_detail_dialog.refresh(record)

    def _task_to_dict(self, record: AIEditTaskRecord) -> dict:
        return {
            "task_id": record.task_id,
            "title": record.title,
            "status": record.status,
            "stage_text": record.stage_text,
            "progress_percent": record.progress_percent,
            "logs": list(record.logs),
            "output_dir": record.output_dir,
            "outputs": list(record.outputs),
            "failed": list(record.failed),
            "warnings": list(record.warnings),
            "round_sources": list(record.round_sources),
            "collage_transparent_sources": list(record.collage_transparent_sources),
            "active_round_index": int(record.active_round_index or 0),
            "final_transparent_dir": record.final_transparent_dir,
            "final_product_dir": record.final_product_dir,
            "xlsx_path": record.xlsx_path,
            "split_profile": dict(record.split_profile),
            "job": {
                "images": [str(path) for path in record.job.images],
                "prompt": record.job.prompt,
                "api_key": "",
                "api_base": record.job.api_base,
                "model": record.job.model,
                "output_dir": str(record.job.output_dir or record.output_dir),
                "size": record.job.size,
                "split_collage": record.job.split_collage,
                "split_count": record.job.split_count,
                "total_return_count": record.job.total_return_count,
                "prefix": record.job.prefix,
                "start_number": record.job.start_number,
                "test_mode": record.job.test_mode,
                "gallery_root": record.job.gallery_root,
                "mockup_root": record.job.mockup_root,
                "xlsx_root": record.job.xlsx_root,
            },
        }

    def _task_from_dict(self, payload: dict) -> AIEditTaskRecord | None:
        job_payload = payload.get("job") or {}
        if not isinstance(job_payload, dict):
            return None
        record = AIEditTaskRecord(
            task_id=str(payload.get("task_id") or ""),
            title=str(payload.get("title") or "AI 改图"),
            job=AIEditJob(
                images=[Path(str(path)) for path in (job_payload.get("images") or [])],
                prompt=str(job_payload.get("prompt") or ""),
                api_key="",
                api_base=str(job_payload.get("api_base") or "https://api.openai.com/v1"),
                model=str(job_payload.get("model") or "gpt-image-2"),
                output_dir=Path(str(job_payload.get("output_dir") or "")) if str(job_payload.get("output_dir") or "") else None,
                size=str(job_payload.get("size") or "1024x1024"),
                split_collage=bool(job_payload.get("split_collage", True)),
                split_count=max(1, int(job_payload.get("split_count") or 10)),
                total_return_count=max(1, int(job_payload.get("total_return_count") or 1)),
                prefix=str(job_payload.get("prefix") or "BO"),
                start_number=int(job_payload.get("start_number") or 1421),
                test_mode=bool(job_payload.get("test_mode", True)),
                gallery_root=str(job_payload.get("gallery_root") or ""),
                mockup_root=str(job_payload.get("mockup_root") or ""),
                xlsx_root=str(job_payload.get("xlsx_root") or ""),
            ),
            status=str(payload.get("status") or "已恢复"),
            stage_text=str(payload.get("stage_text") or "已恢复"),
            progress_percent=max(0, min(100, int(payload.get("progress_percent") or 0))),
            logs=[str(line) for line in (payload.get("logs") or [])],
            output_dir=str(payload.get("output_dir") or ""),
            outputs=[str(path) for path in (payload.get("outputs") or [])],
            failed=[str(path) for path in (payload.get("failed") or [])],
            warnings=[str(path) for path in (payload.get("warnings") or [])],
            round_sources=[str(path) for path in (payload.get("round_sources") or [])],
            collage_transparent_sources=[str(path) for path in (payload.get("collage_transparent_sources") or [])],
            active_round_index=max(0, int(payload.get("active_round_index") or 0)),
            final_transparent_dir=str(payload.get("final_transparent_dir") or ""),
            final_product_dir=str(payload.get("final_product_dir") or ""),
            xlsx_path=str(payload.get("xlsx_path") or ""),
            split_profile=dict(payload.get("split_profile") or {}),
        )
        if record.collage_transparent_sources and not record.round_sources:
            record.round_sources = list(record.collage_transparent_sources)
        recovered_round_sources = _legacy_round_sources_from_batch_dirs(
            output_dir=record.output_dir,
            final_transparent_dir=record.final_transparent_dir,
        )
        expected_round_count = _expected_round_count(record)
        if not record.round_sources:
            record.round_sources = recovered_round_sources
        elif len(record.round_sources) < expected_round_count and len(recovered_round_sources) >= expected_round_count:
            record.round_sources = recovered_round_sources
        elif _looks_like_final_transparent_round_sources(record.round_sources, record.final_transparent_dir):
            record.round_sources = recovered_round_sources or record.round_sources
        return record

    def _save_task_history(self) -> None:
        if self.task_store is None:
            return
        self.task_store.save([self._task_to_dict(record) for record in self.tasks])

    def _load_task_history(self) -> None:
        if self.task_store is None:
            return
        for payload in self.task_store.load():
            record = self._task_from_dict(payload)
            if record is None:
                continue
            self.tasks.append(record)
        self._rebuild_task_list()
        self._remember_tasks_file_mtime()

    def reload_tasks_from_store(self, *, force: bool = False) -> None:
        if self.task_store is None:
            return
        current_mtime = self._current_tasks_file_mtime()
        if not force and current_mtime == self._tasks_file_mtime:
            return
        current_task = self.current_task
        current_task_id = current_task.task_id if current_task is not None else ""
        records: list[AIEditTaskRecord] = []
        seen_task_ids: set[str] = set()
        for payload in self.task_store.load():
            record = self._task_from_dict(payload)
            if record is None:
                continue
            if current_task is not None and record.task_id == current_task_id:
                records.append(current_task)
            else:
                records.append(record)
            seen_task_ids.add(record.task_id)
        if current_task is not None and current_task_id and current_task_id not in seen_task_ids:
            records.append(current_task)
        self.tasks = records
        self._rebuild_task_list()
        self._tasks_file_mtime = current_mtime

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.reload_tasks_from_store()

    def _current_tasks_file_mtime(self) -> float | None:
        if self.task_store is None or not self.task_store.path.exists():
            return None
        return self.task_store.path.stat().st_mtime

    def _remember_tasks_file_mtime(self) -> None:
        self._tasks_file_mtime = self._current_tasks_file_mtime()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._flush_persist()
        if self.process is not None:
            kill = getattr(self.process, "kill", None)
            if kill is not None:
                kill()
            wait_for_finished = getattr(self.process, "waitForFinished", None)
            if wait_for_finished is not None:
                wait_for_finished(1500)
            self.process = None
        for thread in list(self._background_threads):
            thread.quit()
            thread.wait(1500)
        self._background_threads.clear()
        self._background_workers.clear()
        super().closeEvent(event)
