from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFormLayout, QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from consoleplat.adapters.putaway_adapter import PutawayAdapter
from consoleplat.config import SettingsStore


class PutawayPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = SettingsStore().load()
        self.adapter = PutawayAdapter(
            project_dir=Path(self.settings.putaway_project_dir or r"E:\1PythonProject\PutawayAiRobot"),
            data_dir_path=Path(self.settings.putaway_data_dir or r"E:\1PythonProject\PutawayAiRobot\data"),
            log_dir_path=Path(self.settings.putaway_log_dir or r"E:\1PythonProject\PutawayAiRobot\log"),
        )
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        header = QFrame()
        header.setObjectName("panel")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 18, 22, 18)
        header_layout.setSpacing(8)

        title = QLabel("自动上架")
        title.setObjectName("sectionTitle")
        hint = QLabel("当前版本先接回 PutawayAiRobot 的目录信息和启动入口，不会在这里直接点击真实发布。")
        hint.setObjectName("cardSubtitle")
        hint.setWordWrap(True)

        header_layout.addWidget(title)
        header_layout.addWidget(hint)
        root.addWidget(header)

        info_panel = QFrame()
        info_panel.setObjectName("panel")
        info_layout = QVBoxLayout(info_panel)
        info_layout.setContentsMargins(22, 18, 22, 18)
        info_layout.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        form.addRow("项目目录", QLabel(str(self.adapter.project_dir)))
        form.addRow("data 目录", QLabel(str(self.adapter.data_dir_path)))
        form.addRow("日志目录", QLabel(str(self.adapter.log_dir_path)))
        info_layout.addLayout(form)

        program, args, cwd = self.adapter.launch_command()
        command_preview = QLabel(f"启动入口：{program} {' '.join(args)}")
        command_preview.setWordWrap(True)
        command_preview.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info_layout.addWidget(command_preview)

        cwd_label = QLabel(f"工作目录：{cwd}")
        cwd_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info_layout.addWidget(cwd_label)

        status_text = "已检测到上架入口脚本" if (self.adapter.project_dir / "browser_dom_automation.py").exists() else "未检测到上架入口脚本"
        self.status_label = QLabel(status_text)
        self.status_label.setObjectName("statusPill")
        info_layout.addWidget(self.status_label)

        self.open_settings_button = QPushButton("去设置里检查路径")
        self.open_settings_button.setObjectName("ghostButton")
        info_layout.addWidget(self.open_settings_button, alignment=Qt.AlignLeft)

        root.addWidget(info_panel)
        root.addStretch(1)
