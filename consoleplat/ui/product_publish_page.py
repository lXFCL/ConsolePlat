from __future__ import annotations

import os
import re
import shutil
import site
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QProcess, QProcessEnvironment, QTimer, Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from consoleplat.adapters.posaiimg_adapter import AIEditJob, LocalImageJob, PosAiImgAdapter
from consoleplat.adapters.putaway_adapter import PutawayAdapter
from consoleplat.config import AppSettings, DEFAULT_AI_EDIT_PROMPT, SettingsStore
from consoleplat.services.ai_edit_formalize_service import formalize_ai_edit_outputs
from consoleplat.services.comfyui_service import ComfyUIService
from consoleplat.services.posai_batch_service import build_batch_paths, suggest_next_start
from consoleplat.services.publish_orchestrator import PublishStage, StageOrchestrator
from consoleplat.services.putaway_sync_service import IMAGE_SUFFIXES, PutawaySyncSummary, sync_putaway_assets
from consoleplat.services.task_store import TaskStore


PRODUCT_TASK_STATUSES = (
    "draft",
    "confirmed",
    "generating",
    "generated",
    "validating",
    "synced",
    "handoff",
    "failed",
)


@dataclass
class PublishValidationResult:
    ok: bool
    image_count: int = 0
    message: str = ""


@dataclass
class ProductTaskRecord:
    task_id: str
    task_name: str
    prefix: str
    start_number: int
    count: int
    generation_mode: str
    product_title: str
    handoff_mode: str = "同步并唤起"
    test_mode: bool = True
    status: str = "draft"
    stage_text: str = "待确认"
    progress_percent: int = 0
    logs: list[str] = field(default_factory=list)
    output_dir: str = ""
    product_dir: str = ""
    xlsx_path: str = ""
    failure_reason: str = ""
    confirmation_summary: str = ""
    job_payload: dict[str, object] = field(default_factory=dict)


def _format_task_timestamp(value: str) -> str:
    clean = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(clean) >= 14:
        clean = clean[:14]
        return f"{clean[:4]}.{clean[4:8]}.{clean[8:12]}.{clean[12:14]}"
    if len(clean) == 12:
        return f"{clean[:4]}.{clean[4:8]}.{clean[8:12]}"
    return str(value or "")


