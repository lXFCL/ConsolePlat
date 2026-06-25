from __future__ import annotations

from functools import partial

from PyQt5.QtCore import QProcess, QThread, QTimer, Qt
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
from consoleplat.services.version_check_service import UpdateCheckWorker, UpdateProxyConfig
from consoleplat.ui.ai_edit_page import AIEditPage
from consoleplat.ui.apply_goods_page import ApplyGoodsPage
from consoleplat.ui.local_image_page import LocalImagePage
from consoleplat.ui.monitor_page import MonitorPage
from consoleplat.ui.product_publish_page import ProductPublishPage
from consoleplat.ui.putaway_page import PutawayPage
from consoleplat.ui.settings_page import SettingsPage
from consoleplat.ui.theme import APP_STYLE, get_app_style


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
        self.badge_label = QLabel("运行")
        self.badge_label.setObjectName("navBadge")
        self.badge_label.setAlignment(Qt.AlignCenter)
        self.badge_label.hide()

        layout.addStretch(1)
        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(self.badge_label)
        layout.addStretch(1)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.state = ShellState()
        self.nav_buttons: dict[str, QPushButton] = {}
        self.page_indexes: dict[str, int] = {}
        self.pages: dict[str, QWidget] = {}
        self._page_placeholders: dict[str, QWidget] = {}
        self._built: set[str] = set()
        self._update_check_thread: QThread | None = None
        self._update_check_worker: UpdateCheckWorker | None = None

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setWindowIcon(QIcon(str(resource_path("assets/images/app_icon.ico"))))
        settings = SettingsStore().load()
        self.resize(settings.startup_width, settings.startup_height)
        self.setMinimumSize(920, 600)
        self.setStyleSheet(get_app_style(settings.theme_name, settings.bg_image_path))
        self._build_ui()
        self.activate_page(self.state.active_page)
        QTimer.singleShot(1500, self._maybe_check_update_on_startup)

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
        self.status_pill = QLabel("框架预览")
        self.status_pill.setObjectName("statusPill")
        header.addWidget(app_title)
        header.addStretch(1)
        header.addWidget(self.status_pill)
        layout.addLayout(header)

        self.stack = QStackedWidget()
        for item in DEFAULT_NAV_ITEMS:
            placeholder = self._create_loading_placeholder(item.key)
            self._page_placeholders[item.key] = placeholder
            self.page_indexes[item.key] = self.stack.addWidget(placeholder)
        layout.addWidget(self.stack, stretch=1)
        return content

    def _create_loading_placeholder(self, key: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        label = QLabel(f"正在加载{PAGE_TITLES.get(key, key)}界面…")
        label.setObjectName("sectionTitle")
        label.setAlignment(Qt.AlignCenter)
        hint = QLabel("首次打开会准备对应模块，请稍候。")
        hint.setObjectName("cardSubtitle")
        hint.setAlignment(Qt.AlignCenter)
        layout.addStretch(1)
        layout.addWidget(label)
        layout.addWidget(hint)
        layout.addStretch(1)
        return page

    def _create_page(self, key: str) -> QWidget:
        if key == "monitor":
            page = MonitorPage()
            page.request_open_publish.connect(self._open_publish_from_monitor)
            return page
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
            settings_page = SettingsPage()
            settings_page.settings_saved.connect(
                lambda s: self.setStyleSheet(get_app_style(s.theme_name, s.bg_image_path))
            )
            return settings_page

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(QLabel(PAGE_TITLES.get(key, key)))
        layout.addWidget(QLabel(PAGE_BODIES.get(key, "")))
        layout.addStretch(1)
        return page

    def activate_page(self, key: str) -> None:
        self._ensure_page_built(key)
        self.state.active_page = key
        self.stack.setCurrentIndex(self.page_indexes[key])
        for item_key, button in self.nav_buttons.items():
            is_active = item_key == key
            button.setChecked(is_active)
            button.setProperty("active", "true" if is_active else "false")
            button.style().unpolish(button)
            button.style().polish(button)
        self.refresh_task_badges()

    def _maybe_check_update_on_startup(self) -> None:
        settings = SettingsStore().load()
        if not settings.check_update_on_startup or self._update_check_thread is not None:
            return
        proxy = UpdateProxyConfig(
            enabled=settings.update_proxy_enabled,
            host=settings.update_proxy_host,
            port=settings.update_proxy_port,
        )
        thread = QThread(self)
        worker = UpdateCheckWorker(proxy)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_startup_check_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._cleanup_update_check_worker(thread, worker))
        self._update_check_thread = thread
        self._update_check_worker = worker
        thread.start()

    def _cleanup_update_check_worker(self, thread: QThread, worker: UpdateCheckWorker) -> None:
        if self._update_check_thread is thread:
            self._update_check_thread = None
        if self._update_check_worker is worker:
            self._update_check_worker = None

    def _on_startup_check_finished(self, result: dict) -> None:
        self._on_startup_update_result(result)

    def _on_startup_update_result(self, result: dict) -> None:
        if not result.get("ok") or not result.get("has_update"):
            return
        release = result.get("release") or {}
        version = str(release.get("version") or "")
        if not version:
            return
        if version == SettingsStore().load().skipped_update_version:
            return
        self._show_update_available(version)

    def _show_update_available(self, version: str) -> None:
        if not hasattr(self, "status_pill"):
            return
        self.status_pill.setText(f"● 发现新版本 v{version}")
        self.status_pill.setProperty("hasUpdate", "true")
        self.status_pill.setCursor(Qt.PointingHandCursor)
        self.status_pill.style().unpolish(self.status_pill)
        self.status_pill.style().polish(self.status_pill)
        self.status_pill.mousePressEvent = lambda event: self._open_update_settings()

    def _open_update_settings(self) -> None:
        self.activate_page("settings")
        page = self.pages.get("settings")
        if isinstance(page, SettingsPage):
            page.activate_update_tab()

    def refresh_task_badges(self) -> None:
        for key, button in self.nav_buttons.items():
            badge = getattr(button, "badge_label", None)
            if badge is None:
                continue
            page = self.pages.get(key)
            running = bool(page and self._page_has_running_task(page))
            badge.setVisible(running)

    def _page_has_running_task(self, page: QWidget) -> bool:
        process = getattr(page, "process", None)
        if process is not None:
            return True
        processes = getattr(page, "processes", None)
        if processes:
            return True
        current_task = getattr(page, "current_task", None)
        if current_task is not None:
            return True
        return False

    def _ensure_page_built(self, key: str) -> None:
        if key in self._built:
            return

        old_index = self.page_indexes[key]
        placeholder = self._page_placeholders[key]
        page = self._create_page(key)
        self.stack.insertWidget(old_index, page)
        self.stack.removeWidget(placeholder)
        placeholder.deleteLater()

        self.pages[key] = page
        self.page_indexes[key] = old_index
        self._built.add(key)

        for index in range(self.stack.count()):
            widget = self.stack.widget(index)
            for item_key, item_page in self.pages.items():
                if widget is item_page:
                    self.page_indexes[item_key] = index
                    break
            for item_key, item_placeholder in self._page_placeholders.items():
                if item_key not in self._built and widget is item_placeholder:
                    self.page_indexes[item_key] = index
                    break

    def _open_publish_from_monitor(self, context: dict) -> None:
        self.activate_page("publish")
        page = self.pages.get("publish")
        if isinstance(page, ProductPublishPage):
            page.prefill_from_monitor(context)

    def closeEvent(self, event) -> None:  # noqa: N802
        for monitor_page in self.findChildren(MonitorPage):
            monitor_page._close_monitor_browser_pages()
        super().closeEvent(event)
