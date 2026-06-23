from __future__ import annotations

import os
import site
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QProcess, Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from consoleplat.adapters.posaiimg_adapter import AIEditJob, PosAiImgAdapter
from consoleplat.config import AppSettings, SettingsStore
from consoleplat.services.ai_edit_formalize_service import (
    backfill_xlsx_colors_from_transparent_dir,
    formalize_ai_edit_outputs,
)
from consoleplat.services.ai_image_edit_cli import convert_image_to_transparent_background, split_collage_image_with_guides
from consoleplat.services.posai_batch_service import build_batch_paths, suggest_next_start
from consoleplat.services.split_profile_store import SplitProfile, SplitProfileStore
from consoleplat.services.task_store import TaskStore


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


def _best_grid_for_count(count: int) -> tuple[int, int]:
    count = max(1, int(count or 1))
    columns = min(5, count)
    rows = (count + columns - 1) // columns
    return columns, rows


def _format_split_count_hint(count: int) -> str:
    columns, rows = _best_grid_for_count(count)
    return f"{max(1, int(count or 1))} 张 ({columns} x {rows})"


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

        self.round_index_label = QLabel()
        self.source_path_label = QLabel("--")
        self.source_path_label.setWordWrap(True)
        layout.addWidget(self.round_index_label)
        layout.addWidget(self.source_path_label)

        nav = QHBoxLayout()
        self.prev_round_button = QPushButton("上一轮")
        self.prev_round_button.clicked.connect(self.show_previous_round)
        self.next_round_button = QPushButton("下一轮")
        self.next_round_button.clicked.connect(self.show_next_round)
        self.convert_transparent_button = QPushButton("转透明底")
        self.convert_transparent_button.clicked.connect(self.convert_current_round)
        self.start_split_button = QPushButton("直接切割")
        self.start_split_button.clicked.connect(self.split_current_round)
        self.open_output_dir_button = QPushButton("打开印花文件夹")
        self.open_output_dir_button.clicked.connect(self.open_output_dir)
        nav.addWidget(self.prev_round_button)
        nav.addWidget(self.next_round_button)
        nav.addWidget(self.convert_transparent_button)
        nav.addWidget(self.start_split_button)
        nav.addWidget(self.open_output_dir_button)
        layout.addLayout(nav)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log, stretch=1)

        self.refresh(record)

    def refresh(self, record: AIEditTaskRecord) -> None:
        self.record = record
        self.meta_label.setText(
            f"状态: {record.status}    前缀: {record.job.prefix}    起始: {record.job.start_number}    轮数: {record.job.total_return_count}"
        )
        self.log.setPlainText("\n".join(record.logs))
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
            return
        self._active_source_index = max(0, min(self._active_source_index, len(sources) - 1))
        self.round_index_label.setText(f"{self._active_source_index + 1}/{len(sources)}")
        self.source_path_label.setText(sources[self._active_source_index])
        self.prev_round_button.setEnabled(self._active_source_index > 0)
        self.next_round_button.setEnabled(self._active_source_index < len(sources) - 1)
        self.convert_transparent_button.setEnabled(True)
        self.start_split_button.setEnabled(True)

    def show_previous_round(self) -> None:
        if self._active_source_index > 0:
            self._active_source_index -= 1
            self._refresh_round_view()

    def show_next_round(self) -> None:
        sources = self._derive_round_sources(self.record)
        if self._active_source_index < len(sources) - 1:
            self._active_source_index += 1
            self._refresh_round_view()

    def open_output_dir(self) -> None:
        path = self.record.final_product_dir or self.record.final_transparent_dir or self.record.output_dir
        if not path:
            return
        try:
            os.startfile(path)  # noqa: S606
        except Exception:
            subprocess.Popen(["explorer", path])

    def convert_current_round(self) -> None:
        if self._page is not None:
            self._page.convert_current_round(self.record, self._find_split_source(self.record))

    def split_current_round(self) -> None:
        if self._page is not None:
            self._page.split_current_round(self.record, self._find_split_source(self.record))


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
        self._stdout_buffer = ""
        self._stderr_buffer = ""
        self._loading_preferences = False
        self.gallery_root = ""
        self.mockup_root = ""
        self.xlsx_root = ""

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
        self.image_list = QListWidget()
        self.image_list.currentItemChanged.connect(self._on_image_selection_changed)
        image_layout.addWidget(self.image_actions_widget)
        image_layout.addWidget(self.image_list, stretch=1)
        layout.addWidget(self.image_panel)

        self.request_panel = QFrame()
        self.request_panel.setObjectName("subPanel")
        request_layout = QVBoxLayout(self.request_panel)
        request_layout.addWidget(QLabel("改图要求"))
        self.prompt_edit = QTextEdit()
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
        settings.ai_edit_split_collage = self.split_collage_check.isChecked()
        settings.ai_edit_split_count = self.split_count_spin.value()
        settings.ai_edit_total_return_count = self.total_return_count_spin.value()
        settings.local_image_test_mode = self.test_mode_check.isChecked()
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

    def _add_image_item(self, image_path: str) -> None:
        path = Path(image_path)
        item = QListWidgetItem(path.name)
        item.setData(Qt.UserRole, str(path))
        item.setToolTip(str(path))
        self.image_list.addItem(item)
        self.image_list.setCurrentItem(item)
        self.selected_image_path_label.setText(str(path))

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
        if self.split_profile_store is None or not job.images:
            return {}
        profile = self.split_profile_store.load(str(job.images[0]))
        return {} if profile is None else {
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
        return record

    def start_job(self) -> None:
        if self.process is not None:
            return
        job = self.build_job()
        if not job.images or not job.prompt:
            return
        self.current_task = self._create_task_record(job)
        self._append_log(f"启动任务：{self.current_task.title}")
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
        if is_ok and not self.current_task.job.test_mode:
            self._run_formalize_post_process()
        self.status_label.setText(self.current_task.status)
        self._save_task_history()
        self._append_log(summary.message)

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
                prefix=self.current_task.job.prefix,
                start_number=self.current_task.job.start_number,
                product_title=product_title,
                xlsx_batch_start_number=self.current_task.job.start_number,
                xlsx_batch_count=max(1, len(split_paths)),
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

    def _derive_round_sources_from_outputs(self, outputs: list[str]) -> list[str]:
        non_split = [path for path in outputs if Path(path).suffix.lower() == ".png" and "_part_" not in Path(path).stem.lower()]
        return non_split or [path for path in outputs if Path(path).suffix.lower() == ".png"]

    def _append_log(self, text: str) -> None:
        if not text or self.current_task is None:
            return
        time_text = datetime.now().strftime("%H:%M:%S")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                self.current_task.logs.append(f"{time_text}  {stripped}")
                progress = _progress_from_text(stripped)
                if progress is not None:
                    self.current_task.progress_percent = progress
        self._save_task_history()

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
        self._rebuild_task_list()
        self._save_task_history()

    def _build_output_path_for_source(self, source_path: str) -> Path:
        source = Path(source_path)
        return source.parent / f"{source.stem}_split"

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
        if record.final_transparent_dir:
            record.final_transparent_dir = str(target_root)
        elif not record.final_transparent_dir:
            record.final_transparent_dir = str(target_root)
        return outputs

    def _replace_split_outputs(self, record: AIEditTaskRecord, source_path: str, new_split_paths: list[str]) -> None:
        if source_path not in record.outputs:
            record.outputs = list(record.outputs) + list(new_split_paths)
            return
        index = record.outputs.index(source_path)
        existing = [path for path in record.outputs if path not in new_split_paths]
        record.outputs = existing[: index + 1] + list(new_split_paths) + existing[index + 1 :]

    def convert_current_round(self, record: AIEditTaskRecord, source_path: str) -> None:
        if not source_path:
            return
        output = convert_image_to_transparent_background(source_path)
        if output not in record.outputs:
            record.outputs.append(output)
        record.round_sources = self._derive_round_sources_from_outputs(record.outputs)
        self._save_task_history()

    def split_current_round(self, record: AIEditTaskRecord, source_path: str) -> None:
        if not source_path:
            return
        output_dir = self._build_output_path_for_source(source_path)
        split_paths = split_collage_image_with_guides(
            source_path,
            output_dir,
            record.job.split_count,
            list(record.split_profile.get("x_guides") or []),
            list(record.split_profile.get("y_guides") or []),
        )
        self._replace_split_outputs(record, source_path, split_paths)
        self._save_task_history()

    def edit_split_profile(self, record: AIEditTaskRecord, source_path: str) -> None:
        if self.split_profile_store is None or not source_path:
            return
        columns, rows = _best_grid_for_count(record.job.split_count)
        profile = SplitProfile(
            source_image=source_path,
            split_count=record.job.split_count,
            columns=columns,
            rows=rows,
            x_guides=[],
            y_guides=[],
            updated_at=datetime.now().isoformat(timespec="seconds"),
        )
        self.split_profile_store.save(profile)
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
            self.task_list.addItem(item)

    def _on_task_sort_changed(self, _text: str) -> None:
        self._rebuild_task_list()

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
        return record

    def _save_task_history(self) -> None:
        if self.task_store is None:
            return
        self.task_store.save([self._task_to_dict(record) for record in self.tasks])

    def _backfill_history_xlsx_colors(self, record: AIEditTaskRecord) -> None:
        xlsx_path = Path(record.xlsx_path) if record.xlsx_path else None
        final_transparent_dir = Path(record.final_transparent_dir) if record.final_transparent_dir else None
        if xlsx_path is None or final_transparent_dir is None:
            return
        try:
            backfill_xlsx_colors_from_transparent_dir(
                xlsx_path=xlsx_path,
                final_transparent_dir=final_transparent_dir,
            )
        except Exception:
            return

    def _load_task_history(self) -> None:
        if self.task_store is None:
            return
        for payload in self.task_store.load():
            record = self._task_from_dict(payload)
            if record is None:
                continue
            self._backfill_history_xlsx_colors(record)
            self.tasks.append(record)
        self._rebuild_task_list()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.process is not None:
            kill = getattr(self.process, "kill", None)
            if kill is not None:
                kill()
            wait_for_finished = getattr(self.process, "waitForFinished", None)
            if wait_for_finished is not None:
                wait_for_finished(1500)
            self.process = None
        super().closeEvent(event)