def _image_files(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(
        [path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES],
        key=lambda path: path.name.lower(),
    )


def _extract_product_numbers(files: list[Path], prefix: str) -> set[int]:
    pattern = re.compile(rf"\b{re.escape(prefix)}[-_]?(\d+)\b", re.IGNORECASE)
    numbers: set[int] = set()
    for path in files:
        match = pattern.search(path.stem)
        if match:
            numbers.add(int(match.group(1)))
    return numbers


def validate_publish_outputs(
    *,
    product_dir: str | Path,
    xlsx_path: str | Path,
    expected_count: int,
    prefix: str,
    start_number: int,
) -> PublishValidationResult:
    product_dir = Path(product_dir)
    xlsx_path = Path(xlsx_path)
    expected_count = max(1, int(expected_count or 1))
    prefix = str(prefix or "").strip()
    start_number = int(start_number or 0)

    if not product_dir.exists():
        return PublishValidationResult(ok=False, message=f"最终产品图目录不存在：{product_dir}")
    if not xlsx_path.exists():
        return PublishValidationResult(ok=False, message=f"XLSX 不存在：{xlsx_path}")

    images = _image_files(product_dir)
    if not images:
        return PublishValidationResult(ok=False, image_count=0, message=f"最终产品图目录没有图片：{product_dir}")
    if len(images) != expected_count:
        return PublishValidationResult(
            ok=False,
            image_count=len(images),
            message=f"图片数量不一致：预期 {expected_count} 张，实际 {len(images)} 张",
        )

    numbers = _extract_product_numbers(images, prefix)
    if not numbers:
        return PublishValidationResult(ok=False, image_count=len(images), message=f"图片文件名未读到 {prefix} 货号")

    expected_last = start_number + expected_count - 1
    if start_number not in numbers or expected_last not in numbers:
        return PublishValidationResult(
            ok=False,
            image_count=len(images),
            message=f"首末货号不匹配：预期 {prefix}-{start_number} 到 {prefix}-{expected_last}",
        )

    return PublishValidationResult(ok=True, image_count=len(images), message=f"产物校验通过：{len(images)} 张图片")


class ProductPublishPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings_store = SettingsStore()
        self.settings = self.settings_store.load()
        self.adapter = PosAiImgAdapter()
        self.comfyui_service = ComfyUIService()
        self.putaway_adapter = PutawayAdapter(
            project_dir=Path(self.settings.putaway_project_dir or r"E:\1PythonProject\PutawayAiRobot"),
            data_dir_path=Path(self.settings.putaway_data_dir or r"E:\1PythonProject\PutawayAiRobot\data"),
            log_dir_path=Path(self.settings.putaway_log_dir or r"E:\1PythonProject\PutawayAiRobot\log"),
        )
        self.task_store = self._build_task_store(self.settings)
        self.tasks: list[ProductTaskRecord] = []
        self._reference_images: list[Path] = []
        self.process: QProcess | None = None
        self.current_task: ProductTaskRecord | None = None
        self._stdout_buffer = ""
        self._stderr_buffer = ""
        self._stopping_task_id = ""
        self._loading_preferences = False
        self._saved_local_count = 10
        self._saved_ai_count = 2
        self._task_started_at = 0.0
        self.orchestrator: StageOrchestrator | None = None

        self.no_output_timer = QTimer(self)
        self.no_output_timer.setSingleShot(False)
        self.no_output_timer.timeout.connect(self._warn_if_no_output_yet)

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
        header_layout.setSpacing(8)
        title = QLabel("产品任务发布")
        title.setObjectName("sectionTitle")
        hint = QLabel("先确认模板参数，再选择 AI 改图或本地生图。第一版只同步产物并唤起上架程序，不自动点击真实发布。")
        hint.setObjectName("cardSubtitle")
        hint.setWordWrap(True)
        header_layout.addWidget(title)
        header_layout.addWidget(hint)
        root.addWidget(header)

        body = QGridLayout()
        body.setSpacing(14)
        body.addWidget(self._build_draft_panel(), 0, 0)
        body.addWidget(self._build_flow_panel(), 0, 1)
        body.addWidget(self._build_task_panel(), 0, 2)
        body.setColumnStretch(0, 2)
        body.setColumnStretch(1, 2)
        body.setColumnStretch(2, 2)
        root.addLayout(body, stretch=1)

    def _build_draft_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setMinimumWidth(350)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)

        title = QLabel("任务模板")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        self.prefix_combo = QComboBox()
        self.prefix_combo.addItems(["BO", "SZW"])
        self.prefix_combo.currentTextChanged.connect(self._refresh_start_number)

        self.task_name_edit = QLineEdit("默认产品发布任务")

        self.start_spin = QSpinBox()
        self.start_spin.setRange(1, 999999)
        self.start_spin.setValue(1421)

        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 500)
        self.count_spin.setValue(10)
        self.count_spin.setSuffix(" 张")

        self.generation_mode_combo = QComboBox()
        self.generation_mode_combo.addItems(["本地生图", "AI 改图"])
        self.generation_mode_combo.currentTextChanged.connect(self._sync_generation_mode)

        self.handoff_combo = QComboBox()
        self.handoff_combo.addItems(["同步并唤起"])

        self.test_mode_check = QCheckBox("测试模式：不占用正式货号，不自动衔接真实发布")
        self.test_mode_check.setChecked(True)
        self.handoff_delay_spin = QSpinBox()
        self.handoff_delay_spin.setRange(0, 3600)
        self.handoff_delay_spin.setSuffix(" 秒")
        self.pause_before_putaway_check = QCheckBox("上架前暂停，等我点“继续上架”")
        self.pause_before_putaway_check.setChecked(True)

        self.form_layout = QFormLayout()
        self.form_layout.setLabelAlignment(Qt.AlignRight)
        self.form_layout.addRow("店铺前缀", self.prefix_combo)
        self.form_layout.addRow("任务名称", self.task_name_edit)
        self.form_layout.addRow("起始货号", self.start_spin)
        self.form_layout.addRow("生图方式", self.generation_mode_combo)
        self.count_label = QLabel("计划张数")
        self.form_layout.addRow(self.count_label, self.count_spin)
        self.form_layout.addRow("上架衔接", self.handoff_combo)
        self.form_layout.addRow("等待上架", self.handoff_delay_spin)
        layout.addLayout(self.form_layout)
        layout.addWidget(self.test_mode_check)
        layout.addWidget(self.pause_before_putaway_check)

        self.local_params_panel = self._build_local_params_panel()
        self.ai_params_panel = self._build_ai_params_panel()
        layout.addWidget(self.local_params_panel)
        layout.addWidget(self.ai_params_panel)

        actions = QHBoxLayout()
        self.confirm_button = QPushButton("同意并开始")
        self.confirm_button.setObjectName("primaryButton")
        self.confirm_button.clicked.connect(self.confirm_and_start)
        self.stop_button = QPushButton("停止任务")
        self.stop_button.setObjectName("ghostButton")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_job)
        self.primary_action_buttons = [self.confirm_button, self.stop_button]
        actions.addWidget(self.confirm_button)
        actions.addWidget(self.stop_button)
        layout.addLayout(actions)
        layout.addStretch(1)
        return panel

    def _build_local_params_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("subPanel")
        layout = QFormLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)

        self.local_style_combo = QComboBox()
        self.local_style_combo.addItem("仿油彩名画风格竖版印花")
        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(8, 60)
        self.steps_spin.setValue(28)
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(1, 2147483647)
        self.seed_spin.setValue(2026061702)
        self.auto_start_comfyui_check = QCheckBox("自动启动 ComfyUI")
        self.auto_start_comfyui_check.setChecked(self.settings.local_image_auto_start_comfyui)
        self.keep_comfyui_check = QCheckBox("任务后保留 ComfyUI")
        self.keep_comfyui_check.setChecked(self.settings.local_image_keep_comfyui)

        layout.addRow("本地风格", self.local_style_combo)
        layout.addRow("采样步数", self.steps_spin)
        layout.addRow("随机种子", self.seed_spin)
        layout.addRow("", self.auto_start_comfyui_check)
        layout.addRow("", self.keep_comfyui_check)
        return panel

    def _build_ai_params_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("subPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        top = QHBoxLayout()
        self.reference_count_label = QLabel("参考图 0 张")
        add_button = QPushButton("添加参考图")
        add_button.setObjectName("ghostButton")
        add_button.clicked.connect(self.add_reference_images)
        top.addWidget(self.reference_count_label)
        top.addStretch(1)
        top.addWidget(add_button)
        layout.addLayout(top)

        self.ai_prompt_edit = QTextEdit()
        self.ai_prompt_edit.setFixedHeight(120)
        self.ai_prompt_edit.setPlainText(self.settings.ai_edit_prompt or DEFAULT_AI_EDIT_PROMPT)
        layout.addWidget(self.ai_prompt_edit)
        return panel

    def _build_flow_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)

        title = QLabel("流程状态")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        self.status_label = QLabel("待确认")
        self.status_label.setObjectName("statusPill")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.flow_labels: list[QLabel] = []
        for step in ("1. 确认参数", "2. 生图", "3. 产物校验", "4. 同步投放目录", "5. 唤起上架"):
            label = QLabel(step)
            label.setObjectName("cardSubtitle")
            self.flow_labels.append(label)
            layout.addWidget(label)

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setObjectName("taskLog")
        self.summary_text.setPlainText("等待确认任务。")
        layout.addWidget(self.summary_text, stretch=1)
        return panel

    def _build_task_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("最近任务")
        title.setObjectName("panelTitle")
        self.batch_delete_toggle = QCheckBox("批量删除")
        self.batch_delete_toggle.toggled.connect(self._toggle_batch_delete_mode)
        self.batch_delete_button = QPushButton("删除选中")
        self.batch_delete_button.setObjectName("ghostButton")
        self.batch_delete_button.setEnabled(False)
        self.batch_delete_button.clicked.connect(self.delete_selected_tasks)
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(self.batch_delete_toggle)
        top.addWidget(self.batch_delete_button)
        layout.addLayout(top)

        self.task_list = QListWidget()
        self.task_list.setObjectName("eventList")
        self.task_list.setSelectionMode(QListWidget.SingleSelection)
        self.task_list.itemSelectionChanged.connect(self._on_task_selection_changed)
        layout.addWidget(self.task_list, stretch=1)

        self.output_label = QLabel("输出路径：--")
        self.output_label.setWordWrap(True)
        self.output_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.output_label)
        return panel

    def _default_product_title(self, prefix: str) -> str:
        if prefix == "SZW":
            return self.settings.szw_product_title
        return self.settings.bo_product_title

    def _refresh_start_number(self, prefix: str) -> None:
        if self._loading_preferences:
            return
        fallback = self.start_spin.value() or (1421 if prefix == "BO" else 3113)
        suggested = suggest_next_start(prefix, self.settings.posai_gallery_root, fallback)
        self.start_spin.setValue(suggested)

    def _sync_generation_mode(self) -> None:
        is_ai = self.generation_mode_combo.currentText() == "AI 改图"
        self.ai_params_panel.setVisible(is_ai)
        self.local_params_panel.setVisible(not is_ai)

        self.count_spin.blockSignals(True)
        if is_ai:
            self.count_label.setText("本次轮数")
            self.count_spin.setSuffix(" 轮")
            if not self._loading_preferences:
                self.count_spin.setValue(self._saved_ai_count)
        else:
            self.count_label.setText("计划张数")
            self.count_spin.setSuffix(" 张")
            if not self._loading_preferences:
                self.count_spin.setValue(self._saved_local_count)
        self.count_spin.blockSignals(False)
        if not self._loading_preferences:
            self._save_preferences()

    def add_reference_images(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择参考图",
            self.settings.ai_edit_reference_dir,
            "Images (*.png *.jpg *.jpeg *.webp)",
        )
        for file_path in files:
            self._add_reference_image(file_path)

    def _add_reference_image(self, image_path: str) -> None:
        path = Path(image_path)
        if path not in self._reference_images:
            self._reference_images.append(path)
        self.reference_count_label.setText(f"参考图 {len(self._reference_images)} 张")
        self._save_preferences()

    def build_local_image_job(self) -> LocalImageJob:
        return LocalImageJob(
            prefix=self.prefix_combo.currentText(),
            start_number=self.start_spin.value(),
            count=self.count_spin.value(),
            style_name=self.local_style_combo.currentText(),
            steps=self.steps_spin.value(),
            seed=self.seed_spin.value(),
            test_mode=self.test_mode_check.isChecked(),
            auto_start_comfyui=self.auto_start_comfyui_check.isChecked(),
            keep_comfyui=self.keep_comfyui_check.isChecked(),
            gallery_root=self.settings.posai_gallery_root,
            mockup_root=self.settings.posai_mockup_root,
            xlsx_root=self.settings.posai_xlsx_root,
        )

    def build_ai_edit_job(self) -> AIEditJob:
        settings = self.settings_store.load()
        self.settings = settings
        provider = settings.default_ai_provider()
        return AIEditJob(
            images=list(self._reference_images),
            prompt=self.ai_prompt_edit.toPlainText().strip(),
            api_key=provider.api_key,
            api_base=provider.api_base,
            model=provider.model,
            output_dir=self._build_ai_output_dir(),
            size=provider.size,
            split_collage=bool(settings.ai_edit_split_collage),
            split_count=max(1, int(settings.ai_edit_split_count or 10)),
            total_return_count=max(1, int(settings.ai_edit_total_return_count or self.count_spin.value() or 1)),
            prefix=self.prefix_combo.currentText(),
            start_number=self.start_spin.value(),
            test_mode=self.test_mode_check.isChecked(),
            gallery_root=settings.posai_gallery_root,
            mockup_root=settings.posai_mockup_root,
            xlsx_root=settings.posai_xlsx_root,
        )

    def _build_ai_output_dir(self) -> Path:
        batch = build_batch_paths(
            prefix=self.prefix_combo.currentText(),
            start_number=self.start_spin.value(),
            count=max(1, self.count_spin.value()),
            style_name="AI改图",
            gallery_root=self.settings.posai_gallery_root,
            mockup_root=self.settings.posai_mockup_root,
            xlsx_root=self.settings.posai_xlsx_root,
            stamp=datetime.now().strftime("%Y.%m%d.%H%M.%S"),
        )
        return batch.gallery_batch_dir / "临时输出"

    def confirm_and_start(self) -> None:
        if self.orchestrator is not None and self.orchestrator.stage == PublishStage.PENDING_CONFIRM:
            self._resume_pending_launch()
            return
        summary = self._confirmation_summary()
        accepted = QMessageBox.question(self, "确认产品任务", summary)
        if accepted != QMessageBox.Yes:
            return
        record = self._create_task_record(summary)
        self.tasks.append(record)
        self._append_record_log(record, "已确认任务，等待生图执行")
        self._save_task_history()
        self._rebuild_task_list()
        self._select_record(record)
        self._set_status(record)
        self._start_generation(record)

    def _count_summary_text(self) -> str:
        if self.generation_mode_combo.currentText() == "AI 改图":
            return f"本次轮数：{self.count_spin.value()} 轮"
        return f"计划张数：{self.count_spin.value()} 张"

    def _confirmation_summary(self) -> str:
        mode = self.generation_mode_combo.currentText()
        occupy_text = "不会占用正式货号" if self.test_mode_check.isChecked() else "将占用正式货号"
        sync_text = "会同步到 PutawayAiRobot data"
        launch_text = "会启动/唤起 PutawayAiRobot"
        delay_seconds = self.handoff_delay_spin.value()
        pause_text = "上架前会暂停等待人工确认" if self.pause_before_putaway_check.isChecked() else "上架前不会额外暂停"
        return (
            f"任务：{self.task_name_edit.text().strip() or '默认产品发布任务'}\n"
            f"店铺前缀：{self.prefix_combo.currentText()}\n"
            f"货号范围：{self.prefix_combo.currentText()}-{self.start_spin.value()} 起\n"
            f"{self._count_summary_text()}\n"
            f"生图方式：{mode}\n"
            f"货号策略：{occupy_text}\n"
            f"上架衔接：{sync_text}；{launch_text}\n"
            f"编排策略：生图完成后等待 {delay_seconds} 秒；{pause_text}\n"
            "安全边界：不会自动点击真实发布按钮。"
        )

    def _create_task_record(self, summary: str) -> ProductTaskRecord:
        mode = self.generation_mode_combo.currentText()
        name = self.task_name_edit.text().strip() or f"{self.prefix_combo.currentText()} 产品发布任务"
        return ProductTaskRecord(
            task_id=datetime.now().strftime("%Y%m%d%H%M%S"),
            task_name=name,
            prefix=self.prefix_combo.currentText(),
            start_number=self.start_spin.value(),
            count=self.count_spin.value(),
            generation_mode=mode,
            product_title=self._default_product_title(self.prefix_combo.currentText()),
            handoff_mode=self.handoff_combo.currentText(),
            test_mode=self.test_mode_check.isChecked(),
            status="confirmed",
            stage_text="已确认",
            progress_percent=20,
            confirmation_summary=summary,
        )

    def _start_generation(self, record: ProductTaskRecord) -> None:
        if self.process is not None:
            self._mark_record_failed(record, "当前已有任务在运行，请等待当前任务结束后再开始新任务。")
            return
        self.current_task = record
        record.failure_reason = ""
        record.status = "generating"
        record.stage_text = "生图中"
        record.progress_percent = 30
        self._append_record_log(record, f"开始执行：{record.generation_mode}")
        self._save_and_refresh(record)
        if record.generation_mode == "AI 改图":
            self._start_ai_generation(record)
            return
        self._start_local_generation(record)

    def _start_local_generation(self, record: ProductTaskRecord) -> None:
        job = self.build_local_image_job()
        record.job_payload = self._local_job_payload(job)
        self._sync_mirror_task(record)
        program, args, cwd = self.adapter.local_image_command(job)
        comfy_status = self.comfyui_service.ensure_ready(
            auto_start=job.auto_start_comfyui,
            timeout_seconds=240,
            logger=lambda msg: self._append_record_log(record, msg),
        )
        self._append_record_log(record, comfy_status.message)
        if not comfy_status.ready:
            record.status = "confirmed"
            record.stage_text = "等待 ComfyUI"
            self.confirm_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.current_task = None
            self._save_and_refresh(record)
            return
        if job.test_mode:
            self._append_record_log(record, "测试模式：只生成测试印花，不占用正式货号，也不自动进入上架。")
        else:
            self._append_record_log(record, "完整模式：会按正式货号生成产物，完成后可继续校验并同步。")
        self._start_process(record, program, args, cwd)

    def _start_ai_generation(self, record: ProductTaskRecord) -> None:
        job = self.build_ai_edit_job()
        if not job.images:
            self._mark_record_failed(record, "请先添加至少 1 张参考图。")
            return
        if not job.prompt:
            self._mark_record_failed(record, "请先填写改图要求。")
            return
        record.job_payload = self._ai_job_payload(job)
        record.output_dir = str(job.output_dir or "")
        self._sync_mirror_task(record)
        self._start_process(record, *self.adapter.ai_edit_command(job), api_key=job.api_key)

    def _local_job_payload(self, job: LocalImageJob) -> dict[str, object]:
        return {
            "style_name": job.style_name,
            "steps": job.steps,
            "width": job.width,
            "height": job.height,
            "seed": job.seed,
            "test_mode": job.test_mode,
            "auto_start_comfyui": job.auto_start_comfyui,
            "keep_comfyui": job.keep_comfyui,
            "gallery_root": job.gallery_root,
            "mockup_root": job.mockup_root,
            "xlsx_root": job.xlsx_root,
        }

    def _ai_job_payload(self, job: AIEditJob) -> dict[str, object]:
        output_dir = Path(job.output_dir or "")
        batch_dir = output_dir.parent if output_dir.name == "临时输出" else output_dir
        return {
            "images": [str(path) for path in job.images],
            "prompt": job.prompt,
            "api_base": job.api_base,
            "model": job.model,
            "output_dir": str(output_dir),
            "batch_dir": str(batch_dir),
            "final_transparent_dir": str(batch_dir / "最终透明底"),
            "size": job.size,
            "split_collage": job.split_collage,
            "split_count": job.split_count,
            "total_return_count": job.total_return_count,
            "test_mode": job.test_mode,
            "gallery_root": job.gallery_root,
            "mockup_root": job.mockup_root,
            "xlsx_root": job.xlsx_root,
        }

    def _start_process(
        self,
        record: ProductTaskRecord,
        program: str,
        args: list[str],
        cwd: Path,
        api_key: str = "",
    ) -> None:
        self._append_record_log(record, f"启动命令：{program} {' '.join(args)}")
        self._append_record_log(record, f"工作目录：{cwd}")
        process = QProcess(self)
        process.setProgram(program)
        process.setArguments(args)
        process.setWorkingDirectory(str(cwd))
        process.readyReadStandardOutput.connect(self._read_stdout)
        process.readyReadStandardError.connect(self._read_stderr)
        process.finished.connect(self._on_process_finished)
        process.errorOccurred.connect(self._on_process_error)
        started_signal = getattr(process, "started", None)
        if started_signal is not None:
            started_signal.connect(lambda: self._append_record_log(record, f"生图进程已启动，PID={process.processId()}"))
        self._stdout_buffer = ""
        self._stderr_buffer = ""
        self._task_started_at = time.time()
        self.process = process
        self.confirm_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self._set_process_env(process, api_key)
        self.no_output_timer.start(15000)
        process.start()

    def _set_process_env(self, process: QProcess, api_key: str = "") -> None:
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUTF8", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        if api_key:
            env.insert("CONSOLEPLAT_AI_IMAGE_API_KEY", api_key)
        pythonpath = env.value("PYTHONPATH", "")
        user_site = site.getusersitepackages()
        if user_site and user_site not in pythonpath:
            pythonpath = os.pathsep.join([part for part in [pythonpath, user_site] if part])
        env.insert("PYTHONPATH", pythonpath)
        process.setProcessEnvironment(env)

    def _mark_record_failed(self, record: ProductTaskRecord, reason: str) -> None:
        if self.current_task is record:
            self.current_task = None
        self.process = None
        self.no_output_timer.stop()
        self._task_started_at = 0.0
        self.confirm_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        record.status = "failed"
        record.stage_text = "失败"
        record.progress_percent = 0
        record.failure_reason = reason
        self._append_record_log(record, reason)
        self._save_and_refresh(record)

    def stop_job(self) -> None:
        if self.current_task is None:
            return
        if self.process is not None:
            self._stopping_task_id = self.current_task.task_id
            self._append_record_log(self.current_task, "正在停止任务...")
            if self.orchestrator is not None:
                self.orchestrator.abort()
            self.process.kill()
            return
        if self.orchestrator is None:
            return
        self._append_record_log(self.current_task, "已中止等待中的上架衔接。")
        self.orchestrator.abort()
        self.current_task.status = "failed"
        self.current_task.stage_text = "已中止"
        self.current_task.progress_percent = 0
        self._save_and_refresh(self.current_task)
        self.confirm_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def _read_stdout(self) -> None:
        if self.process is None or self.current_task is None:
            return
        text = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._stdout_buffer += text
        if text.strip():
            self.no_output_timer.stop()
        self._append_record_log(self.current_task, text.rstrip())
        self._update_progress_from_text(text)

    def _read_stderr(self) -> None:
        if self.process is None or self.current_task is None:
            return
        text = bytes(self.process.readAllStandardError()).decode("utf-8", errors="replace")
        self._stderr_buffer += text
        if text.strip():
            self.no_output_timer.stop()
        self._append_record_log(self.current_task, text.rstrip())

    def _update_progress_from_text(self, text: str) -> None:
        if self.current_task is None or not text.strip():
            return
        if self.current_task.generation_mode == "本地生图":
            if "Queued " in text:
                self.current_task.stage_text = "排队中"
                self.current_task.progress_percent = max(self.current_task.progress_percent, 36)
            elif "Saved " in text:
                self.current_task.stage_text = "生成中"
                self.current_task.progress_percent = max(self.current_task.progress_percent, 48)
            elif "Done. Exported " in text:
                self.current_task.stage_text = "导出完成"
                self.current_task.progress_percent = max(self.current_task.progress_percent, 55)
        else:
            self.current_task.stage_text = "生图中"
            self.current_task.progress_percent = max(self.current_task.progress_percent, 42)
            if '"outputs"' in text or "output_dir" in text:
                self.current_task.progress_percent = max(self.current_task.progress_percent, 55)
        self._save_and_refresh(self.current_task)

    def _on_process_finished(self, exit_code: int, _exit_status) -> None:
        process = self.process
        record = self.current_task
        if process is None or record is None:
            return
        stdout = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
        stderr = bytes(process.readAllStandardError()).decode("utf-8", errors="replace")
        if stdout.strip():
            self._stdout_buffer += stdout
            self._append_record_log(record, stdout.rstrip())
        if stderr.strip():
            self._stderr_buffer += stderr
            self._append_record_log(record, stderr.rstrip())
        self.process = None
        self.no_output_timer.stop()
        self._task_started_at = 0.0
        self.current_task = None
        self.confirm_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        if self._stopping_task_id == record.task_id:
            self._stopping_task_id = ""
            self._mark_record_failed(record, "任务已手动停止")
            return
        if record.generation_mode == "AI 改图":
            self._finish_ai_generation(record, exit_code)
            return
        self._finish_local_generation(record, exit_code)

    def _finish_local_generation(self, record: ProductTaskRecord, exit_code: int) -> None:
        if exit_code != 0:
            self._mark_record_failed(record, f"本地生图失败，退出码 {exit_code}")
            return
        summary = self.adapter.parse_finished_result(
            self._stdout_buffer,
            LocalImageJob(
                prefix=record.prefix,
                start_number=record.start_number,
                count=record.count,
                test_mode=record.test_mode,
            ),
        )
        if not summary.ok:
            self._mark_record_failed(record, summary.message)
            return
        record.status = "generated"
        record.stage_text = "生图完成"
        record.progress_percent = 55
        record.output_dir = summary.print_dir or summary.raw_dir
        record.product_dir = summary.mockup_dir
        record.xlsx_path = summary.xlsx_path
        self._append_record_log(record, summary.message)
        if record.product_dir and record.xlsx_path:
            self._append_record_log(record, "已拿到最终产品图和 xlsx，可继续点击“校验并同步”。")
        else:
            self._append_record_log(record, "当前任务已结束，但还没有完整上架产物。")
        self._save_and_refresh(record)
        self._auto_continue_after_generation(record)

    def _finish_ai_generation(self, record: ProductTaskRecord, exit_code: int) -> None:
        summary = self.adapter.parse_ai_edit_result(self._stdout_buffer)
        if exit_code != 0 or not summary.ok:
            failed_items = list(summary.failed or [])
            reason = failed_items[0] if failed_items else (summary.message or f"AI 改图失败，退出码 {exit_code}")
            self._mark_record_failed(record, reason)
            return
        record.status = "generated"
        record.stage_text = "生图完成"
        record.progress_percent = 55
        record.output_dir = summary.output_dir
        record.job_payload["outputs"] = list(summary.outputs or [])
        self._append_record_log(record, summary.message)
        if record.test_mode:
            self._append_record_log(record, "测试模式已结束，当前不会进入正式上架流程。")
        else:
            if not self._formalize_ai_outputs(record, summary.outputs or []):
                return
        self._save_and_refresh(record)
        self._auto_continue_after_generation(record)

    def _formalize_ai_outputs(self, record: ProductTaskRecord, outputs: list[str]) -> bool:
        split_paths = [
            Path(path)
            for path in outputs
            if Path(path).suffix.lower() == ".png" and "_part_" in Path(path).stem.lower()
        ]
        if not split_paths:
            self._mark_record_failed(record, "AI 改图没有生成可用于正式后处理的切割结果。")
            return False
        final_transparent_dir = Path(str(record.job_payload.get("final_transparent_dir") or ""))
        if not final_transparent_dir:
            self._mark_record_failed(record, "缺少最终透明底目录，无法继续正式后处理。")
            return False
        batch_dir = final_transparent_dir.parent
        settings = self.settings_store.load()
        product_dir = self._derive_ai_product_dir(record)
        xlsx_path = self._derive_ai_xlsx_path(record)
        summary = formalize_ai_edit_outputs(
            split_paths=split_paths,
            final_transparent_dir=final_transparent_dir,
            final_product_dir=product_dir,
            xlsx_path=xlsx_path,
            putaway_data_dir=Path(settings.putaway_data_dir),
            prefix=record.prefix.upper(),
            start_number=record.start_number,
            product_title=record.product_title,
            xlsx_batch_start_number=record.start_number,
            xlsx_batch_count=self._expected_output_count(record),
        )
        if not summary.ok:
            self._mark_record_failed(record, summary.message)
            return False
        record.status = "synced"
        record.stage_text = "已同步"
        record.progress_percent = 80
        record.product_dir = str(product_dir)
        record.xlsx_path = str(xlsx_path)
        record.job_payload["final_transparent_dir"] = str(final_transparent_dir)
        record.job_payload["final_product_dir"] = str(product_dir)
        record.job_payload["outputs"] = list(summary.renamed_outputs)
        self._append_record_log(record, summary.message)
        if summary.putaway is not None and summary.putaway.message:
            self._append_record_log(record, summary.putaway.message)
        self._save_and_refresh(record)
        return True

    def _expected_output_count(self, record: ProductTaskRecord) -> int:
        if record.generation_mode == "AI 改图":
            split_count = max(1, int(record.job_payload.get("split_count") or 25))
            total_rounds = max(1, int(record.job_payload.get("total_return_count") or record.count or 1))
            return total_rounds * split_count
        return max(1, int(record.count or 1))

    def _build_orchestrator(self, record: ProductTaskRecord) -> StageOrchestrator:
        return StageOrchestrator(
            schedule=lambda delay_seconds, callback: QTimer.singleShot(max(0, int(delay_seconds)) * 1000, callback),
            on_validate=self._run_handoff_validation,
            on_launch=self._launch_putaway_record,
            on_stage_changed=lambda target, stage, countdown_seconds=None: self._on_orchestrator_stage_changed(
                target,
                stage,
                countdown_seconds=countdown_seconds,
            ),
        )

    def _on_orchestrator_stage_changed(
        self,
        record: ProductTaskRecord,
        stage: PublishStage,
        *,
        countdown_seconds: int | None = None,
    ) -> None:
        stage_text_map = {
            PublishStage.WAITING_HANDOFF: "等待上架",
            PublishStage.VALIDATING: "产物校验",
            PublishStage.PENDING_CONFIRM: "待确认上架",
            PublishStage.LAUNCHING: "正在唤起上架",
            PublishStage.DONE: "已唤起上架",
            PublishStage.ABORTED: "已中止",
            PublishStage.FAILED: "上架衔接失败",
        }
        progress_map = {
            PublishStage.WAITING_HANDOFF: 80,
            PublishStage.VALIDATING: 60,
            PublishStage.PENDING_CONFIRM: 90,
            PublishStage.LAUNCHING: 95,
            PublishStage.DONE: 100,
            PublishStage.ABORTED: 0,
            PublishStage.FAILED: 0,
        }
        record.stage_text = stage_text_map.get(stage, record.stage_text)
        record.progress_percent = progress_map.get(stage, record.progress_percent)
        if stage == PublishStage.WAITING_HANDOFF and countdown_seconds is not None:
            self._append_record_log(record, f"将在 {countdown_seconds} 秒后进入上架衔接。")
        elif stage == PublishStage.PENDING_CONFIRM:
            self._append_record_log(record, "已完成校验与同步，等待人工确认继续上架。")
        elif stage == PublishStage.ABORTED:
            self._append_record_log(record, "上架衔接已中止。")
        self.stop_button.setEnabled(stage not in {PublishStage.DONE, PublishStage.ABORTED, PublishStage.FAILED})
        self.confirm_button.setEnabled(stage in {PublishStage.PENDING_CONFIRM} or self.process is None)
        if stage == PublishStage.PENDING_CONFIRM:
            self.confirm_button.setText("继续上架")
        else:
            self.confirm_button.setText("同意并开始")
        self._save_and_refresh(record)

    def _resume_pending_launch(self) -> None:
        if self.orchestrator is None:
            return
        self.orchestrator.resume_launch()

    def _run_handoff_validation(self, record: ProductTaskRecord) -> bool:
        if record.status != "generated":
            return True
        return bool(getattr(self.validate_and_sync(record), "ok", False))

    def _warn_if_no_output_yet(self) -> None:
        if self.process is None or self.current_task is None:
            return
        if self._stdout_buffer.strip() or self._stderr_buffer.strip():
            return
        waited_seconds = max(0, int(time.time() - self._task_started_at)) if self._task_started_at else 0
        state = getattr(self.process, "state", lambda: None)()
        state_text = "运行中" if state == QProcess.Running else ("启动中" if state == QProcess.Starting else "未知")
        if self.current_task.generation_mode == "AI 改图":
            hint = (
                f"暂时还没有收到脚本输出，已等待 {waited_seconds} 秒。当前进程状态：{state_text}。"
                "常见原因是 AI 改图接口响应较慢、网络请求尚未返回，或脚本仍在初始化。"
            )
        else:
            hint = (
                f"暂时还没有收到脚本输出，已等待 {waited_seconds} 秒。当前进程状态：{state_text}。"
                "常见原因是 ComfyUI 尚未启动、conda 环境启动较慢，或脚本仍在初始化。"
            )
        self._append_record_log(
            self.current_task,
            hint,
        )
        self._save_and_refresh(self.current_task)

    def _derive_ai_product_dir(self, record: ProductTaskRecord) -> Path:
        mockup_root = str(record.job_payload.get("mockup_root") or self.settings.posai_mockup_root)
        batch_dir = Path(str(record.job_payload.get("batch_dir") or ""))
        if batch_dir:
            batch_name = batch_dir.name
            parts = batch_dir.parts
            if len(parts) >= 4:
                prefix, year, month = parts[-4], parts[-3], parts[-2]
                return Path(mockup_root) / prefix / year / month / batch_name / "最终产品图"
        batch = build_batch_paths(
            prefix=record.prefix,
            start_number=record.start_number,
            count=self._expected_output_count(record),
            style_name="AI改图",
            gallery_root=str(record.job_payload.get("gallery_root") or self.settings.posai_gallery_root),
            mockup_root=mockup_root,
            xlsx_root=str(record.job_payload.get("xlsx_root") or self.settings.posai_xlsx_root),
            stamp=datetime.now().strftime("%Y.%m%d.%H%M.%S"),
        )
        return batch.mockup_final_dir

    def _derive_ai_xlsx_path(self, record: ProductTaskRecord) -> Path:
        xlsx_root = str(record.job_payload.get("xlsx_root") or self.settings.posai_xlsx_root)
        batch_dir = Path(str(record.job_payload.get("batch_dir") or ""))
        if batch_dir:
            return Path(xlsx_root) / record.prefix / f"{batch_dir.name}.xlsx"
        batch = build_batch_paths(
            prefix=record.prefix,
            start_number=record.start_number,
            count=self._expected_output_count(record),
            style_name="AI改图",
            gallery_root=str(record.job_payload.get("gallery_root") or self.settings.posai_gallery_root),
            mockup_root=str(record.job_payload.get("mockup_root") or self.settings.posai_mockup_root),
            xlsx_root=xlsx_root,
            stamp=datetime.now().strftime("%Y.%m%d.%H%M.%S"),
        )
        return batch.xlsx_path

    def _auto_continue_after_generation(self, record: ProductTaskRecord) -> None:
        if record.test_mode or record.handoff_mode != "同步并唤起":
            return
        if not record.product_dir or not record.xlsx_path:
            return
        self.current_task = record
        self.orchestrator = self._build_orchestrator(record)
        self.orchestrator.begin_handoff(
            record,
            delay_seconds=self.settings.publish_handoff_delay_seconds,
            pause_before_putaway=self.settings.publish_pause_before_putaway,
        )

    def _on_process_error(self, error) -> None:
        record = self.current_task
        message = f"生图进程启动失败：{error}"
        self.no_output_timer.stop()
        self._task_started_at = 0.0
        if record is None:
            self.process = None
            self.confirm_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            return
        self._mark_record_failed(record, message)

    def validate_and_sync_selected(self) -> None:
        record = self._selected_record()
        if record is None:
            return
        self.validate_and_sync(record)

    def validate_and_sync(self, record: ProductTaskRecord) -> PutawaySyncSummary | PublishValidationResult:
        record.status = "validating"
        record.stage_text = "产物校验"
        record.progress_percent = 60
        validation = validate_publish_outputs(
            product_dir=record.product_dir,
            xlsx_path=record.xlsx_path,
            expected_count=record.count,
            prefix=record.prefix,
            start_number=record.start_number,
        )
        if not validation.ok:
            record.status = "failed"
            record.stage_text = "校验失败"
            record.progress_percent = 0
            record.failure_reason = validation.message
            self._append_record_log(record, validation.message)
            self._save_and_refresh(record)
            return validation

        summary = sync_putaway_assets(
            source_images_dir=record.product_dir,
            source_xlsx_path=record.xlsx_path,
            target_data_dir=self.settings.putaway_data_dir,
        )
        if summary.ok:
            record.status = "synced"
            record.stage_text = "已同步"
            record.progress_percent = 80
        else:
            record.status = "failed"
            record.stage_text = "同步失败"
            record.progress_percent = 0
            record.failure_reason = summary.message
        self._append_record_log(record, summary.message)
        self._save_and_refresh(record)
        return summary

    def launch_putaway_for_selected(self) -> None:
        record = self._selected_record()
        if record is None:
            return
        self._launch_putaway_record(record)

    def delete_selected_tasks(self) -> None:
        task_ids = self._selected_task_ids()
        if not task_ids:
            return
        confirmed = QMessageBox.question(
            self,
            "确认删除",
            f"将删除 {len(task_ids)} 条发布任务，并清理对应输出目录、最终透明底、最终产品图、XLSX 以及镜像任务记录。是否继续？",
        )
        if confirmed != QMessageBox.Yes:
            return
        removing = [record for record in self.tasks if record.task_id in task_ids]
        self.tasks = [record for record in self.tasks if record.task_id not in task_ids]
        for record in removing:
            self._delete_task_files(record)
            self._delete_mirror_task(record)
        self._save_task_history()
        self._rebuild_task_list()
        self._set_status(self.tasks[0] if self.tasks else None)

    def _toggle_batch_delete_mode(self, enabled: bool) -> None:
        self.task_list.setSelectionMode(QListWidget.MultiSelection if enabled else QListWidget.SingleSelection)
        self.batch_delete_button.setEnabled(enabled)
        if not enabled:
            self.task_list.clearSelection()

    def _selected_task_ids(self) -> list[str]:
        task_ids: list[str] = []
        for item in self.task_list.selectedItems():
            task_id = item.data(Qt.UserRole)
            if task_id:
                task_ids.append(str(task_id))
        return task_ids

    def _launch_putaway_record(self, record: ProductTaskRecord) -> None:
        program, args, cwd = self.putaway_adapter.launch_command()

        started = QProcess.startDetached(program, args, str(cwd))
        if started:
            record.status = "handoff"
            record.stage_text = "已唤起上架"
            record.progress_percent = 100
            self._append_record_log(record, "已唤起 PutawayAiRobot；真实发布仍需在上架程序内确认")
        else:
            record.status = "failed"
            record.stage_text = "唤起失败"
            record.failure_reason = f"无法启动：{program}"
            self._append_record_log(record, record.failure_reason)
        self._save_and_refresh(record)

    def _delete_task_files(self, record: ProductTaskRecord) -> None:
        targets: list[Path] = []
        if record.generation_mode == "AI 改图":
            output_path = Path(record.output_dir or str(record.job_payload.get("output_dir") or ""))
            if self._is_safe_cleanup_path(output_path):
                if output_path.name == "临时输出" and output_path.parent.name.startswith("AI改图_"):
                    targets.append(output_path.parent)
                else:
                    targets.append(output_path)
            final_transparent_dir = Path(str(record.job_payload.get("final_transparent_dir") or ""))
            if self._is_safe_cleanup_path(final_transparent_dir):
                if final_transparent_dir.name == "最终透明底" and final_transparent_dir.parent.name.startswith("AI改图_"):
                    targets.append(final_transparent_dir.parent)
                else:
                    targets.append(final_transparent_dir)
            final_product_dir = Path(record.product_dir or str(record.job_payload.get("final_product_dir") or ""))
            if self._is_safe_cleanup_path(final_product_dir):
                if final_product_dir.name == "最终产品图" and final_product_dir.parent.name.startswith("AI改图_"):
                    targets.append(final_product_dir.parent)
                else:
                    targets.append(final_product_dir)
        else:
            for raw_path in (record.output_dir, record.product_dir):
                path = Path(raw_path or "")
                if self._is_safe_cleanup_path(path):
                    targets.append(path)
        for path in sorted({path for path in targets if str(path)}, key=lambda item: len(item.parts), reverse=True):
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)
        xlsx_path = Path(record.xlsx_path or "")
        if self._is_safe_cleanup_path(xlsx_path, allow_file=True) and xlsx_path.exists():
            xlsx_path.unlink(missing_ok=True)

    def _is_safe_cleanup_path(self, path: Path, *, allow_file: bool = False) -> bool:
        raw_text = str(path or "").strip()
        if not raw_text or raw_text in {".", ".."}:
            return False
        try:
            resolved = path.resolve(strict=False)
        except OSError:
            return False
        anchor = resolved.anchor
        if not resolved.name or str(resolved) == anchor:
            return False
        workspace_root = Path.cwd().resolve()
        try:
            resolved.relative_to(workspace_root)
            return False
        except ValueError:
            pass
        if resolved.exists():
            if resolved.is_file():
                return allow_file
            if not resolved.is_dir():
                return False
        else:
            if path.suffix and not allow_file:
                return False
        return len(resolved.parts) >= 3

    def _delete_mirror_task(self, record: ProductTaskRecord) -> None:
        program_data_dir = (self.settings.program_data_dir or "").strip()
        if not program_data_dir:
            return
        store_name = "local_image_tasks" if record.generation_mode == "本地生图" else "ai_edit_tasks"
        store = TaskStore(program_data_dir, store_name)
        remaining = [item for item in store.load() if str(item.get("task_id") or "") != record.task_id]
        store.save(remaining)

    def _selected_record(self) -> ProductTaskRecord | None:
        items = self.task_list.selectedItems()
        if not items:
            return self.tasks[0] if self.tasks else None
        task_id = items[0].data(Qt.UserRole)
        return next((record for record in self.tasks if record.task_id == task_id), None)

    def _select_record(self, record: ProductTaskRecord) -> None:
        for index in range(self.task_list.count()):
            item = self.task_list.item(index)
            if item.data(Qt.UserRole) == record.task_id:
                self.task_list.setCurrentItem(item)
                return

    def _save_and_refresh(self, record: ProductTaskRecord) -> None:
        self._save_task_history()
        self._sync_mirror_task(record)
        self._rebuild_task_list()
        self._select_record(record)
        self._set_status(record)

    def _sync_mirror_task(self, record: ProductTaskRecord) -> None:
        program_data_dir = (self.settings.program_data_dir or "").strip()
        if not program_data_dir or not record.job_payload:
            return
        if record.generation_mode == "本地生图":
            store = TaskStore(program_data_dir, "local_image_tasks")
            payload = self._local_mirror_record(record)
        else:
            store = TaskStore(program_data_dir, "ai_edit_tasks")
            payload = self._ai_mirror_record(record)
        items = [item for item in store.load() if str(item.get("task_id") or "") != record.task_id]
        items.append(payload)
        store.save(items)

    def _local_mirror_record(self, record: ProductTaskRecord) -> dict:
        payload = record.job_payload or {}
        test_mode = bool(payload.get("test_mode", record.test_mode))
        mode_text = "测试模式" if test_mode else "完整模式"
        style_name = str(payload.get("style_name") or "仿油彩名画风格竖版印花")
        title = (
            f"{mode_text} {record.prefix} {style_name} {record.count} 张"
            if test_mode
            else f"{mode_text} {record.prefix}-{record.start_number} 起 {record.count} 张"
        )
        return {
            "task_id": record.task_id,
            "mode_text": mode_text,
            "title": title,
            "status": self._mirror_status_text(record),
            "stage_text": record.stage_text,
            "progress_percent": record.progress_percent,
            "logs": list(record.logs),
            "print_dir": record.output_dir,
            "product_dir": record.product_dir,
            "xlsx_path": record.xlsx_path,
            "job": {
                "prefix": record.prefix,
                "start_number": record.start_number,
                "count": record.count,
                "style_name": style_name,
                "steps": int(payload.get("steps") or 28),
                "width": int(payload.get("width") or 832),
                "height": int(payload.get("height") or 1216),
                "seed": int(payload.get("seed") or 2026061702),
                "test_mode": test_mode,
                "auto_start_comfyui": bool(payload.get("auto_start_comfyui", True)),
                "keep_comfyui": bool(payload.get("keep_comfyui", True)),
                "gallery_root": str(payload.get("gallery_root") or self.settings.posai_gallery_root),
                "mockup_root": str(payload.get("mockup_root") or self.settings.posai_mockup_root),
                "xlsx_root": str(payload.get("xlsx_root") or self.settings.posai_xlsx_root),
            },
        }

    def _ai_mirror_record(self, record: ProductTaskRecord) -> dict:
        payload = record.job_payload or {}
        total_return_count = max(1, int(payload.get("total_return_count") or record.count or 1))
        test_mode = bool(payload.get("test_mode", record.test_mode))
        title = f"AI 改图 {record.prefix}-{record.start_number}\n{total_return_count} 轮 · {('测试模式' if test_mode else '正式模式')}"
        return {
            "task_id": record.task_id,
            "title": title,
            "status": self._mirror_status_text(record),
            "stage_text": record.stage_text,
            "progress_percent": record.progress_percent,
            "logs": list(record.logs),
            "output_dir": record.output_dir,
            "outputs": list(payload.get("outputs") or []),
            "failed": [],
            "warnings": [],
            "round_sources": [],
            "collage_transparent_sources": [],
            "active_round_index": 0,
            "final_transparent_dir": str(payload.get("final_transparent_dir") or ""),
            "final_product_dir": record.product_dir,
            "xlsx_path": record.xlsx_path,
            "split_profile": {},
            "job": {
                "images": list(payload.get("images") or []),
                "prompt": str(payload.get("prompt") or ""),
                "api_key": "",
                "api_base": str(payload.get("api_base") or self.settings.ai_edit_api_base),
                "model": str(payload.get("model") or self.settings.ai_edit_model),
                "output_dir": str(payload.get("output_dir") or record.output_dir),
                "size": str(payload.get("size") or self.settings.ai_edit_size),
                "split_collage": bool(payload.get("split_collage", True)),
                "split_count": int(payload.get("split_count") or 25),
                "total_return_count": total_return_count,
                "prefix": record.prefix,
                "start_number": record.start_number,
                "test_mode": test_mode,
                "gallery_root": str(payload.get("gallery_root") or self.settings.posai_gallery_root),
                "mockup_root": str(payload.get("mockup_root") or self.settings.posai_mockup_root),
                "xlsx_root": str(payload.get("xlsx_root") or self.settings.posai_xlsx_root),
            },
        }

    def _mirror_status_text(self, record: ProductTaskRecord) -> str:
        return {
            "confirmed": "等待启动",
            "generating": "运行中",
            "generated": "完成",
            "validating": "校验中",
            "synced": "已同步",
            "handoff": "完成",
            "failed": "失败",
        }.get(record.status, record.status)

    def _append_record_log(self, record: ProductTaskRecord, text: str) -> None:
        if not text:
            return
        time_text = datetime.now().strftime("%H:%M:%S")
        record.logs.append(f"{time_text}  {text}")

    def _set_status(self, record: ProductTaskRecord | None) -> None:
        if record is None:
            self.status_label.setText("待确认")
            self.progress_bar.setValue(0)
            self.summary_text.setPlainText("等待确认任务。")
            self.output_label.setText("输出路径：--")
            return

        self.status_label.setText(f"{record.stage_text} / {record.status}")
        self.progress_bar.setValue(record.progress_percent)

        detail = record.confirmation_summary or ""
        if record.failure_reason:
            detail += f"\n\n失败原因：{record.failure_reason}"
        if record.logs:
            detail += "\n\n" + "\n".join(record.logs[-20:])
        self.summary_text.setPlainText(detail.strip() or "等待任务日志。")

        output_parts = [part for part in (record.product_dir, record.xlsx_path) if part]
        if not output_parts and record.output_dir:
            output_parts = [record.output_dir]
        self.output_label.setText("输出路径：" + (" | ".join(output_parts) if output_parts else "--"))

    def _on_task_selection_changed(self) -> None:
        self._set_status(self._selected_record())

    def _rebuild_task_list(self) -> None:
        self.task_list.clear()
        for record in sorted(self.tasks, key=lambda item: item.task_id, reverse=True):
            item = QListWidgetItem(
                f"{_format_task_timestamp(record.task_id)}  {record.task_name}\n"
                f"{record.generation_mode} · {record.prefix}-{record.start_number} · {record.status} · {record.stage_text}"
            )
            item.setData(Qt.UserRole, record.task_id)
            self.task_list.addItem(item)

    def _build_task_store(self, settings: AppSettings) -> TaskStore | None:
        if not settings.program_data_dir:
            return None
        return TaskStore(settings.program_data_dir, "product_publish_tasks")

    def _load_preferences(self) -> None:
        self._loading_preferences = True
        settings = self.settings_store.load()
        self.settings = settings
        self.prefix_combo.setCurrentText(getattr(settings, "publish_prefix", "") or "BO")
        self.task_name_edit.setText(str(getattr(settings, "publish_task_name", "") or "默认产品发布任务"))
        saved_start = max(0, int(getattr(settings, "publish_start_number", 0) or 0))
        if saved_start:
            self.start_spin.setValue(saved_start)
        else:
            self._refresh_start_number(self.prefix_combo.currentText())
        saved_mode = str(getattr(settings, "publish_generation_mode", "") or "本地生图")
        self.generation_mode_combo.setCurrentText(saved_mode if saved_mode in {"本地生图", "AI 改图"} else "本地生图")
        self._saved_local_count = max(1, int(getattr(settings, "publish_local_count", 10) or 10))
        self._saved_ai_count = max(1, int(getattr(settings, "publish_ai_count", 2) or 2))
        self.count_spin.setValue(
            self._saved_ai_count if self.generation_mode_combo.currentText() == "AI 改图" else self._saved_local_count
        )
        self.handoff_combo.setCurrentText(str(getattr(settings, "publish_handoff_mode", "") or "同步并唤起"))
        self.handoff_delay_spin.setValue(max(0, int(getattr(settings, "publish_handoff_delay_seconds", 0) or 0)))
        self.pause_before_putaway_check.setChecked(bool(getattr(settings, "publish_pause_before_putaway", True)))
        self.test_mode_check.setChecked(bool(getattr(settings, "publish_test_mode", True)))
        self.steps_spin.setValue(max(8, int(getattr(settings, "publish_local_steps", 28) or 28)))
        self.seed_spin.setValue(max(1, int(getattr(settings, "publish_local_seed", 2026061702) or 2026061702)))
        self.auto_start_comfyui_check.setChecked(bool(getattr(settings, "publish_auto_start_comfyui", settings.local_image_auto_start_comfyui)))
        self.keep_comfyui_check.setChecked(bool(getattr(settings, "publish_keep_comfyui", settings.local_image_keep_comfyui)))
        saved_prompt = str(getattr(settings, "publish_ai_prompt", "") or settings.ai_edit_prompt or DEFAULT_AI_EDIT_PROMPT)
        self.ai_prompt_edit.setPlainText(saved_prompt)
        saved_refs = [Path(str(path)) for path in (getattr(settings, "publish_ai_reference_images", []) or []) if str(path)]
        self._reference_images = saved_refs
        self.reference_count_label.setText(f"参考图 {len(self._reference_images)} 张")
        self._sync_generation_mode()
        self._loading_preferences = False

        self.prefix_combo.currentTextChanged.connect(self._save_preferences)
        self.task_name_edit.textChanged.connect(self._save_preferences)
        self.start_spin.valueChanged.connect(self._save_preferences)
        self.count_spin.valueChanged.connect(self._save_preferences)
        self.handoff_combo.currentTextChanged.connect(self._save_preferences)
        self.handoff_delay_spin.valueChanged.connect(self._save_preferences)
        self.pause_before_putaway_check.toggled.connect(self._save_preferences)
        self.test_mode_check.toggled.connect(self._save_preferences)
        self.steps_spin.valueChanged.connect(self._save_preferences)
        self.seed_spin.valueChanged.connect(self._save_preferences)
        self.auto_start_comfyui_check.toggled.connect(self._save_preferences)
        self.keep_comfyui_check.toggled.connect(self._save_preferences)
        self.ai_prompt_edit.textChanged.connect(self._save_preferences)

    def _save_preferences(self, *_args) -> None:
        if self._loading_preferences:
            return
        settings = self.settings_store.load()
        settings.publish_prefix = self.prefix_combo.currentText()
        settings.publish_task_name = self.task_name_edit.text().strip() or "默认产品发布任务"
        settings.publish_start_number = self.start_spin.value()
        settings.publish_generation_mode = self.generation_mode_combo.currentText()
        if self.generation_mode_combo.currentText() == "AI 改图":
            self._saved_ai_count = self.count_spin.value()
            settings.publish_ai_count = self._saved_ai_count
        else:
            self._saved_local_count = self.count_spin.value()
            settings.publish_local_count = self._saved_local_count
        if not settings.publish_local_count:
            settings.publish_local_count = self._saved_local_count
        if not settings.publish_ai_count:
            settings.publish_ai_count = self._saved_ai_count
        settings.publish_handoff_mode = self.handoff_combo.currentText()
        settings.publish_handoff_delay_seconds = self.handoff_delay_spin.value()
        settings.publish_pause_before_putaway = self.pause_before_putaway_check.isChecked()
        settings.publish_test_mode = self.test_mode_check.isChecked()
        settings.publish_local_steps = self.steps_spin.value()
        settings.publish_local_seed = self.seed_spin.value()
        settings.publish_auto_start_comfyui = self.auto_start_comfyui_check.isChecked()
        settings.publish_keep_comfyui = self.keep_comfyui_check.isChecked()
        settings.publish_ai_prompt = self.ai_prompt_edit.toPlainText().strip() or DEFAULT_AI_EDIT_PROMPT
        settings.publish_ai_reference_images = [str(path) for path in self._reference_images]
        self.settings_store.save(settings)
        self.settings = settings

    def _save_task_history(self) -> None:
        if self.task_store is None:
            return
        self.task_store.save([self._task_to_dict(record) for record in self.tasks])

    def _load_task_history(self) -> None:
        if self.task_store is None:
            return
        self.tasks = [record for record in (self._task_from_dict(item) for item in self.task_store.load()) if record is not None]
        self._rebuild_task_list()
        self._set_status(self.tasks[0] if self.tasks else None)

    def _task_to_dict(self, record: ProductTaskRecord) -> dict:
        return {
            "task_id": record.task_id,
            "task_name": record.task_name,
            "prefix": record.prefix,
            "start_number": record.start_number,
            "count": record.count,
            "generation_mode": record.generation_mode,
            "handoff_mode": record.handoff_mode,
            "test_mode": record.test_mode,
            "product_title": record.product_title,
            "status": record.status,
            "stage_text": record.stage_text,
            "progress_percent": record.progress_percent,
            "logs": list(record.logs),
            "output_dir": record.output_dir,
            "product_dir": record.product_dir,
            "xlsx_path": record.xlsx_path,
            "failure_reason": record.failure_reason,
            "confirmation_summary": record.confirmation_summary,
            "job_payload": dict(record.job_payload),
        }

    def _task_from_dict(self, payload: dict) -> ProductTaskRecord | None:
        if not isinstance(payload, dict):
            return None
        status = str(payload.get("status") or "draft")
        if status not in PRODUCT_TASK_STATUSES:
            status = "draft"
        return ProductTaskRecord(
            task_id=str(payload.get("task_id") or ""),
            task_name=str(payload.get("task_name") or "产品发布任务"),
            prefix=str(payload.get("prefix") or "BO"),
            start_number=int(payload.get("start_number") or 1421),
            count=max(1, int(payload.get("count") or 10)),
            generation_mode=str(payload.get("generation_mode") or "本地生图"),
            product_title=str(payload.get("product_title") or self._default_product_title(str(payload.get("prefix") or "BO"))),
            handoff_mode=str(payload.get("handoff_mode") or "同步并唤起"),
            test_mode=bool(payload.get("test_mode", True)),
            status=status,
            stage_text=str(payload.get("stage_text") or "待确认"),
            progress_percent=max(0, min(100, int(payload.get("progress_percent") or 0))),
            logs=[str(line) for line in (payload.get("logs") or [])],
            output_dir=str(payload.get("output_dir") or ""),
            product_dir=str(payload.get("product_dir") or ""),
            xlsx_path=str(payload.get("xlsx_path") or ""),
            failure_reason=str(payload.get("failure_reason") or ""),
            confirmation_summary=str(payload.get("confirmation_summary") or ""),
            job_payload=dict(payload.get("job_payload") or {}),
        )

    def closeEvent(self, event) -> None:  # noqa: N802
        self.no_output_timer.stop()
        if self.orchestrator is not None:
            self.orchestrator.abort()
        if self.process is not None:
            kill = getattr(self.process, "kill", None)
            if kill is not None:
                kill()
            wait_for_finished = getattr(self.process, "waitForFinished", None)
            if wait_for_finished is not None:
                wait_for_finished(1500)
            self.process = None
        super().closeEvent(event)
