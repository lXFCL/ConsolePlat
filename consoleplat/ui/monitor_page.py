from __future__ import annotations

import json
import os
import subprocess
import sys

from PyQt5.QtCore import QProcess, QTimer, Qt
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QComboBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from consoleplat.paths import resource_path
from consoleplat.adapters.sendgoods_adapter import SendGoodsAdapter
from consoleplat.config import SettingsStore
from consoleplat.services.app_log import log_exception
from consoleplat.services.monitor_service import EmptyMonitorSource, MonitorEvent, MonitorSnapshot
from consoleplat.ui.components import HeroBanner

SHOP_OPTIONS = ("YUHOOBO", "YUHAOBO")


class MetricCard(QFrame):
    def __init__(self, title: str, value: str = "0", accent: str = "#fb78b7") -> None:
        super().__init__()
        self.setObjectName("metricCard")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("metricValue")
        self.title_label = QLabel(title)
        self.title_label.setObjectName("metricTitle")
        marker = QLabel()
        marker.setFixedSize(8, 42)
        marker.setStyleSheet(f"background: {accent}; border-radius: 4px;")

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 12, 14, 12)
        row.setSpacing(12)
        row.addWidget(marker)
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(self.value_label)
        text.addWidget(self.title_label)
        row.addLayout(text)
        row.addStretch(1)

    def set_value(self, value: int) -> None:
        self.value_label.setText(str(value))


class MonitorPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings_store = SettingsStore()
        self.sendgoods_adapter = SendGoodsAdapter()
        self.source = self._build_source()
        self.previous_snapshot: MonitorSnapshot | None = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_snapshot)
        self.metric_cards: dict[str, MetricCard] = {}
        self.is_fetching = False
        self.fetch_process: QProcess | None = None
        self.export_process: QProcess | None = None
        self.cleanup_started = False

        self._build_ui()
        initial = MonitorSnapshot.empty(
            shop_name=self._active_shop_name(),
            refresh_interval_seconds=getattr(self.source, "refresh_interval_seconds", 5),
        )
        self.previous_snapshot = initial
        self.apply_snapshot(initial, 0)

    def _build_source(self):
        settings = self.settings_store.load()
        return EmptyMonitorSource(refresh_interval_seconds=settings.refresh_interval_seconds, shop_name=settings.active_shop)

    def _active_shop_name(self) -> str:
        settings = self.settings_store.load()
        return settings.active_shop or "YUHOOBO"

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("monitorScroll")
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)

        root = QVBoxLayout(content)
        root.setContentsMargins(0, 0, 10, 18)
        root.setSpacing(14)

        hero = HeroBanner(str(resource_path("assets/images/dashboard_hero.png")), background_y_offset=56)
        hero.setMinimumHeight(180)
        hero.setMaximumHeight(210)
        root.addWidget(hero)

        top = QHBoxLayout()
        title = QLabel("商品监控 >")
        title.setObjectName("sectionTitle")
        self.source_label = QLabel("来源：等待刷新")
        self.source_label.setObjectName("statusPill")
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(self.source_label)
        root.addLayout(top)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        for index, (name, accent) in enumerate(
            (("待发货", "#fb78b7"), ("备货件数", "#6ba6ff"), ("高优先级", "#ffbd63"), ("异常提醒", "#8ad7c4"))
        ):
            card = MetricCard(name, accent=accent)
            self.metric_cards[name] = card
            grid.addWidget(card, 0, index)
        root.addLayout(grid)

        control_panel = QFrame()
        control_panel.setObjectName("panel")
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(18, 14, 18, 14)
        control_layout.setSpacing(12)
        control_title = QLabel("刷新控制")
        control_title.setObjectName("panelTitle")
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(2, 120)
        self.interval_spin.setValue(self.settings_store.load().refresh_interval_seconds)
        self.interval_spin.setSuffix(" 秒")
        self.interval_spin.valueChanged.connect(self.update_interval)
        self.shop_combo = QComboBox()
        self.shop_combo.addItems(SHOP_OPTIONS)
        active_shop_index = self.shop_combo.findText(self._active_shop_name())
        self.shop_combo.setCurrentIndex(max(0, active_shop_index))
        self.shop_combo.currentTextChanged.connect(self.update_active_shop)
        self.toggle_button = QPushButton("开始监控")
        self.toggle_button.setObjectName("primaryButton")
        self.toggle_button.clicked.connect(self.toggle_monitor)
        self.manual_button = QPushButton("立即刷新")
        self.manual_button.setObjectName("ghostButton")
        self.manual_button.clicked.connect(self.refresh_snapshot)
        self.export_button = QPushButton("导出备货单")
        self.export_button.setObjectName("ghostButton")
        self.export_button.clicked.connect(self.export_purchase_sheet)
        self.open_export_folder_button = QPushButton("打开文件夹")
        self.open_export_folder_button.setObjectName("ghostButton")
        self.open_export_folder_button.clicked.connect(self.open_export_folder)
        self.last_fetch_label = QLabel("最近刷新：--")
        self.last_fetch_label.setObjectName("cardSubtitle")
        control_layout.addWidget(control_title)
        control_layout.addWidget(QLabel("店铺"))
        control_layout.addWidget(self.shop_combo)
        control_layout.addWidget(self.interval_spin)
        control_layout.addWidget(self.toggle_button)
        control_layout.addWidget(self.manual_button)
        control_layout.addWidget(self.export_button)
        control_layout.addWidget(self.open_export_folder_button)
        control_layout.addStretch(1)
        control_layout.addWidget(self.last_fetch_label)
        root.addWidget(control_panel)

        table_panel = QFrame()
        table_panel.setObjectName("panel")
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(18, 16, 18, 16)
        table_layout.setSpacing(10)
        table_title = QLabel("待处理商品")
        table_title.setObjectName("panelTitle")
        self.order_empty_state = QFrame()
        self.order_empty_state.setObjectName("subPanel")
        self.order_empty_state.setMinimumHeight(132)
        empty_layout = QVBoxLayout(self.order_empty_state)
        empty_layout.setContentsMargins(18, 20, 18, 20)
        empty_layout.setSpacing(8)
        empty_layout.setAlignment(Qt.AlignCenter)
        self.order_empty_title = QLabel("监控尚未启动")
        self.order_empty_title.setObjectName("monitorEmptyTitle")
        self.order_empty_title.setAlignment(Qt.AlignCenter)
        self.order_empty_title.setMinimumHeight(30)
        self.order_empty_hint = QLabel("点击上方“开始监控”或“立即刷新”后，这里会显示待处理商品。")
        self.order_empty_hint.setObjectName("monitorEmptyHint")
        self.order_empty_hint.setAlignment(Qt.AlignCenter)
        self.order_empty_hint.setWordWrap(True)
        self.order_empty_hint.setMaximumWidth(420)
        self.order_empty_hint.setMinimumHeight(38)
        empty_layout.addWidget(self.order_empty_title)
        empty_layout.addWidget(self.order_empty_hint)
        self.order_table = QTableWidget(0, 8)
        self.order_table.setHorizontalHeaderLabels(["序号", "备货单", "货号", "SKU", "颜色", "尺码", "件数", "状态"])
        self.order_table.horizontalHeader().setStretchLastSection(True)
        self.order_table.verticalHeader().setVisible(False)
        self.order_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.order_table.setAlternatingRowColors(True)
        self.order_table.setMinimumHeight(230)
        self.order_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        table_layout.addWidget(table_title)
        table_layout.addWidget(self.order_empty_state)
        table_layout.addWidget(self.order_table)
        root.addWidget(table_panel)

        event_panel = QFrame()
        event_panel.setObjectName("panel")
        event_layout = QVBoxLayout(event_panel)
        event_layout.setContentsMargins(18, 16, 18, 16)
        event_layout.setSpacing(10)
        event_title = QLabel("事件流")
        event_title.setObjectName("panelTitle")
        self.event_list = QListWidget()
        self.event_list.setObjectName("eventList")
        self.event_list.setMinimumHeight(170)
        event_layout.addWidget(event_title)
        event_layout.addWidget(self.event_list)
        root.addWidget(event_panel)
        root.addStretch(1)

    def update_interval(self, seconds: int) -> None:
        self.source.refresh_interval_seconds = seconds
        settings = self.settings_store.load()
        settings.refresh_interval_seconds = seconds
        self.settings_store.save(settings)
        if self.timer.isActive():
            self.timer.start(seconds * 1000)

    def update_active_shop(self, shop_name: str) -> None:
        settings = self.settings_store.load()
        settings.active_shop = shop_name.strip() or "YUHOOBO"
        self.settings_store.save(settings)
        self.page_size_configured = False
        self.source = self._build_source()
        self.previous_snapshot = MonitorSnapshot.empty(
            shop_name=settings.active_shop,
            refresh_interval_seconds=self.interval_spin.value(),
            message="已切换监控店铺，等待刷新真实页面数据",
        )
        self.apply_snapshot(self.previous_snapshot, 0)

    def toggle_monitor(self) -> None:
        if self.timer.isActive():
            self.timer.stop()
            self.toggle_button.setText("开始监控")
            return
        self.timer.start(self.interval_spin.value() * 1000)
        self.toggle_button.setText("停止监控")
        self.refresh_snapshot()

    def refresh_snapshot(self) -> None:
        if self.is_fetching:
            return
        self.is_fetching = True
        self.manual_button.setEnabled(False)
        self.source_label.setText("来源：正在读取页面...")
        process = QProcess(self)
        process.setProgram(sys.executable)
        process.setArguments(["-m", "consoleplat.services.monitor_fetch_cli"])
        process.finished.connect(self._on_fetch_process_finished)
        process.errorOccurred.connect(self._on_fetch_process_error)
        self.fetch_process = process
        process.start()

    def export_purchase_sheet(self) -> None:
        if self.export_process is not None:
            return
        self.export_button.setEnabled(False)
        self.source_label.setText("来源：正在导出备货单...")
        program, args = self.sendgoods_adapter.export_command()
        process = QProcess(self)
        process.setProgram(program)
        process.setArguments(args)
        process.finished.connect(self._on_export_process_finished)
        process.errorOccurred.connect(self._on_export_process_error)
        self.export_process = process
        process.start()

    def open_export_folder(self) -> None:
        folder = self.sendgoods_adapter.export_dir(getattr(self, "_last_export_payload", None))
        folder.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(folder))  # noqa: S606 - user explicitly opens a local folder.
        except Exception:
            subprocess.Popen(["explorer", str(folder)])

    def _on_fetch_process_finished(self, _exit_code: int, _exit_status) -> None:
        process = self.fetch_process
        if process is None:
            return
        stdout = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace").strip()
        stderr = bytes(process.readAllStandardError()).decode("utf-8", errors="replace").strip()
        self.fetch_process = None
        self.is_fetching = False
        self.manual_button.setEnabled(True)
        if stderr:
            log_exception("monitor-fetch-stderr", RuntimeError(stderr[-1000:]))
        try:
            payload = json.loads(stdout)
        except Exception as exc:  # noqa: BLE001
            log_exception("monitor-fetch-json", exc)
            self.on_fetch_failed(f"读取进程没有返回有效结果：{stderr or stdout[-300:]}")
            return
        if payload.get("ok"):
            self.on_snapshot_ready(MonitorSnapshot.from_dict(payload.get("snapshot") or {}))
            return
        prefix = "LOGIN_REQUIRED::" if payload.get("kind") == "login" else ""
        self.on_fetch_failed(f"{prefix}{payload.get('message') or '读取失败'}")

    def _handle_fetch_payload(self, payload: dict) -> None:
        if payload.get("ok"):
            self.on_snapshot_ready(MonitorSnapshot.from_dict(payload.get("snapshot") or {}))
            return
        prefix = "LOGIN_REQUIRED::" if payload.get("kind") == "login" else ""
        self.on_fetch_failed(f"{prefix}{payload.get('message') or '读取失败'}")

    def _on_fetch_process_error(self, error) -> None:
        self.fetch_process = None
        self.is_fetching = False
        self.manual_button.setEnabled(True)
        self.on_fetch_failed(f"读取进程启动失败：{error}")

    def _on_export_process_finished(self, _exit_code: int, _exit_status) -> None:
        process = self.export_process
        if process is None:
            return
        stdout = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace").strip()
        stderr = bytes(process.readAllStandardError()).decode("utf-8", errors="replace").strip()
        self.export_process = None
        self.export_button.setEnabled(True)
        if stderr:
            log_exception("sendgoods-export-stderr", RuntimeError(stderr[-1000:]))
        try:
            payload = json.loads(stdout)
        except Exception as exc:  # noqa: BLE001
            log_exception("sendgoods-export-json", exc)
            payload = {"ok": False, "message": f"导出进程没有返回有效结果：{stderr or stdout[-300:]}"}
        self._last_export_payload = payload
        base = self.previous_snapshot or MonitorSnapshot.empty(
            shop_name=self._active_shop_name(),
            refresh_interval_seconds=self.interval_spin.value(),
        )
        snapshot = self.sendgoods_adapter.apply_export_result(base, payload)
        self.previous_snapshot = snapshot
        self.apply_snapshot(snapshot, 0)

    def _on_export_process_error(self, error) -> None:
        self.export_process = None
        self.export_button.setEnabled(True)
        base = self.previous_snapshot or MonitorSnapshot.empty(
            shop_name=self._active_shop_name(),
            refresh_interval_seconds=self.interval_spin.value(),
        )
        snapshot = self.sendgoods_adapter.apply_export_result(
            base,
            {"ok": False, "message": f"导出进程启动失败：{error}"},
        )
        self.previous_snapshot = snapshot
        self.apply_snapshot(snapshot, 0)

    def on_snapshot_ready(self, snapshot: MonitorSnapshot) -> None:
        try:
            new_orders = snapshot.diff_new_orders(self.previous_snapshot)
            self.previous_snapshot = snapshot
            self.apply_snapshot(snapshot, len(new_orders))
        except Exception as exc:  # noqa: BLE001 - keep UI alive and surface the issue.
            log_exception("monitor-ui-success", exc)
            self.on_fetch_failed(f"界面刷新失败：{exc}")
        finally:
            self.manual_button.setEnabled(True)

    def on_fetch_failed(self, message: str) -> None:
        try:
            needs_login = message.startswith("LOGIN_REQUIRED::")
            if needs_login:
                message = message.replace("LOGIN_REQUIRED::", "", 1)
                if self.timer.isActive():
                    self.timer.stop()
                    self.toggle_button.setText("开始监控")
            base = self.previous_snapshot or MonitorSnapshot.empty(
                shop_name=self._active_shop_name(),
                refresh_interval_seconds=self.interval_spin.value(),
            )
            now_snapshot = MonitorSnapshot.empty(
                shop_name=base.shop_name,
                region=base.region,
                refresh_interval_seconds=self.interval_spin.value(),
                source_status=("等待登录" if needs_login else f"读取失败：{message}"),
                message=message,
            )
            fallback = MonitorSnapshot(
                shop_name=now_snapshot.shop_name,
                region=now_snapshot.region,
                fetched_at=now_snapshot.fetched_at,
                refresh_interval_seconds=now_snapshot.refresh_interval_seconds,
                metrics=base.metrics if base.source_status == "Temu 实时页面" else now_snapshot.metrics,
                orders=base.orders if base.source_status == "Temu 实时页面" else now_snapshot.orders,
                events=(
                    *base.events[-4:],
                    MonitorEvent(now_snapshot.fetched_at.strftime("%H:%M:%S"), "warn", message),
                ),
                source_status=now_snapshot.source_status,
            )
            self.apply_snapshot(fallback, 0)
        except Exception as exc:  # noqa: BLE001
            log_exception("monitor-ui-failed", exc)
            self.source_label.setText(f"来源：监控界面异常：{exc}")
        finally:
            self.manual_button.setEnabled(True)

    def apply_snapshot(self, snapshot: MonitorSnapshot, new_count: int = 0) -> None:
        for name, card in self.metric_cards.items():
            card.set_value(snapshot.metrics.get(name, 0))
        self.source_label.setText(f"来源：{snapshot.source_status} / {snapshot.shop_name} / {snapshot.region}")
        self.last_fetch_label.setText(f"最近刷新：{snapshot.fetched_at.strftime('%H:%M:%S')}，新增 {new_count} 条")

        self.order_table.setRowCount(len(snapshot.orders))
        self.order_table.setVisible(bool(snapshot.orders))
        self.order_empty_state.setVisible(not snapshot.orders)
        for row, order in enumerate(snapshot.orders):
            values = [
                str(row + 1),
                order.order_id,
                order.product_sku,
                order.sku_code,
                order.color,
                order.size,
                str(order.quantity),
                order.status,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col in {0, 5, 6}:
                    item.setTextAlignment(Qt.AlignCenter)
                self.order_table.setItem(row, col, item)
        self._apply_order_table_column_sizes(has_rows=bool(snapshot.orders))

        self.event_list.clear()
        for event in snapshot.events:
            item = QListWidgetItem(f"{event.time_text}  {event.message}")
            self.event_list.addItem(item)

    def _apply_order_table_column_sizes(self, has_rows: bool) -> None:
        widths = [58, 170, 120, 150, 90, 90, 76]
        for index, width in enumerate(widths):
            self.order_table.setColumnWidth(index, width)
        if has_rows:
            self.order_table.resizeColumnsToContents()
            minimums = {0: 58, 1: 170, 2: 120, 3: 150, 4: 90, 5: 90, 6: 76}
            for index, width in minimums.items():
                self.order_table.setColumnWidth(index, max(width, self.order_table.columnWidth(index)))
        self.order_table.horizontalHeader().setStretchLastSection(True)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override name.
        if self.fetch_process is not None:
            self.fetch_process.kill()
            self.fetch_process.waitForFinished(1500)
            self.fetch_process = None
        if self.export_process is not None:
            self.export_process.kill()
            self.export_process.waitForFinished(1500)
            self.export_process = None
        self._close_monitor_browser_pages()
        super().closeEvent(event)

    def _close_monitor_browser_pages(self) -> None:
        if self.cleanup_started:
            return
        self.cleanup_started = True
        try:
            subprocess.Popen(
                [sys.executable, "-m", "consoleplat.services.monitor_fetch_cli", "--close-monitor-pages"],
                cwd=os.getcwd(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as exc:  # noqa: BLE001
            log_exception("monitor-close-pages", exc)
