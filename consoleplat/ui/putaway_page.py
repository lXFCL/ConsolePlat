from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QEvent, Qt, QTimer
from PyQt5.QtWidgets import QApplication, QFrame, QLabel, QStackedWidget, QVBoxLayout, QWidget

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
        self._embed_loaded = False
        self._parent_stack: QStackedWidget | None = None
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

        self.status_label = QLabel("准备加载内嵌上架界面…")
        self.status_label.setObjectName("statusPill")
        container_layout.addWidget(self.status_label)

        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.error_label.hide()
        container_layout.addWidget(self.error_label)

        root.addWidget(self.container_panel, stretch=1)

    def showEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().showEvent(event)
        self._schedule_embedded_load()

    def event(self, event) -> bool:  # noqa: N802 - Qt override
        handled = super().event(event)
        if event.type() == QEvent.ParentChange:
            self._connect_parent_stack()
        return handled

    def _connect_parent_stack(self) -> None:
        parent = self.parentWidget()
        if not isinstance(parent, QStackedWidget) or parent is self._parent_stack:
            return
        self._parent_stack = parent
        parent.currentChanged.connect(self._on_parent_stack_current_changed)

    def _on_parent_stack_current_changed(self, index: int) -> None:
        if self._embed_loaded or self._parent_stack is None or self._parent_stack.widget(index) is not self:
            return
        if self._parent_stack.isVisible():
            self._schedule_embedded_load()
        else:
            self._load_embedded()

    def _schedule_embedded_load(self) -> None:
        if self._embed_loaded:
            return
        QTimer.singleShot(0, self._load_embedded)

    def _load_embedded(self) -> None:
        if self._embed_loaded:
            return
        self._embed_loaded = True
        self.status_label.setText("正在加载内嵌上架界面…")
        QApplication.processEvents()

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
            self.error_label.hide()
            self.container_panel.layout().addWidget(self.embedded_widget, stretch=1)
