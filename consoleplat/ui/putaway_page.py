from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

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
        self.embedded_widget: QWidget | None = None

        header = QFrame()
        header.setObjectName("panel")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 18, 22, 18)
        header_layout.setSpacing(8)

        title = QLabel("自动上架")
        title.setObjectName("sectionTitle")
        hint = QLabel("当前页面直接内嵌 PutawayAiRobot 界面；真实发布流程仍由上架程序内部控制，请谨慎操作。")
        hint.setObjectName("cardSubtitle")
        hint.setWordWrap(True)

        header_layout.addWidget(title)
        header_layout.addWidget(hint)
        root.addWidget(header)

        self.container_panel = QFrame()
        self.container_panel.setObjectName("panel")
        container_layout = QVBoxLayout(self.container_panel)
        container_layout.setContentsMargins(22, 18, 22, 18)
        container_layout.setSpacing(12)

        meta_label = QLabel(
            f"项目目录：{self.adapter.project_dir}\n"
            f"data 目录：{self.adapter.data_dir_path}\n"
            f"日志目录：{self.adapter.log_dir_path}"
        )
        meta_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        container_layout.addWidget(meta_label)

        self.status_label = QLabel("正在加载内嵌上架界面…")
        self.status_label.setObjectName("statusPill")
        container_layout.addWidget(self.status_label)

        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.error_label.hide()
        container_layout.addWidget(self.error_label)

        self.open_settings_button = QPushButton("去设置里检查路径")
        self.open_settings_button.setObjectName("ghostButton")
        container_layout.addWidget(self.open_settings_button, alignment=Qt.AlignLeft)

        try:
            self.embedded_widget = self.adapter.build_embedded_widget(parent=self.container_panel)
        except Exception as exc:
            self.embedded_widget = None
            self.status_label.setText("内嵌上架界面加载失败")
            self.error_label.setText(
                "无法加载 PutawayAiRobot 内嵌界面。\n"
                f"错误类型：{type(exc).__name__}\n"
                f"错误信息：{exc}"
            )
            self.error_label.show()
        else:
            self.status_label.setText("已加载 PutawayAiRobot 内嵌界面")
            container_layout.addWidget(self.embedded_widget, stretch=1)

        root.addWidget(self.container_panel, stretch=1)
