from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QEvent, Qt, QTimer
from PyQt5.QtWidgets import QApplication, QFrame, QLabel, QMessageBox, QStackedWidget, QVBoxLayout, QWidget

from consoleplat.adapters.putaway_adapter import PutawayAdapter
from consoleplat.config import SettingsStore, resolve_project_dir


class PutawayPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = SettingsStore().load()
        project_dir = resolve_project_dir("putaway", self.settings.putaway_project_dir)
        data_dir = Path(self.settings.putaway_data_dir).expanduser() if self.settings.putaway_data_dir else (
            project_dir / "data" if project_dir else None
        )
        log_dir = Path(self.settings.putaway_log_dir).expanduser() if self.settings.putaway_log_dir else (
            project_dir / "log" if project_dir else None
        )
        self._path_error = "" if project_dir else "未找到 PutawayAiRobot 项目，请在设置中指定上架项目目录。"
        self.adapter = PutawayAdapter(
            project_dir=project_dir or Path("PutawayAiRobot"),
            data_dir_path=data_dir or Path("PutawayAiRobot/data"),
            log_dir_path=log_dir or Path("PutawayAiRobot/log"),
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
        header.setObjectName("putawayStatusAnchor")
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
        self.container_panel.setObjectName("putawayEmbedAnchor")
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
        if self._path_error:
            self.status_label.setText("内嵌上架界面加载失败")
            self.error_label.setText(self._path_error)
            self.error_label.show()
            return
        self.status_label.setText("正在加载内嵌上架界面…")
        QApplication.processEvents()

        try:
            self.embedded_widget = self.adapter.build_embedded_widget(
                parent=self.container_panel,
                home_url=self.settings.putaway_home_url,
                album_url=self.settings.putaway_album_url,
            )
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

    def prepare_product_import_from_publish(self, record: object) -> None:
        self._load_embedded()
        if self.embedded_widget is None:
            return
        try:
            self._activate_product_data_tab()
            self._set_latest_excel_dir()
            self._call_embedded_method("clear_product_rows", "清空产品数据")
            self._call_embedded_method("import_from_latest_excel", "导入最新Excel")
        except Exception as exc:
            self.error_label.setText(str(exc))
            self.error_label.show()
            QMessageBox.critical(self, "上架数据导入失败", str(exc))
            return
        task_name = str(getattr(record, "task_name", "") or "发布任务")
        self.error_label.hide()
        self.status_label.setText(f"已从发布任务进入产品数据导入：{task_name}")

    def _activate_product_data_tab(self) -> None:
        tabs = getattr(self.embedded_widget, "tabs", None)
        if tabs is None:
            raise AttributeError("PutawayAiRobot 内嵌界面缺少 tabs，无法切换到产品数据页。")
        for index in range(tabs.count()):
            if tabs.tabText(index) == "产品数据":
                tabs.setCurrentIndex(index)
                return
        raise ValueError("PutawayAiRobot 内嵌界面未找到“产品数据”标签。")

    def _set_latest_excel_dir(self) -> None:
        input_widget = getattr(self.embedded_widget, "latest_excel_dir_input", None)
        if input_widget is None:
            return
        data_dir = str(self.settings.putaway_data_dir or self.adapter.data_dir_path)
        input_widget.setText(data_dir)

    def _call_embedded_method(self, method_name: str, action_name: str) -> None:
        method = getattr(self.embedded_widget, method_name, None)
        if method is None or not callable(method):
            raise AttributeError(f"PutawayAiRobot 内嵌界面缺少“{action_name}”方法。")
        method()
