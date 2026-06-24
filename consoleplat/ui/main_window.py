from __future__ import annotations

from functools import partial

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QFrame,
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
from consoleplat.models import DEFAULT_NAV_ITEMS, PAGE_TITLES, ShellState
from consoleplat.paths import resource_path
from consoleplat.ui.ai_edit_page import AIEditPage
from consoleplat.ui.apply_goods_page import ApplyGoodsPage
from consoleplat.ui.local_image_page import LocalImagePage
from consoleplat.ui.monitor_page import MonitorPage
from consoleplat.ui.product_publish_page import ProductPublishPage
from consoleplat.ui.putaway_page import PutawayPage
from consoleplat.ui.settings_page import SettingsPage
from consoleplat.ui.theme import APP_STYLE


PAGE_BODIES = {
    "putaway": "这里会承接 PutawayAiRobot 的同步与唤起。",
    "apply": "这里会承接申请、合规和后置流程。",
}


class NavButton(QPushButton):
    def __init__(self, icon: str, title: str, *, large_icon: bool = True) -> None:
        super().__init__()
        self.setObjectName("navButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self.setAutoExclusive(True)
        self.setFixedHeight(58)
        self.setAccessibleName(title)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(2)

        icon_label = QLabel(icon)
        icon_label.setObjectName("navIcon")
        icon_label.setAlignment(Qt.AlignCenter)
        font = icon_label.font()
        font.setPointSize(36 if large_icon else 14)
        icon_label.setFont(font)

        title_label = QLabel(title)
        title_label.setObjectName("navTitle")
        title_label.setAlignment(Qt.AlignCenter)

        layout.addStretch(1)
        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addStretch(1)


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

        root_layout.addWidget(self._build_sidebar())
        root_layout.addWidget(self._build_content(), stretch=1)
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
            button = NavButton(item.icon, item.title, large_icon=item.key != "settings")
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
        if key == "monitor":
            return MonitorPage()
        if key == "publish":
            return ProductPublishPage()
        if key == "local_image":
            return LocalImagePage()
        if key == "ai_edit":
            return AIEditPage()
        if key == "putaway":
            return PutawayPage()
        if key == "apply":
            return ApplyGoodsPage()
        if key == "settings":
            return SettingsPage()

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(QLabel(PAGE_TITLES.get(key, key)))
        layout.addWidget(QLabel(PAGE_BODIES.get(key, "")))
        layout.addStretch(1)
        return page

    def activate_page(self, key: str) -> None:
        self.state.active_page = key
        self.stack.setCurrentIndex(self.page_indexes[key])
        for item_key, button in self.nav_buttons.items():
            is_active = item_key == key
            button.setChecked(is_active)
            button.setProperty("active", "true" if is_active else "false")
            button.style().unpolish(button)
            button.style().polish(button)

    def closeEvent(self, event) -> None:  # noqa: N802
        for monitor_page in self.findChildren(MonitorPage):
            monitor_page._close_monitor_browser_pages()
        super().closeEvent(event)
