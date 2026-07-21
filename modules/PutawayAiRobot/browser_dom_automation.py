import os
import re
import sys

from PyQt5 import QtCore, QtWidgets

from app_version import APP_TITLE
from browser_launch import detect_available_browsers
from cdp_utils import list_cdp_pages
from config_store import (
    browser_profile_dir,
    DEFAULT_WEIGHTS,
    load_account_profiles,
    load_product_rows,
    load_runtime_settings,
    normalize_declare_price,
    normalize_weights,
    save_account_profiles,
    save_product_rows,
    save_runtime_settings,
)
from dianxiaomi_flows import HOME_URL
from excel_importer import find_latest_xlsx_in_directory, load_product_rows_from_xlsx
from image_resolver import validate_sku_images
from workers import AlbumCleanupWorker, BatchPublishWorker, BrowserWorker, CdpActionWorker


class PutawayEmbeddedWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.user_data_dir_input = QtWidgets.QLineEdit(browser_profile_dir())
        self.port_input = QtWidgets.QSpinBox()
        self.port_input.setRange(1024, 65535)
        self.port_input.setValue(9222)
        self.open_home_btn = QtWidgets.QPushButton("启动浏览器并打开店小秘")
        self.close_browser_btn = QtWidgets.QPushButton("关闭浏览器")
        self.close_browser_btn.setEnabled(False)

        self.cdp_input = QtWidgets.QLineEdit("http://127.0.0.1:9222")
        self.refresh_btn = QtWidgets.QPushButton("刷新标签页")
        self.pages = QtWidgets.QTableWidget(0, 2)
        self.pages.setHorizontalHeaderLabels(["标题", "URL"])
        self.pages.horizontalHeader().setStretchLastSection(True)
        self.pages.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.pages.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        self.fill_login_btn = QtWidgets.QPushButton("自动填写登录（验证码手动）")
        self.fill_login_btn.setEnabled(False)
        self.enter_create_btn = QtWidgets.QPushButton("进入创建产品页面")
        self.enter_create_btn.setEnabled(False)
        self.select_shop_category_btn = QtWidgets.QPushButton("开始批量上架")
        self.select_shop_category_btn.setEnabled(False)
        self.open_runtime_settings_tab_btn = QtWidgets.QPushButton("运行设置")

        self.status = QtWidgets.QLabel("")
        self.status.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        self.tabs = QtWidgets.QTabWidget()

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.tabs)

        automation = QtWidgets.QWidget()
        automation_layout = QtWidgets.QVBoxLayout(automation)

        row1 = QtWidgets.QHBoxLayout()
        row1.addWidget(QtWidgets.QLabel("配置目录："))
        row1.addWidget(self.user_data_dir_input, 1)
        row1.addWidget(QtWidgets.QLabel("端口："))
        row1.addWidget(self.port_input)
        row1.addWidget(self.open_home_btn)
        row1.addWidget(self.close_browser_btn)
        automation_layout.addLayout(row1)

        row2 = QtWidgets.QHBoxLayout()
        row2.addWidget(QtWidgets.QLabel("CDP地址："))
        row2.addWidget(self.cdp_input, 1)
        row2.addWidget(self.refresh_btn)
        automation_layout.addLayout(row2)

        automation_layout.addWidget(self.pages, 1)

        row3 = QtWidgets.QHBoxLayout()
        row3.addWidget(self.fill_login_btn)
        row3.addWidget(self.enter_create_btn)
        row3.addWidget(self.select_shop_category_btn)
        self.manual_cleanup_btn = QtWidgets.QPushButton("立即清理图片空间")
        row3.addWidget(self.manual_cleanup_btn)
        row3.addWidget(self.open_runtime_settings_tab_btn)
        row3.addStretch(1)
        automation_layout.addLayout(row3)

        footer = QtWidgets.QHBoxLayout()
        footer.addWidget(self.status, 1)
        self.duration_status = QtWidgets.QLabel("用时：--:--")
        self.duration_status.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        footer.addWidget(self.duration_status)
        automation_layout.addLayout(footer)
        self.tabs.addTab(automation, "自动化")

        settings = QtWidgets.QWidget()
        settings_layout = QtWidgets.QVBoxLayout(settings)
        form = QtWidgets.QFormLayout()
        self.account_combo = QtWidgets.QComboBox()
        self.username_input = QtWidgets.QLineEdit()
        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        form.addRow("本次运行账号：", self.account_combo)
        form.addRow("账号：", self.username_input)
        form.addRow("密码：", self.password_input)
        settings_layout.addLayout(form)
        account_btn_row = QtWidgets.QHBoxLayout()
        self.save_cred_btn = QtWidgets.QPushButton("保存/更新账号")
        self.delete_cred_btn = QtWidgets.QPushButton("删除当前账号")
        self.set_active_cred_btn = QtWidgets.QPushButton("设为本次运行账号")
        account_btn_row.addWidget(self.save_cred_btn)
        account_btn_row.addWidget(self.delete_cred_btn)
        account_btn_row.addWidget(self.set_active_cred_btn)
        account_btn_row.addStretch(1)
        self.settings_status = QtWidgets.QLabel("")
        self.settings_status.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        settings_layout.addLayout(account_btn_row)
        settings_layout.addWidget(self.settings_status)
        settings_layout.addStretch(1)
        self.tabs.addTab(settings, "账号配置")

        product_data = QtWidgets.QWidget()
        product_layout = QtWidgets.QVBoxLayout(product_data)
        self.product_table = QtWidgets.QTableWidget(0, 5)
        self.product_table.setHorizontalHeaderLabels(["店铺名称", "产品分类", "产品标题", "产品序列号", "颜色"])
        self.product_table.horizontalHeader().setStretchLastSection(True)
        self.product_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.product_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.product_table.setAlternatingRowColors(True)
        self.product_table.verticalHeader().setDefaultSectionSize(34)
        self.product_table.horizontalHeader().setHighlightSections(False)

        excel_source_box = QtWidgets.QGroupBox("Excel 来源")
        excel_source_layout = QtWidgets.QHBoxLayout(excel_source_box)
        self.latest_excel_dir_input = QtWidgets.QLineEdit()
        self.latest_excel_dir_input.setPlaceholderText("选择存放Excel的文件夹，点击导入最新Excel会自动读取最新的 .xlsx")
        self.browse_latest_excel_dir_btn = QtWidgets.QPushButton("选择文件夹")
        self.browse_latest_excel_dir_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DirOpenIcon))
        excel_source_layout.addWidget(QtWidgets.QLabel("文件夹："))
        excel_source_layout.addWidget(self.latest_excel_dir_input, 1)
        excel_source_layout.addWidget(self.browse_latest_excel_dir_btn)
        product_layout.addWidget(excel_source_box)
        product_layout.addWidget(self.product_table, 1)

        product_btn_row = QtWidgets.QHBoxLayout()
        self.import_latest_excel_btn = QtWidgets.QPushButton("导入最新Excel")
        self.import_latest_excel_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ArrowDown))
        self.import_excel_btn = QtWidgets.QPushButton("从Excel导入")
        self.import_excel_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogOpenButton))
        self.clear_product_btn = QtWidgets.QPushButton("清空产品数据")
        self.clear_product_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_TrashIcon))
        self.save_product_rows_btn = QtWidgets.QPushButton("保存产品数据")
        self.save_product_rows_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogSaveButton))
        self.product_status = QtWidgets.QLabel("")
        self.product_status.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        product_btn_row.addWidget(self.import_latest_excel_btn)
        product_btn_row.addWidget(self.import_excel_btn)
        product_btn_row.addWidget(self.clear_product_btn)
        product_btn_row.addWidget(self.save_product_rows_btn)
        product_btn_row.addStretch(1)
        product_layout.addLayout(product_btn_row)
        product_layout.addWidget(self.product_status)
        self.tabs.addTab(product_data, "产品数据")

        self.runtime_settings_tab = QtWidgets.QWidget()
        runtime_settings_layout = QtWidgets.QVBoxLayout(self.runtime_settings_tab)
        runtime_form = QtWidgets.QFormLayout()
        self.parallel_publish_input = QtWidgets.QSpinBox()
        self.parallel_publish_input.setRange(1, 20)
        self.cleanup_every_input = QtWidgets.QSpinBox()
        self.cleanup_every_input.setRange(1, 1000)
        self.cleanup_max_rounds_input = QtWidgets.QSpinBox()
        self.cleanup_max_rounds_input.setRange(1, 2000)
        self.upload_fail_stop_threshold_input = QtWidgets.QSpinBox()
        self.upload_fail_stop_threshold_input.setRange(0, 50)
        self.upload_fail_stop_threshold_input.setSpecialValueText("0（关闭保护）")
        self.declare_price_input = QtWidgets.QDoubleSpinBox()
        self.declare_price_input.setDecimals(2)
        self.declare_price_input.setRange(0.01, 999999.99)
        self.declare_price_input.setValue(14.0)
        self.weight_inputs = []
        self.browser_preference_input = QtWidgets.QComboBox()
        runtime_form.addRow("同时并发数量：", self.parallel_publish_input)
        runtime_form.addRow("每成功多少条清理一次：", self.cleanup_every_input)
        runtime_form.addRow("单次清理最大轮次：", self.cleanup_max_rounds_input)
        runtime_form.addRow("连续上传失败停止阈值：", self.upload_fail_stop_threshold_input)
        runtime_form.addRow("申报价格：", self.declare_price_input)
        for index, default_weight in enumerate(DEFAULT_WEIGHTS, start=1):
            weight_input = QtWidgets.QSpinBox()
            weight_input.setRange(1, 999999)
            weight_input.setValue(default_weight)
            self.weight_inputs.append(weight_input)
            runtime_form.addRow(f"第{index}档克重（g）：", weight_input)
        runtime_form.addRow("浏览器类型：", self.browser_preference_input)
        runtime_settings_layout.addLayout(runtime_form)
        runtime_btn_row = QtWidgets.QHBoxLayout()
        self.save_runtime_settings_btn = QtWidgets.QPushButton("保存运行设置")
        self.refresh_browser_options_btn = QtWidgets.QPushButton("刷新浏览器检测")
        runtime_btn_row.addWidget(self.save_runtime_settings_btn)
        runtime_btn_row.addWidget(self.refresh_browser_options_btn)
        runtime_btn_row.addStretch(1)
        runtime_settings_layout.addLayout(runtime_btn_row)
        self.runtime_settings_status = QtWidgets.QLabel("")
        self.runtime_settings_status.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        runtime_settings_layout.addWidget(self.runtime_settings_status)
        runtime_settings_layout.addStretch(1)
        self.tabs.addTab(self.runtime_settings_tab, "运行设置")

        self._data = []
        self._browser_worker = None
        self._action_worker = None
        self._duration_elapsed = QtCore.QElapsedTimer()
        self._duration_tick = QtCore.QTimer(self)
        self._duration_tick.setInterval(200)
        self._duration_tick.timeout.connect(self._update_duration_label)

        self.refresh_btn.clicked.connect(self.refresh_pages)
        self.pages.itemSelectionChanged.connect(self._on_select)
        self.open_home_btn.clicked.connect(self.open_home)
        self.close_browser_btn.clicked.connect(self.close_browser)
        self.fill_login_btn.clicked.connect(self.fill_login_selected)
        self.enter_create_btn.clicked.connect(self.enter_create_selected)
        self.select_shop_category_btn.clicked.connect(self.select_shop_category_selected)
        self.manual_cleanup_btn.clicked.connect(self.run_manual_cleanup)
        self.open_runtime_settings_tab_btn.clicked.connect(self.open_runtime_settings_tab)

        self.save_cred_btn.clicked.connect(self.save_credentials_ui)
        self.delete_cred_btn.clicked.connect(self.delete_current_account_ui)
        self.set_active_cred_btn.clicked.connect(self.set_active_account_ui)
        self.account_combo.currentIndexChanged.connect(self._on_account_combo_changed)
        self.browse_latest_excel_dir_btn.clicked.connect(self.select_latest_excel_dir)
        self.import_latest_excel_btn.clicked.connect(self.import_from_latest_excel)
        self.import_excel_btn.clicked.connect(self.import_from_excel)
        self.clear_product_btn.clicked.connect(self.clear_product_rows)
        self.save_product_rows_btn.clicked.connect(self.save_product_rows_ui)
        self.save_runtime_settings_btn.clicked.connect(self.save_runtime_settings_ui)
        self.refresh_browser_options_btn.clicked.connect(self._reload_browser_options)

        self._accounts = []
        self._active_username = ""
        self._loading_accounts = False
        self._load_accounts_ui()
        self._load_product_rows_ui()
        self._load_runtime_settings_ui()
        self._apply_app_style()

        QtCore.QTimer.singleShot(0, self.refresh_pages)

    def _apply_app_style(self):
        self.setStyleSheet(
            """
            QWidget {
                background: #f4f7f6;
                color: #202b33;
                font-size: 13px;
                font-family: "Microsoft YaHei UI", "Microsoft YaHei", Arial;
            }
            QTabWidget::pane {
                border: 1px solid #d6dfdc;
                background: #ffffff;
                border-radius: 6px;
            }
            QTabBar::tab {
                background: #e8eeeb;
                color: #53615d;
                padding: 8px 18px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #11705f;
                border: 1px solid #d6dfdc;
                border-bottom: 1px solid #ffffff;
            }
            QGroupBox {
                background: #ffffff;
                border: 1px solid #d9e2df;
                border-radius: 6px;
                margin-top: 12px;
                padding: 16px 12px 12px 12px;
                font-weight: 600;
                color: #2d4b45;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                background: #ffffff;
            }
            QPushButton {
                background: #ffffff;
                border: 1px solid #c9d4d1;
                border-radius: 5px;
                padding: 7px 12px;
                min-height: 18px;
            }
            QPushButton:hover {
                background: #edf7f4;
                border-color: #3a9887;
            }
            QPushButton:pressed {
                background: #dcefeb;
            }
            QPushButton:disabled {
                background: #eef1f0;
                color: #9aa5a2;
                border-color: #d9dfdd;
            }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background: #ffffff;
                border: 1px solid #c7d2cf;
                border-radius: 5px;
                padding: 6px 8px;
                min-height: 20px;
            }
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
                border-color: #2d9d8b;
            }
            QTableWidget {
                background: #ffffff;
                alternate-background-color: #f7faf9;
                gridline-color: #e2e8e6;
                border: 1px solid #d6dfdc;
                border-radius: 6px;
                selection-background-color: #d7f0ea;
                selection-color: #16342d;
            }
            QHeaderView::section {
                background: #eaf1ee;
                color: #2a403b;
                border: none;
                border-right: 1px solid #d6dfdc;
                border-bottom: 1px solid #d6dfdc;
                padding: 8px;
                font-weight: 600;
            }
            QLabel {
                background: transparent;
            }
            """
        )

    def refresh_pages(self):
        self.status.setText("刷新中…")
        QtWidgets.QApplication.processEvents()
        try:
            self._data = list_cdp_pages(self.cdp_input.text())
            self.pages.setRowCount(0)
            for p in self._data:
                r = self.pages.rowCount()
                self.pages.insertRow(r)
                self.pages.setItem(r, 0, QtWidgets.QTableWidgetItem(p["title"]))
                self.pages.setItem(r, 1, QtWidgets.QTableWidgetItem(p["url"]))
            if self._data:
                self.pages.selectRow(0)
            self.status.setText(f"已加载 {len(self._data)} 个页面")
        except Exception as e:
            self.status.setText(str(e))

    def _on_select(self):
        enabled = self.pages.currentRow() >= 0 and bool(self._data)
        self.fill_login_btn.setEnabled(enabled)
        self.enter_create_btn.setEnabled(enabled)
        self.select_shop_category_btn.setEnabled(enabled)

    def _selected_tab_url(self):
        r = self.pages.currentRow()
        if r < 0 or r >= len(self._data):
            return ""
        return self._data[r]["url"]

    def _selected_tab_ws(self):
        r = self.pages.currentRow()
        if r < 0 or r >= len(self._data):
            return ""
        return self._data[r].get("webSocketDebuggerUrl", "")

    def _app_screen_geometry(self):
        screen = None
        try:
            center = self.mapToGlobal(self.rect().center())
            screen = QtWidgets.QApplication.screenAt(center)
        except Exception:
            screen = None
        if screen is None:
            try:
                screen = QtWidgets.QApplication.primaryScreen()
            except Exception:
                screen = None
        if screen is None:
            return {}
        g = screen.availableGeometry()
        return {"left": int(g.left()), "top": int(g.top()), "width": int(g.width()), "height": int(g.height())}

    def _selected_product_row(self):
        row = self.product_table.currentRow()
        if row < 0:
            return None
        values = []
        for c in range(5):
            item = self.product_table.item(row, c)
            values.append((item.text() if item else "").strip())
        return {"shop_name": values[0], "category": values[1], "title": values[2], "sku": values[3], "color": values[4]}

    def _run_action(self, worker, busy_text: str):
        if self._action_worker and self._action_worker.isRunning():
            return
        self.fill_login_btn.setEnabled(False)
        self.enter_create_btn.setEnabled(False)
        self.select_shop_category_btn.setEnabled(False)
        self.manual_cleanup_btn.setEnabled(False)
        self.status.setText(busy_text)
        self.duration_status.setText("用时：--:--")
        self._duration_elapsed.restart()
        self._duration_tick.start()
        QtWidgets.QApplication.processEvents()
        try:
            worker.progress.connect(self.status.setText)
        except Exception:
            pass
        try:
            worker.row_done.connect(self._on_batch_row_done)
        except Exception:
            pass
        worker.ok.connect(self._on_action_ok)
        worker.failed.connect(self._on_action_failed)
        self._action_worker = worker
        worker.start()

    def fill_login_selected(self):
        creds = self._selected_credentials()
        if not creds["username"] or not creds["password"]:
            QtWidgets.QMessageBox.warning(self, "提示", "请先在“账号配置”里保存账号密码")
            return
        cdp = self.cdp_input.text()
        url = self._selected_tab_url()
        ws = self._selected_tab_ws()
        worker = CdpActionWorker("fill_login", cdp, url, page_ws=ws, username=creds["username"], password=creds["password"])
        self._run_action(worker, "正在填写登录信息…")

    def enter_create_selected(self):
        cdp = self.cdp_input.text()
        url = self._selected_tab_url()
        ws = self._selected_tab_ws()
        worker = CdpActionWorker("enter_create", cdp, url, page_ws=ws)
        self._run_action(worker, "正在进入创建产品页面…")

    def select_shop_category_selected(self):
        rows = self._collect_product_rows_ui()
        valid_rows = [r for r in rows if (r.get("shop_name") or "").strip() and (r.get("category") or "").strip()]
        if not valid_rows:
            QtWidgets.QMessageBox.warning(self, "提示", "产品数据中没有可发布的有效行（店铺名称和产品分类不能为空）")
            return
        image_check = validate_sku_images([r.get("sku") for r in valid_rows])
        if (not image_check.get("exists")) or image_check.get("image_count", 0) <= 0 or image_check.get("missing"):
            base_dir = image_check.get("base_dir") or ""
            missing = image_check.get("missing") or []
            lines = []
            if not image_check.get("exists"):
                lines.append(f"产品主图目录不存在：{base_dir}")
            elif image_check.get("image_count", 0) <= 0:
                lines.append(f"产品主图目录没有图片：{base_dir}")
            if missing:
                show = missing[:50]
                lines.append(f"缺少 {len(missing)} 个货号对应的产品主图：")
                lines.extend(show)
                if len(missing) > len(show):
                    lines.append(f"... 还有 {len(missing) - len(show)} 个未显示")
            lines.append("")
            lines.append("规则：data/pic/1 中图片文件名需要等于货号，或包含货号，例如 BO-306_产品标题.png")
            QtWidgets.QMessageBox.warning(self, "产品主图检查失败", "\n".join(lines))
            return
        cdp = self.cdp_input.text()
        url = self._selected_tab_url()
        ws = self._selected_tab_ws()
        creds = self._selected_credentials()
        if not creds["username"] or not creds["password"]:
            QtWidgets.QMessageBox.warning(self, "提示", "请先在“账号配置”里保存并选择本次运行账号")
            return
        declare_price = normalize_declare_price(self.declare_price_input.value())
        weights = tuple(normalize_weights([weight_input.value() for weight_input in self.weight_inputs]))
        weights_text = "/".join(str(weight) for weight in weights)
        try:
            self._save_runtime_settings_from_ui()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "运行设置保存失败", str(e))
            return
        confirmation = QtWidgets.QMessageBox.question(
            self,
            "确认批量上架",
            "即将执行真实批量上架并立即发布。\n\n"
            f"有效商品：{len(valid_rows)} 条\n"
            f"申报价格：{declare_price}\n"
            f"克重：{weights_text}g\n\n"
            "是否继续？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if confirmation != QtWidgets.QMessageBox.Yes:
            return
        parallel_count = min(int(self.parallel_publish_input.value()), len(valid_rows))
        cleanup_every = int(self.cleanup_every_input.value())
        worker = BatchPublishWorker(
            cdp,
            url,
            ws,
            valid_rows,
            parallel_count,
            screen_geometry=self._app_screen_geometry(),
            cleanup_every=cleanup_every,
            cleanup_max_rounds=int(self.cleanup_max_rounds_input.value()),
            upload_fail_stop_threshold=int(self.upload_fail_stop_threshold_input.value()),
            login_username=creds["username"],
            login_password=creds["password"],
            declare_price=declare_price,
            weights=weights,
        )
        self._run_action(worker, f"正在批量上架（并发{parallel_count}，申报价格{declare_price}，克重{weights_text}g）…")

    def open_runtime_settings_tab(self):
        idx = self.tabs.indexOf(self.runtime_settings_tab)
        if idx >= 0:
            self.tabs.setCurrentIndex(idx)

    def run_manual_cleanup(self):
        cdp = (self.cdp_input.text() or "").strip()
        if not cdp:
            QtWidgets.QMessageBox.warning(self, "提示", "CDP地址为空")
            return
        worker = AlbumCleanupWorker(cdp, max_rounds=int(self.cleanup_max_rounds_input.value()))
        self._run_action(worker, "正在清理图片空间…")

    def _load_runtime_settings_ui(self):
        self._reload_browser_options()
        settings = load_runtime_settings()
        self.parallel_publish_input.setValue(int(settings.get("parallel_count") or 1))
        self.cleanup_every_input.setValue(int(settings.get("cleanup_every") or 50))
        self.cleanup_max_rounds_input.setValue(int(settings.get("cleanup_max_rounds") or 40))
        self.upload_fail_stop_threshold_input.setValue(int(settings.get("upload_fail_stop_threshold", 3)))
        self.declare_price_input.setValue(float(normalize_declare_price(settings.get("declare_price"))))
        for weight_input, weight in zip(self.weight_inputs, normalize_weights(settings.get("weights"))):
            weight_input.setValue(weight)
        self.latest_excel_dir_input.setText(settings.get("latest_excel_dir") or "")
        browser_pref = (settings.get("browser_preference") or "auto").strip().lower()
        idx = self.browser_preference_input.findData(browser_pref)
        if idx >= 0:
            self.browser_preference_input.setCurrentIndex(idx)
        self.runtime_settings_status.setText("已加载运行设置")

    def _save_runtime_settings_from_ui(self):
        save_runtime_settings(
            int(self.parallel_publish_input.value()),
            int(self.cleanup_every_input.value()),
            int(self.cleanup_max_rounds_input.value()),
            str(self.browser_preference_input.currentData() or "auto"),
            int(self.upload_fail_stop_threshold_input.value()),
            self.latest_excel_dir_input.text(),
            normalize_declare_price(self.declare_price_input.value()),
            [weight_input.value() for weight_input in self.weight_inputs],
        )

    def save_runtime_settings_ui(self):
        try:
            self._save_runtime_settings_from_ui()
            self.runtime_settings_status.setText("运行设置已保存")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "失败", str(e))

    def _reload_browser_options(self):
        items = detect_available_browsers()
        current = str(self.browser_preference_input.currentData() or "auto")
        self.browser_preference_input.clear()
        for it in items:
            self.browser_preference_input.addItem(it.get("label") or "", it.get("value") or "auto")
        idx = self.browser_preference_input.findData(current)
        if idx < 0:
            idx = self.browser_preference_input.findData("auto")
        if idx >= 0:
            self.browser_preference_input.setCurrentIndex(idx)

    def open_home(self):
        if self._browser_worker and self._browser_worker.isRunning():
            return
        port = int(self.port_input.value())
        self.cdp_input.setText(f"http://127.0.0.1:{port}")
        self.status.setText("启动浏览器中…")
        QtWidgets.QApplication.processEvents()

        creds = self._selected_credentials()
        worker = BrowserWorker(
            self.user_data_dir_input.text(),
            port,
            HOME_URL,
            creds["username"],
            creds["password"],
            browser_preference=str(self.browser_preference_input.currentData() or "auto"),
        )
        worker.started_ok.connect(self._on_browser_started)
        worker.failed.connect(self._on_browser_failed)
        self._browser_worker = worker
        self.open_home_btn.setEnabled(False)
        self.close_browser_btn.setEnabled(True)
        worker.start()

    def close_browser(self):
        if self._browser_worker and self._browser_worker.isRunning():
            self.status.setText("正在关闭浏览器…")
            QtWidgets.QApplication.processEvents()
            self._browser_worker.stop()
            self._browser_worker.wait(8000)
        self.open_home_btn.setEnabled(True)
        self.close_browser_btn.setEnabled(False)
        self.status.setText("浏览器已关闭")

    def _on_browser_started(self):
        self.status.setText("浏览器已启动并打开店小秘")
        QtCore.QTimer.singleShot(800, self.refresh_pages)

    def _on_browser_failed(self, msg: str):
        self.open_home_btn.setEnabled(True)
        self.close_browser_btn.setEnabled(False)
        QtWidgets.QMessageBox.critical(self, "失败", msg)

    def _selected_credentials(self):
        username = (self.account_combo.currentData() or self.username_input.text() or "").strip()
        if username:
            for item in getattr(self, "_accounts", []):
                if (item.get("username") or "").strip() == username:
                    return {"username": username, "password": item.get("password") or ""}
        return {"username": (self.username_input.text() or "").strip(), "password": self.password_input.text() or ""}

    def _load_accounts_ui(self):
        self._loading_accounts = True
        try:
            profiles = load_account_profiles()
            self._accounts = profiles.get("accounts") or []
            self._active_username = (profiles.get("active_username") or "").strip()
            self.account_combo.clear()
            for item in self._accounts:
                username = (item.get("username") or "").strip()
                if username:
                    self.account_combo.addItem(username, username)
            if self.account_combo.count() <= 0:
                self.account_combo.addItem("未配置账号", "")
            idx = self.account_combo.findData(self._active_username)
            if idx < 0:
                idx = 0
            self.account_combo.setCurrentIndex(idx)
            self._fill_account_fields_from_combo()
            if self._active_username:
                self.settings_status.setText(f"本次运行账号：{self._active_username}")
            else:
                self.settings_status.setText("未配置账号")
        finally:
            self._loading_accounts = False

    def _fill_account_fields_from_combo(self):
        username = (self.account_combo.currentData() or "").strip()
        for item in getattr(self, "_accounts", []):
            if (item.get("username") or "").strip() == username:
                self.username_input.setText(username)
                self.password_input.setText(item.get("password") or "")
                return
        self.username_input.setText("")
        self.password_input.setText("")

    def _on_account_combo_changed(self):
        if getattr(self, "_loading_accounts", False):
            return
        self._fill_account_fields_from_combo()

    def _save_accounts_ui(self):
        save_account_profiles(getattr(self, "_accounts", []), self._active_username)
        self._load_accounts_ui()

    def save_credentials_ui(self):
        try:
            username = (self.username_input.text() or "").strip()
            if not username:
                QtWidgets.QMessageBox.warning(self, "提示", "账号不能为空")
                return
            password = self.password_input.text() or ""
            replaced = False
            accounts = []
            for item in getattr(self, "_accounts", []):
                if (item.get("username") or "").strip() == username:
                    accounts.append({"username": username, "password": password})
                    replaced = True
                else:
                    accounts.append(item)
            if not replaced:
                accounts.append({"username": username, "password": password})
            self._accounts = accounts
            self._active_username = username
            self._save_accounts_ui()
            self.settings_status.setText(f"已保存，本次运行账号：{username}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "失败", str(e))

    def delete_current_account_ui(self):
        username = (self.account_combo.currentData() or self.username_input.text() or "").strip()
        if not username:
            return
        reply = QtWidgets.QMessageBox.question(self, "确认", f"确定删除账号配置：{username}？")
        if reply != QtWidgets.QMessageBox.Yes:
            return
        self._accounts = [item for item in getattr(self, "_accounts", []) if (item.get("username") or "").strip() != username]
        if self._active_username == username:
            self._active_username = self._accounts[0]["username"] if self._accounts else ""
        try:
            self._save_accounts_ui()
            self.settings_status.setText("已删除账号配置")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "失败", str(e))

    def set_active_account_ui(self):
        username = (self.account_combo.currentData() or self.username_input.text() or "").strip()
        if not username:
            QtWidgets.QMessageBox.warning(self, "提示", "请先保存账号")
            return
        self._active_username = username
        try:
            self._save_accounts_ui()
            self.settings_status.setText(f"本次运行账号：{username}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "失败", str(e))

    def _on_action_ok(self, msg: str):
        self._duration_tick.stop()
        self._update_duration_label()
        self.status.setText(msg)
        m = re.search(r"用时\s*(\d{2}:\d{2})", msg or "")
        if m:
            self.duration_status.setText(f"用时：{m.group(1)}")
        self.manual_cleanup_btn.setEnabled(True)
        self._on_select()

    def _on_action_failed(self, msg: str):
        self._duration_tick.stop()
        self._update_duration_label()
        self.manual_cleanup_btn.setEnabled(True)
        if "连续" in (msg or "") and "上传失败" in (msg or "") and "关闭浏览器" in (msg or ""):
            try:
                if self._browser_worker and self._browser_worker.isRunning():
                    self._browser_worker.stop()
                    self._browser_worker.wait(3000)
            except Exception:
                pass
            self.open_home_btn.setEnabled(True)
            self.close_browser_btn.setEnabled(False)
        self._on_select()
        QtWidgets.QMessageBox.critical(self, "失败", msg)

    def _update_duration_label(self):
        if not self._duration_elapsed.isValid():
            return
        elapsed_ms = max(0, int(self._duration_elapsed.elapsed()))
        mm = elapsed_ms // 60000
        ss = (elapsed_ms % 60000) // 1000
        self.duration_status.setText(f"用时：{mm:02d}:{ss:02d}")

    def _load_product_rows_ui(self):
        rows = load_product_rows()
        self._set_product_table_rows(rows)
        self.product_status.setText(f"已加载 {self.product_table.rowCount()} 行")

    def _set_product_table_rows(self, rows):
        self.product_table.setRowCount(0)
        for r in rows:
            idx = self.product_table.rowCount()
            self.product_table.insertRow(idx)
            self.product_table.setItem(idx, 0, QtWidgets.QTableWidgetItem(r.get("shop_name", "")))
            self.product_table.setItem(idx, 1, QtWidgets.QTableWidgetItem(r.get("category", "")))
            self.product_table.setItem(idx, 2, QtWidgets.QTableWidgetItem(r.get("title", "")))
            self.product_table.setItem(idx, 3, QtWidgets.QTableWidgetItem(r.get("sku", "")))
            self.product_table.setItem(idx, 4, QtWidgets.QTableWidgetItem(r.get("color", "")))
        if self.product_table.rowCount() > 0:
            self.product_table.selectRow(0)

    def _collect_product_rows_ui(self):
        rows = []
        for r in range(self.product_table.rowCount()):
            items = [self.product_table.item(r, c) for c in range(5)]
            rows.append(
                {
                    "shop_name": (items[0].text() if items[0] else "").strip(),
                    "category": (items[1].text() if items[1] else "").strip(),
                    "title": (items[2].text() if items[2] else "").strip(),
                    "sku": (items[3].text() if items[3] else "").strip(),
                    "color": (items[4].text() if items[4] else "").strip(),
                }
            )
        return rows

    def _remove_first_matching_product_row(self, row_data: dict):
        keys = ["shop_name", "category", "title", "sku", "color"]
        want = [(row_data.get(k) or "").strip() for k in keys]
        for r in range(self.product_table.rowCount()):
            got = []
            for c in range(5):
                it = self.product_table.item(r, c)
                got.append((it.text() if it else "").strip())
            if got == want:
                self.product_table.removeRow(r)
                return True
        return False

    def _on_batch_row_done(self, row_data, ok: bool, _reason: str):
        if not ok:
            return
        changed = self._remove_first_matching_product_row(row_data or {})
        if changed:
            try:
                save_product_rows(self._collect_product_rows_ui())
            except Exception:
                pass

    def save_product_rows_ui(self):
        try:
            rows = self._collect_product_rows_ui()
            save_product_rows(rows)
            self.product_status.setText("已保存")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "失败", str(e))

    def select_latest_excel_dir(self):
        current = (self.latest_excel_dir_input.text() or "").strip()
        default_dir = current if os.path.isdir(current) else os.path.dirname(os.path.abspath(__file__))
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, "选择最新Excel文件夹", default_dir)
        if not folder_path:
            return
        self.latest_excel_dir_input.setText(folder_path)
        try:
            self._save_runtime_settings_from_ui()
            self.product_status.setText(f"已设置最新Excel文件夹：{folder_path}")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "提示", f"文件夹已选择，但保存失败：{e}")

    def _import_product_rows_from_file(self, file_path: str):
        rows = load_product_rows_from_xlsx(file_path)
        self._set_product_table_rows(rows)
        self.product_status.setText(f"已导入 {self.product_table.rowCount()} 行：{file_path}")

    def import_from_latest_excel(self):
        try:
            self._save_runtime_settings_from_ui()
            folder_path = self.latest_excel_dir_input.text()
            file_path = find_latest_xlsx_in_directory(folder_path)
            self._import_product_rows_from_file(file_path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "失败", str(e))

    def import_from_excel(self):
        base = os.path.dirname(os.path.abspath(__file__))
        default_dir = base
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "选择Excel文件",
            default_dir,
            "Excel Files (*.xlsx)",
        )
        if not file_path:
            return
        try:
            self._import_product_rows_from_file(file_path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "失败", str(e))

    def clear_product_rows(self):
        try:
            self.product_table.setRowCount(0)
            save_product_rows([])
            self.product_status.setText("已清空")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "失败", str(e))


def create_putaway_widget(parent=None):
    return PutawayEmbeddedWidget(parent)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1080, 640)
        self.embedded_widget = create_putaway_widget(self)
        self.setCentralWidget(self.embedded_widget)


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
