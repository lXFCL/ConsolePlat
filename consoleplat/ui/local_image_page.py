from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QProcess, Qt, QTimer
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from consoleplat.adapters.posaiimg_adapter import LocalImageJob, PosAiImgAdapter
from consoleplat.config import SettingsStore, resolve_project_dir
from consoleplat.paths import default_prints_dir
from consoleplat.services.app_log import log_exception
from consoleplat.services.comfyui_service import ComfyUIService
from consoleplat.services.posai_batch_service import suggest_next_start
from consoleplat.services.task_store import TaskStore


@dataclass
class LocalImageTaskRecord:
    task_id: str
    mode_text: str
    title: str
    job: LocalImageJob
    status: str = "等待启动"
    stage_text: str = "待启动"
    progress_percent: int = 0
    logs: list[str] = field(default_factory=list)
    print_dir: str = ""
    product_dir: str = ""
    xlsx_path: str = ""


def _format_task_timestamp(value: str) -> str:
    clean = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(clean) >= 14:
        clean = clean[:14]
        return f"{clean[:4]}.{clean[4:8]}.{clean[8:12]}.{clean[12:14]}"
    if len(clean) == 12:
        return f"{clean[:4]}.{clean[4:8]}.{clean[8:12]}"
    return str(value or "")


class TaskDetailDialog(QDialog):
    def __init__(self, record: LocalImageTaskRecord, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.record = record
        self.setWindowTitle(f"任务详情 - {record.title}")
        self.resize(860, 640)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        title = QLabel(record.title)
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        meta = QLabel(
            f"模式：{record.mode_text}\n"
            f"店铺前缀：{record.job.prefix}    张数：{record.job.count}    起始货号：{record.job.start_number}\n"
            f"状态：{record.status}"
        )
        meta.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(meta)

        progress_frame = QFrame()
        progress_frame.setObjectName("subPanel")
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setContentsMargins(14, 12, 14, 12)
        progress_layout.setSpacing(8)
        progress_header = QHBoxLayout()
        progress_header.addWidget(QLabel("任务进度"))
        progress_header.addStretch(1)
        self.progress_label = QLabel(self._progress_text(record))
        self.progress_label.setObjectName("statusPill")
        progress_header.addWidget(self.progress_label)
        progress_layout.addLayout(progress_header)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(record.progress_percent)
        progress_layout.addWidget(self.progress_bar)
        layout.addWidget(progress_frame)

        outputs = QFrame()
        outputs.setObjectName("subPanel")
        outputs_layout = QVBoxLayout(outputs)
        outputs_layout.setContentsMargins(14, 12, 14, 12)
        outputs_layout.setSpacing(12)
        outputs_title = QLabel("产物路径")
        outputs_title.setObjectName("panelTitle")
        outputs_layout.addWidget(outputs_title)

        self.print_path_label = QLabel(record.print_dir or "--")
        self.print_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.print_path_label.setWordWrap(True)
        self.open_print_button = QPushButton("打开透明底")
        self.open_print_button.setObjectName("ghostButton")
        self.open_print_button.setEnabled(bool(record.print_dir))
        self.open_print_button.clicked.connect(lambda: self._open_folder(record.print_dir))
        outputs_layout.addLayout(self._folder_row("透明底", self.print_path_label, self.open_print_button))

        self.product_path_label = QLabel(record.product_dir or "--")
        self.product_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.product_path_label.setWordWrap(True)
        self.open_product_button = QPushButton("打开产品图")
        self.open_product_button.setObjectName("ghostButton")
        self.open_product_button.setEnabled(bool(record.product_dir))
        self.open_product_button.clicked.connect(lambda: self._open_folder(record.product_dir))
        outputs_layout.addLayout(self._folder_row("产品图", self.product_path_label, self.open_product_button))

        self.xlsx_path_label = QLabel(record.xlsx_path or "--")
        self.xlsx_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.xlsx_path_label.setWordWrap(True)
        outputs_layout.addLayout(self._folder_row("表格", self.xlsx_path_label, None))
        layout.addWidget(outputs)

        log_title = QLabel("日志")
        log_title.setObjectName("panelTitle")
        layout.addWidget(log_title)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setObjectName("taskLog")
        self.log.setPlainText("\n".join(record.logs))
        layout.addWidget(self.log, stretch=1)

        close_button = QPushButton("关闭")
        close_button.setObjectName("ghostButton")
        close_button.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(close_button)
        layout.addLayout(row)

    def refresh(self, record: LocalImageTaskRecord) -> None:
        self.record = record
        self.progress_bar.setValue(record.progress_percent)
        self.progress_label.setText(self._progress_text(record))
        self.print_path_label.setText(record.print_dir or "--")
        self.product_path_label.setText(record.product_dir or "--")
        self.xlsx_path_label.setText(record.xlsx_path or "--")
        self.open_print_button.setEnabled(bool(record.print_dir))
        self.open_product_button.setEnabled(bool(record.product_dir))
        self.log.setPlainText("\n".join(record.logs))

    def _progress_text(self, record: LocalImageTaskRecord) -> str:
        return f"{record.stage_text} {record.progress_percent}%"

    def _folder_row(self, label_text: str, path_label: QLabel, button: QPushButton | None) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(QLabel(label_text), 0)
        row.addWidget(path_label, 1)
        if button is not None:
            row.addWidget(button, 0)
        return row

    def _open_folder(self, path: str) -> None:
        if not path:
            return
        try:
            os.startfile(path)  # noqa: S606
        except Exception:
            subprocess.Popen(["explorer", path])


class LocalImagePage(QWidget):
    def _format_task_timestamp(self, value: str) -> str:
        return _format_task_timestamp(value)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings_store = SettingsStore()
        self.adapter = PosAiImgAdapter()
        self.comfyui_service = ComfyUIService()
        self.process: QProcess | None = None
        self.current_task: LocalImageTaskRecord | None = None
        self.tasks: list[LocalImageTaskRecord] = []
        self.task_detail_dialog: TaskDetailDialog | None = None
        self._stdout_buffer = ""
        self._stderr_buffer = ""
        self._loading_preferences = False
        self._task_started_at = 0.0
        self.gallery_root = ""
        self.mockup_root = ""
        self.xlsx_root = ""
        self.posai_comfyui_dir = ""
        self.posai_model_root = ""
        self.task_store: TaskStore | None = None
        self._tasks_file_mtime: float | None = None
        self._dirty_task_ids: set[str] = set()
        self._persist_timer = QTimer(self)
        self._persist_timer.setSingleShot(True)
        self._persist_timer.setInterval(500)
        self._persist_timer.timeout.connect(self._flush_persist)

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
        title = QLabel("本地生图")
        title.setObjectName("sectionTitle")
        hint = QLabel("在这里发起 PosAiImg 本地批次任务。主页只保留配置和任务清单，日志与产物详情放到任务弹窗里查看。")
        hint.setObjectName("cardSubtitle")
        hint.setWordWrap(True)
        header_layout.addWidget(title)
        header_layout.addWidget(hint)
        root.addWidget(header)

        body = QHBoxLayout()
        body.setSpacing(14)
        body.addWidget(self._build_config_panel(), 0)
        body.addWidget(self._build_task_panel(), 1)
        root.addLayout(body, stretch=1)

    def _build_config_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setMinimumWidth(360)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)

        title = QLabel("批次配置")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        self.prefix_combo = QComboBox()
        self.prefix_combo.addItems(["BO", "SZW"])
        self.prefix_combo.currentTextChanged.connect(self._refresh_start_number)

        self.style_combo = QComboBox()
        self.style_combo.addItem("仿油彩名画风格竖版印花")

        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 200)
        self.count_spin.setValue(10)
        self.count_spin.setSuffix(" 张")

        self.start_spin = QSpinBox()
        self.start_spin.setRange(1, 999999)
        self.start_spin.setValue(1421)

        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(8, 60)
        self.steps_spin.setValue(28)

        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(1, 2147483647)
        self.seed_spin.setValue(2026061702)

        self.auto_start_comfyui_check = QCheckBox("自动启动 ComfyUI")
        self.keep_comfyui_check = QCheckBox("任务后保留 ComfyUI")
        self.keep_comfyui_check.setChecked(True)
        self.test_mode_check = QCheckBox("测试模式：只生成测试印花，不走货号和后画流程")
        self.test_mode_check.setChecked(True)
        self.test_mode_check.toggled.connect(self._sync_mode_controls)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.addRow("店铺前缀", self.prefix_combo)
        form.addRow("风格", self.style_combo)
        form.addRow("张数", self.count_spin)
        form.addRow("起始货号", self.start_spin)
        form.addRow("采样步数", self.steps_spin)
        form.addRow("随机种子", self.seed_spin)
        layout.addLayout(form)
        layout.addWidget(self.auto_start_comfyui_check)
        layout.addWidget(self.keep_comfyui_check)
        layout.addWidget(self.test_mode_check)

        actions = QHBoxLayout()
        self.start_button = QPushButton("开始生图")
        self.start_button.setObjectName("primaryButton")
        self.start_button.clicked.connect(self.start_job)
        self.stop_button = QPushButton("停止任务")
        self.stop_button.setObjectName("ghostButton")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_job)
        self.open_output_button = QPushButton("打开输出目录")
        self.open_output_button.setObjectName("ghostButton")
        self.open_output_button.setEnabled(False)
        self.open_output_button.clicked.connect(self.open_output_dir)
        actions.addWidget(self.start_button)
        actions.addWidget(self.stop_button)
        actions.addWidget(self.open_output_button)
        layout.addLayout(actions)
        layout.addStretch(1)
        return panel

    def _build_task_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("任务清单")
        title.setObjectName("panelTitle")
        self.task_sort_combo = QComboBox()
        self.task_sort_combo.addItems(["按时间（新到旧）", "按时间（旧到新）"])
        self.task_sort_combo.currentTextChanged.connect(self._on_task_sort_changed)
        self.status_label = QLabel("等待开始")
        self.status_label.setObjectName("statusPill")
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(self.task_sort_combo)
        top.addWidget(self.status_label)
        layout.addLayout(top)

        hint = QLabel("单击或双击任务可查看日志、任务进度和产物目录。")
        hint.setObjectName("cardSubtitle")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.task_list = QListWidget()
        self.task_list.setObjectName("eventList")
        self.task_list.itemClicked.connect(self.show_task_detail)
        self.task_list.itemDoubleClicked.connect(self.show_task_detail)
        layout.addWidget(self.task_list, stretch=1)
        return panel

    def _build_task_detail_dialog(self, record: LocalImageTaskRecord) -> TaskDetailDialog:
        return TaskDetailDialog(record, self)

    def build_job(self) -> LocalImageJob:
        return LocalImageJob(
            prefix=self.prefix_combo.currentText(),
            start_number=self.start_spin.value(),
            count=self.count_spin.value(),
            style_name=self.style_combo.currentText(),
            steps=self.steps_spin.value(),
            seed=self.seed_spin.value(),
            test_mode=self.test_mode_check.isChecked(),
            auto_start_comfyui=self.auto_start_comfyui_check.isChecked(),
            keep_comfyui=self.keep_comfyui_check.isChecked(),
            gallery_root=self.gallery_root,
            mockup_root=self.mockup_root,
            xlsx_root=self.xlsx_root,
        )

    def start_job(self) -> None:
        if self.process is not None:
            return

        job = self.build_job()
        self.current_task = self._create_task_record(job)
        missing_resource_message = self._missing_posai_resource_message(job)
        if missing_resource_message:
            self._update_current_task(status="等待资源配置", stage_text="等待资源配置", progress_percent=0)
            self.status_label.setText("等待资源配置")
            self._append_log(missing_resource_message)
            self._flush_persist()
            return

        comfy_status = self.comfyui_service.ensure_ready(
            auto_start=job.auto_start_comfyui,
            timeout_seconds=240,
            logger=self._append_log,
        )
        self._append_log(comfy_status.message)
        if not comfy_status.ready:
            self._update_current_task(status="等待 ComfyUI", stage_text="等待 ComfyUI", progress_percent=0)
            self.status_label.setText("等待 ComfyUI")
            return

        program, args, cwd = self.adapter.local_image_command(job)
        self._append_log(f"启动任务：{self.current_task.title}")
        self._append_log(f"即将启动命令：{program} {' '.join(args)}")
        self._append_log(f"工作目录：{cwd}")

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
            started_signal.connect(self._on_process_started)
        state_changed_signal = getattr(process, "stateChanged", None)
        if state_changed_signal is not None:
            state_changed_signal.connect(self._on_process_state_changed)
        self.process = process
        self._stdout_buffer = ""
        self._stderr_buffer = ""
        self._task_started_at = time.time()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.open_output_button.setEnabled(False)
        self._update_current_task(status="运行中", stage_text="准备启动", progress_percent=5)
        self.status_label.setText("运行中")
        self.no_output_timer.start(15000)
        process.start()

    def _create_task_record(self, job: LocalImageJob) -> LocalImageTaskRecord:
        mode_text = "测试模式" if job.test_mode else "完整模式"
        if job.test_mode:
            title = f"{mode_text} {job.prefix} {job.style_name} {job.count} 张"
        else:
            title = f"{mode_text} {job.prefix}-{job.start_number} 起 {job.count} 张"
        record = LocalImageTaskRecord(
            task_id=datetime.now().strftime("%Y%m%d%H%M%S"),
            mode_text=mode_text,
            title=title,
            job=job,
            status="等待启动",
            stage_text="待启动",
            progress_percent=0,
        )
        self.tasks.append(record)
        self._rebuild_task_list()
        self._dirty_task_ids.add(record.task_id)
        self._flush_persist()
        return record

    def _missing_posai_resource_message(self, job: LocalImageJob) -> str:
        if job.test_mode:
            return ""
        missing: list[str] = []
        if not self.posai_comfyui_dir or not Path(self.posai_comfyui_dir).exists():
            missing.append("ComfyUI 安装目录")
        if not self.posai_model_root or not Path(self.posai_model_root).exists():
            missing.append("模型目录")
        if not missing:
            return ""
        return "PosAiImg 资源未配置完整，请先到设置页下载或配置：" + "、".join(missing)

    def stop_job(self) -> None:
        if self.process is None:
            return
        self._append_log("正在停止任务...")
        self.process.kill()

    def open_output_dir(self) -> None:
        if self.current_task is None:
            return
        path = self.current_task.product_dir or self.current_task.print_dir
        if not path:
            return
        try:
            os.startfile(path)  # noqa: S606
        except Exception:
            subprocess.Popen(["explorer", path])

    def _read_stdout(self) -> None:
        if self.process is None:
            return
        text = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._stdout_buffer += text
        if text.strip():
            self.no_output_timer.stop()
        self._append_log(text.rstrip())
        self._update_progress_from_text(text)

    def _read_stderr(self) -> None:
        if self.process is None:
            return
        text = bytes(self.process.readAllStandardError()).decode("utf-8", errors="replace")
        self._stderr_buffer += text
        if text.strip():
            self.no_output_timer.stop()
        self._append_log(text.rstrip())

    def _on_process_started(self) -> None:
        process_id = self.process.processId() if self.process is not None else 0
        self._append_log(f"生图进程已启动，PID={process_id}")

    def _on_process_state_changed(self, state: int) -> None:
        state_map = {
            QProcess.NotRunning: "未运行",
            QProcess.Starting: "启动中",
            QProcess.Running: "运行中",
        }
        self._append_log(f"进程状态变化：{state_map.get(state, '未知')}")

    def _on_process_finished(self, exit_code: int, _exit_status) -> None:
        process = self.process
        if process is None:
            return

        stdout = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
        stderr = bytes(process.readAllStandardError()).decode("utf-8", errors="replace")
        if stdout.strip():
            self._stdout_buffer += stdout
            self._append_log(stdout.rstrip())
        if stderr.strip():
            self._stderr_buffer += stderr
            self._append_log(stderr.rstrip())

        self.process = None
        self.no_output_timer.stop()
        self._task_started_at = 0.0
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

        if exit_code == 0:
            summary = self.adapter.parse_finished_result(
                self._stdout_buffer,
                self.current_task.job if self.current_task else LocalImageJob(),
            )
            status_text = "完成" if summary.ok else "完成但未解析"
            self._update_current_task(
                status=status_text,
                stage_text="已完成" if summary.ok else "待确认",
                progress_percent=100,
                print_dir=summary.print_dir,
                product_dir=summary.mockup_dir,
                xlsx_path=summary.xlsx_path,
            )
            self.status_label.setText(status_text)
            self.open_output_button.setEnabled(bool(summary.print_dir or summary.mockup_dir))
            self._append_log(summary.message)
            self._flush_persist()
            return

        message = f"任务失败，退出码 {exit_code}"
        self._update_current_task(status="失败", stage_text="失败", progress_percent=0)
        self.status_label.setText("失败")
        self._append_log(message)
        self._flush_persist()

    def _on_process_error(self, error) -> None:
        self.process = None
        self.no_output_timer.stop()
        self._task_started_at = 0.0
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("启动失败")
        self._update_current_task(status="启动失败", stage_text="启动失败", progress_percent=0)
        message = f"生图进程启动失败：{error}"
        self._append_log(message)
        self._flush_persist()
        log_exception("local-image-process", RuntimeError(message))

    def _append_log(self, text: str) -> None:
        if not text:
            return
        if self.current_task is None:
            return
        time_text = datetime.now().strftime("%H:%M:%S")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            self.current_task.logs.append(f"{time_text}  {stripped}")
        self._touch_task(self.current_task)
        self._refresh_task_detail_dialog()

    def _update_progress_from_text(self, text: str) -> None:
        if self.current_task is None:
            return
        if "Queued " in text:
            self._set_task_progress(min(30, self.current_task.progress_percent + 6), "排队")
        if "Saved " in text:
            self._set_task_progress(min(95, max(self.current_task.progress_percent, self.current_task.progress_percent + 10)), "生成")
        if "Done. Exported " in text:
            self._set_task_progress(100, "已完成")

    def _warn_if_no_output_yet(self) -> None:
        if self.process is None:
            return
        if self._stdout_buffer.strip() or self._stderr_buffer.strip():
            return
        waited_seconds = max(0, int(time.time() - self._task_started_at)) if self._task_started_at else 0
        state = getattr(self.process, "state", lambda: None)()
        state_text = "运行中" if state == QProcess.Running else ("启动中" if state == QProcess.Starting else "未知")
        self._append_log(
            f"暂时还没有收到脚本输出，已等待 {waited_seconds} 秒。当前进程状态：{state_text}。"
            "常见原因是 ComfyUI 尚未启动、conda 环境启动较慢，或脚本仍在初始化。"
        )

    def _set_task_progress(self, percent: int, stage_text: str) -> None:
        if self.current_task is None:
            return
        self._update_current_task(
            status=self.current_task.status,
            stage_text=stage_text,
            progress_percent=max(0, min(100, percent)),
        )

    def _update_current_task(
        self,
        status: str,
        stage_text: str | None = None,
        progress_percent: int | None = None,
        print_dir: str = "",
        product_dir: str = "",
        xlsx_path: str = "",
    ) -> None:
        if self.current_task is None:
            return
        self.current_task.status = status
        if stage_text is not None:
            self.current_task.stage_text = stage_text
        if progress_percent is not None:
            self.current_task.progress_percent = progress_percent
        if print_dir:
            self.current_task.print_dir = print_dir
        if product_dir:
            self.current_task.product_dir = product_dir
        if xlsx_path:
            self.current_task.xlsx_path = xlsx_path
        self._touch_task(self.current_task)
        self._refresh_task_detail_dialog()

    def _refresh_task_item(self, record: LocalImageTaskRecord) -> None:
        item = self._task_item(record)
        if item is None:
            self._rebuild_task_list()
            return
        item.setText(
            f"{_format_task_timestamp(record.task_id)}  {record.title}  {record.status} · {record.stage_text} {record.progress_percent}%"
        )

    def _task_item(self, record: LocalImageTaskRecord) -> QListWidgetItem | None:
        for index in range(self.task_list.count()):
            item = self.task_list.item(index)
            if item is not None and item.data(Qt.UserRole) == record.task_id:
                return item
        return None

    def _touch_task(self, record: LocalImageTaskRecord | None) -> None:
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

    def _refresh_task_detail_dialog(self) -> None:
        if self.task_detail_dialog is not None and self.task_detail_dialog.isVisible():
            self.task_detail_dialog.refresh(self.task_detail_dialog.record)

    def _sync_mode_controls(self, checked: bool) -> None:
        self.start_spin.setEnabled(not checked)
        if not self._loading_preferences:
            self._save_preferences()

    def _load_preferences(self) -> None:
        self._loading_preferences = True
        settings = self.settings_store.load()
        self.gallery_root = settings.posai_gallery_root
        self.mockup_root = settings.posai_mockup_root
        self.xlsx_root = settings.posai_xlsx_root
        self.posai_comfyui_dir = settings.posai_comfyui_dir
        self.posai_model_root = settings.posai_model_root
        self.task_store = self._build_task_store(settings.program_data_dir)
        self.auto_start_comfyui_check.setChecked(settings.local_image_auto_start_comfyui)
        self.keep_comfyui_check.setChecked(settings.local_image_keep_comfyui)
        self.test_mode_check.setChecked(settings.local_image_test_mode)
        self.auto_start_comfyui_check.toggled.connect(self._save_preferences)
        self.keep_comfyui_check.toggled.connect(self._save_preferences)
        self.test_mode_check.toggled.connect(self._save_preferences)
        self._refresh_start_number(self.prefix_combo.currentText())
        self._sync_mode_controls(self.test_mode_check.isChecked())
        self._loading_preferences = False

    def _save_preferences(self, *_args) -> None:
        if self._loading_preferences:
            return
        settings = self.settings_store.load()
        settings.local_image_auto_start_comfyui = self.auto_start_comfyui_check.isChecked()
        settings.local_image_keep_comfyui = self.keep_comfyui_check.isChecked()
        settings.local_image_test_mode = self.test_mode_check.isChecked()
        self.settings_store.save(settings)

    def _refresh_start_number(self, prefix: str) -> None:
        if self._loading_preferences:
            return
        fallback = self.start_spin.value() or (1421 if prefix == "BO" else 3113)
        posai = resolve_project_dir("posaiimg")
        gallery_root = self.gallery_root or (str(posai / "图库") if posai else str(default_prints_dir()))
        suggested = suggest_next_start(prefix, gallery_root, fallback)
        self.start_spin.setValue(suggested)

    def show_task_detail(self, item: QListWidgetItem) -> None:
        index = self.task_list.row(item)
        ordered_tasks = self._ordered_tasks()
        if index < 0 or index >= len(ordered_tasks):
            return
        record = ordered_tasks[index]
        dialog = self._build_task_detail_dialog(record)
        self.task_detail_dialog = dialog
        dialog.exec_()
        if self.task_detail_dialog is dialog:
            self.task_detail_dialog = None

    def _build_task_store(self, program_data_dir: str) -> TaskStore | None:
        base_dir = (program_data_dir or "").strip()
        if not base_dir:
            return None
        return TaskStore(base_dir, "local_image_tasks")

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
        records: list[LocalImageTaskRecord] = []
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

    def closeEvent(self, event) -> None:  # noqa: N802
        self._flush_persist()
        super().closeEvent(event)

    def _current_tasks_file_mtime(self) -> float | None:
        if self.task_store is None or not self.task_store.path.exists():
            return None
        return self.task_store.path.stat().st_mtime

    def _remember_tasks_file_mtime(self) -> None:
        self._tasks_file_mtime = self._current_tasks_file_mtime()

    def _ordered_tasks(self) -> list[LocalImageTaskRecord]:
        reverse = self.task_sort_combo.currentText() != "按时间（旧到新）" if hasattr(self, "task_sort_combo") else True
        return sorted(self.tasks, key=lambda record: record.task_id, reverse=reverse)

    def _rebuild_task_list(self) -> None:
        self.task_list.clear()
        for record in self._ordered_tasks():
            item = QListWidgetItem("")
            item.setData(Qt.UserRole, record.task_id)
            self.task_list.addItem(item)
            self._refresh_task_item(record)

    def _on_task_sort_changed(self, _text: str) -> None:
        self._rebuild_task_list()

    def _task_to_dict(self, record: LocalImageTaskRecord) -> dict:
        return {
            "task_id": record.task_id,
            "mode_text": record.mode_text,
            "title": record.title,
            "status": record.status,
            "stage_text": record.stage_text,
            "progress_percent": record.progress_percent,
            "logs": list(record.logs),
            "print_dir": record.print_dir,
            "product_dir": record.product_dir,
            "xlsx_path": record.xlsx_path,
            "job": {
                "prefix": record.job.prefix,
                "start_number": record.job.start_number,
                "count": record.job.count,
                "style_name": record.job.style_name,
                "steps": record.job.steps,
                "width": record.job.width,
                "height": record.job.height,
                "seed": record.job.seed,
                "test_mode": record.job.test_mode,
                "auto_start_comfyui": record.job.auto_start_comfyui,
                "keep_comfyui": record.job.keep_comfyui,
                "gallery_root": record.job.gallery_root,
                "mockup_root": record.job.mockup_root,
                "xlsx_root": record.job.xlsx_root,
            },
        }

    def _task_from_dict(self, payload: dict) -> LocalImageTaskRecord | None:
        job_payload = payload.get("job") or {}
        if not isinstance(job_payload, dict):
            return None
        job = LocalImageJob(
            prefix=str(job_payload.get("prefix") or "BO"),
            start_number=int(job_payload.get("start_number") or 1421),
            count=max(1, int(job_payload.get("count") or 10)),
            style_name=str(job_payload.get("style_name") or "仿油彩名画风格竖版印花"),
            steps=int(job_payload.get("steps") or 28),
            width=int(job_payload.get("width") or 832),
            height=int(job_payload.get("height") or 1216),
            seed=int(job_payload.get("seed") or 2026061702),
            test_mode=bool(job_payload.get("test_mode", True)),
            auto_start_comfyui=bool(job_payload.get("auto_start_comfyui", False)),
            keep_comfyui=bool(job_payload.get("keep_comfyui", True)),
            gallery_root=str(job_payload.get("gallery_root") or ""),
            mockup_root=str(job_payload.get("mockup_root") or ""),
            xlsx_root=str(job_payload.get("xlsx_root") or ""),
        )
        return LocalImageTaskRecord(
            task_id=str(payload.get("task_id") or ""),
            mode_text=str(payload.get("mode_text") or "已恢复"),
            title=str(payload.get("title") or "本地生图"),
            job=job,
            status=str(payload.get("status") or "已恢复"),
            stage_text=str(payload.get("stage_text") or "已恢复"),
            progress_percent=max(0, min(100, int(payload.get("progress_percent") or 0))),
            logs=[str(line) for line in (payload.get("logs") or [])],
            print_dir=str(payload.get("print_dir") or ""),
            product_dir=str(payload.get("product_dir") or ""),
            xlsx_path=str(payload.get("xlsx_path") or ""),
        )

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
