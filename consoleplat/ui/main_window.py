from __future__ import annotations

from functools import partial

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from consoleplat import APP_NAME, APP_VERSION
from consoleplat.config import SettingsStore
from consoleplat.models import DEFAULT_NAV_ITEMS, DEFAULT_TASK_CARDS, PAGE_TITLES, ShellState
from consoleplat.paths import resource_path
from consoleplat.ui.components import HeroBanner, TaskCardWidget, make_page_panel
from consoleplat.ui.monitor_page import MonitorPage
from consoleplat.ui.settings_page import SettingsPage
from consoleplat.ui.theme import APP_STYLE


PAGE_BODIES = {
    "monitor": "这里会放店铺实时监控、5 秒刷新设置、待发货提醒和触发记录。当前版本只搭页面框架。",
    "purchase": "这里会衔接 SendGoods 的采集、预览、异常清单和 Excel 输出。",
    "local_image": "这里会衔接 PosAiImg 的本地生图风格、张数、店铺和货号批次。",
    "ai_edit": "这里会放 API Key、参考图片、改图要求、任务进度和结果预览。",
    "outputs": "这里会校验最终透明底、产品图、xlsx，并显示投放到 PutawayAiRobot data 的状态。",
    "putaway": "这里会启动或连接 PutawayAiRobot，并展示自动上架进度。",
    "apply": "这里会配置 ApplyGoods 后置流程、等待时间和人工确认点。",
    "settings": "这里会集中管理项目路径、CDP 地址、刷新间隔、等待时间和密钥存储策略。",
}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.state = ShellState()
        self.nav_buttons: dict[str, QPushButton] = {}
        self.page_indexes: dict[str, int] = {}

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setWindowIcon(QIcon(str(resource_path("assets/images/app_icon.ico"))))
        settings = SettingsStore().load()
        self.resize(settings.startup_width, settings.startup_height)
        self.setMinimumSize(920, 600)
        self.setStyleSheet(APP_STYLE)
        self._build_ui()
        self.activate_page(self.state.active_page)

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = self._build_sidebar()
        content = self._build_content()

        root_layout.addWidget(sidebar)
        root_layout.addWidget(content, stretch=1)
        self.setCentralWidget(root)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(74)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(4, 12, 4, 12)
        layout.setSpacing(7)

        mark = QLabel("CP")
        mark.setAlignment(Qt.AlignCenter)
        mark.setFixedHeight(32)
        mark.setStyleSheet("font-weight: 800; color: #fb78b7;")
        layout.addWidget(mark)

        for item in DEFAULT_NAV_ITEMS:
            button = QPushButton(f"{item.icon}\n{item.title}")
            button.setObjectName("navButton")
            button.setCursor(Qt.PointingHandCursor)
            button.setFixedHeight(58)
            button.clicked.connect(partial(self.activate_page, item.key))
            self.nav_buttons[item.key] = button
            layout.addWidget(button)

        layout.addStretch(1)
        return sidebar

    def _build_content(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 14, 18, 18)
        layout.setSpacing(14)

        header = QHBoxLayout()
        app_title = QLabel(f"{APP_NAME} v{APP_VERSION}")
        app_title.setObjectName("appTitle")
        status = QLabel("框架预览")
        status.setObjectName("statusPill")
        header.addWidget(app_title)
        header.addStretch(1)
        header.addWidget(status)
        layout.addLayout(header)

        self.stack = QStackedWidget()
        for item in DEFAULT_NAV_ITEMS:
            page = self._create_page(item.key)
            self.page_indexes[item.key] = self.stack.addWidget(page)
        layout.addWidget(self.stack, stretch=1)
        return content

    def _create_page(self, key: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        if key == "monitor":
            layout.addWidget(MonitorPage(), stretch=1)
            return page

        if key == "settings":
            layout.addWidget(SettingsPage(), stretch=1)
            return page

        panel = make_page_panel(PAGE_TITLES.get(key, key), PAGE_BODIES[key])
        layout.addWidget(panel)
        layout.addStretch(1)
        return page

    def activate_page(self, key: str) -> None:
        self.state.active_page = key
        self.stack.setCurrentIndex(self.page_indexes[key])
        for item_key, button in self.nav_buttons.items():
            button.setProperty("active", "true" if item_key == key else "false")
            button.style().unpolish(button)
            button.style().polish(button)
