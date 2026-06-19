from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from consoleplat.config import AppSettings, SettingsStore, ShopAccount


class SettingsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = SettingsStore()
        self.tab_buttons: dict[str, QPushButton] = {}
        self._build_ui()
        self.load_settings()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        self.shop_combo = QComboBox()
        self.shop_combo.addItems(["YUHOOBO", "YUHAOBO"])
        self.shop_combo.currentTextChanged.connect(self._load_account_for_shop)

        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("手机号 / 账号")
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("密码")

        self.cdp_edit = QLineEdit()
        self.cdp_edit.setPlaceholderText("http://127.0.0.1:9222")
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(2, 120)
        self.interval_spin.setSuffix(" 秒")

        self.purchase_export_dir_edit = QLineEdit()
        self.purchase_export_dir_edit.setObjectName("purchaseExportDirEdit")
        self.purchase_export_dir_edit.setPlaceholderText("E:/1PythonProject/SendGoods/outputs")

        self.startup_width_spin = QSpinBox()
        self.startup_width_spin.setObjectName("startupWidthSpin")
        self.startup_width_spin.setRange(920, 2560)
        self.startup_width_spin.setSuffix(" px")
        self.startup_height_spin = QSpinBox()
        self.startup_height_spin.setObjectName("startupHeightSpin")
        self.startup_height_spin.setRange(600, 1600)
        self.startup_height_spin.setSuffix(" px")

        tabs = QHBoxLayout()
        tabs.setSpacing(8)
        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)
        for index, (key, label) in enumerate([("monitor", "监控"), ("account", "账号"), ("program", "程序")]):
            button = QPushButton(label)
            button.setObjectName("settingsTabButton")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, page_index=index: self.activate_module(page_index))
            self.tab_group.addButton(button)
            self.tab_buttons[key] = button
            tabs.addWidget(button)
        tabs.addStretch(1)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_monitor_panel())
        self.stack.addWidget(self._build_account_panel())
        self.stack.addWidget(self._build_program_panel())

        actions = QHBoxLayout()
        self.save_button = QPushButton("保存设置")
        self.save_button.setObjectName("primaryButton")
        self.save_button.setCursor(Qt.PointingHandCursor)
        self.save_button.clicked.connect(self.save_settings)
        self.status_label = QLabel("")
        self.status_label.setObjectName("cardSubtitle")
        actions.addWidget(self.save_button)
        actions.addWidget(self.status_label)
        actions.addStretch(1)

        root.addLayout(tabs)
        root.addWidget(self.stack)
        root.addLayout(actions)
        root.addStretch(1)
        self.activate_module(0)

    def _build_monitor_panel(self) -> QFrame:
        panel = self._make_panel("监控模块", "设置店铺监控刷新间隔、Chrome 连接地址和备货单导出目录。")
        layout = panel.layout()
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        export_dir_row = QHBoxLayout()
        self.browse_export_dir_button = QPushButton("选择")
        self.browse_export_dir_button.setObjectName("ghostButton")
        self.browse_export_dir_button.setCursor(Qt.PointingHandCursor)
        self.browse_export_dir_button.clicked.connect(self.choose_export_dir)
        export_dir_row.addWidget(self.purchase_export_dir_edit, 1)
        export_dir_row.addWidget(self.browse_export_dir_button)

        form.addRow("监控店铺", self.shop_combo)
        form.addRow("Chrome 调试地址", self.cdp_edit)
        form.addRow("刷新间隔", self.interval_spin)
        form.addRow("备货单导出目录", export_dir_row)
        layout.addLayout(form)
        return panel

    def _build_account_panel(self) -> QFrame:
        panel = self._make_panel("账号模块", "用于 Temu 登录。密码会使用 Windows DPAPI 保存在本机，不写入项目目录。")
        layout = panel.layout()
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.addRow("账号", self.phone_edit)
        form.addRow("密码", self.password_edit)
        layout.addLayout(form)
        return panel

    def _build_program_panel(self) -> QFrame:
        panel = self._make_panel("程序模块", "设置软件启动时的默认窗口大小；保存后下次打开生效。")
        layout = panel.layout()
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.addRow("默认宽度", self.startup_width_spin)
        form.addRow("默认高度", self.startup_height_spin)
        layout.addLayout(form)
        return panel

    def _make_panel(self, title: str, hint: str) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        hint_label = QLabel(hint)
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: #607081;")
        layout.addWidget(title_label)
        layout.addWidget(hint_label)
        return panel

    def activate_module(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for button_index, button in enumerate(self.tab_group.buttons()):
            is_active = button_index == index
            button.setChecked(is_active)
            button.setProperty("active", "true" if is_active else "false")
            button.style().unpolish(button)
            button.style().polish(button)

    def load_settings(self) -> None:
        settings = self.store.load()
        index = self.shop_combo.findText(settings.active_shop)
        self.shop_combo.blockSignals(True)
        self.shop_combo.setCurrentIndex(max(0, index))
        self.shop_combo.blockSignals(False)
        self.cdp_edit.setText(settings.cdp_endpoint)
        self.interval_spin.setValue(settings.refresh_interval_seconds)
        self.purchase_export_dir_edit.setText(settings.purchase_export_dir)
        self.startup_width_spin.setValue(settings.startup_width)
        self.startup_height_spin.setValue(settings.startup_height)
        self._load_account_for_shop(self.shop_combo.currentText(), settings)

    def save_settings(self) -> None:
        old_settings = self.store.load()
        shop_name = self.shop_combo.currentText().strip() or "YUHOOBO"
        accounts = dict(old_settings.accounts)
        accounts[shop_name] = ShopAccount(
            shop_name=shop_name,
            phone=self.phone_edit.text().strip(),
            password=self.password_edit.text(),
        )
        settings = AppSettings(
            active_shop=shop_name,
            cdp_endpoint=self.cdp_edit.text().strip() or "http://127.0.0.1:9222",
            refresh_interval_seconds=self.interval_spin.value(),
            purchase_export_dir=self.purchase_export_dir_edit.text().strip() or "E:/1PythonProject/SendGoods/outputs",
            startup_width=self.startup_width_spin.value(),
            startup_height=self.startup_height_spin.value(),
            accounts=accounts,
        )
        self.store.save(settings)
        self.status_label.setText(f"已保存到 {self.store.path}")

    def choose_export_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择备货单导出目录", self.purchase_export_dir_edit.text())
        if path:
            self.purchase_export_dir_edit.setText(path)

    def _load_account_for_shop(self, shop_name: str, settings: AppSettings | None = None) -> None:
        settings = settings or self.store.load()
        account = settings.accounts.get(shop_name) or ShopAccount(shop_name=shop_name)
        self.phone_edit.setText(account.phone)
        self.password_edit.setText(account.password)
