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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from consoleplat.config import AppSettings, DEFAULT_AI_EDIT_PROMPT, SettingsStore, ShopAccount


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

        self.purchase_export_dir_edit = self._line_edit(
            "purchaseExportDirEdit",
            "E:/1PythonProject/SendGoods/outputs",
        )

        self.posai_gallery_root_edit = self._line_edit(
            "posaiGalleryRootEdit",
            "E:/1PythonProject/PosAiImg/图库",
        )
        self.posai_mockup_root_edit = self._line_edit(
            "posaiMockupRootEdit",
            "E:/1PythonProject/PosAiImg/批量贴图结果",
        )
        self.posai_xlsx_root_edit = self._line_edit(
            "posaiXlsxRootEdit",
            "E:/1PythonProject/PosAiImg/衣物对应的xlsx",
        )
        self.ai_edit_api_base_edit = self._line_edit(
            "aiEditApiBaseEdit",
            "https://api.openai.com/v1",
        )
        self.ai_edit_model_edit = self._line_edit("aiEditModelEdit", "gpt-image-2")
        self.ai_edit_size_edit = self._line_edit("aiEditSizeEdit", "1024x1024")
        self.ai_edit_prompt_edit = QTextEdit()
        self.ai_edit_prompt_edit.setObjectName("aiEditPromptEdit")
        self.ai_edit_prompt_edit.setFixedHeight(120)

        self.bo_product_title_edit = self._line_edit("boProductTitleEdit")
        self.szw_product_title_edit = self._line_edit("szwProductTitleEdit")
        self.publish_prefix_combo = QComboBox()
        self.publish_prefix_combo.addItems(["BO", "SZW"])
        self.publish_task_name_edit = self._line_edit("publishTaskNameEdit")
        self.publish_generation_mode_combo = QComboBox()
        self.publish_generation_mode_combo.addItems(["本地生图", "AI 改图"])
        self.publish_local_count_spin = QSpinBox()
        self.publish_local_count_spin.setObjectName("publishLocalCountSpin")
        self.publish_local_count_spin.setRange(1, 500)
        self.publish_local_count_spin.setSuffix(" 张")
        self.publish_ai_count_spin = QSpinBox()
        self.publish_ai_count_spin.setObjectName("publishAiCountSpin")
        self.publish_ai_count_spin.setRange(1, 500)
        self.publish_ai_count_spin.setSuffix(" 轮")

        self.putaway_project_dir_edit = self._line_edit(
            "putawayProjectDirEdit",
            "E:/1PythonProject/PutawayAiRobot",
        )
        self.putaway_data_dir_edit = self._line_edit(
            "putawayDataDirEdit",
            "E:/1PythonProject/PutawayAiRobot/data",
        )
        self.putaway_log_dir_edit = self._line_edit(
            "putawayLogDirEdit",
            "E:/1PythonProject/PutawayAiRobot/log",
        )
        self.program_data_dir_edit = self._line_edit("programDataDirEdit")

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
        tab_items = [
            ("monitor", "监控"),
            ("account", "账号"),
            ("image", "生图 / 改图"),
            ("publish", "发布"),
            ("program", "程序"),
        ]
        for index, (key, label) in enumerate(tab_items):
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
        self.stack.addWidget(self._build_image_panel())
        self.stack.addWidget(self._build_publish_panel())
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
        panel = self._make_panel("监控模块", "这里集中放 Temu 监控、浏览器连接和拿货表导出目录。")
        layout = panel.layout()
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.addRow("监控店铺", self.shop_combo)
        form.addRow("Chrome 调试地址", self.cdp_edit)
        form.addRow("刷新间隔", self.interval_spin)
        form.addRow("拿货表导出目录", self._browse_row(self.purchase_export_dir_edit, self.choose_export_dir))
        layout.addLayout(form)
        return panel

    def _build_account_panel(self) -> QFrame:
        panel = self._make_panel("账号模块", "账号密码仅保存在当前机器，密码继续走 Windows DPAPI。")
        layout = panel.layout()
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.addRow("账号", self.phone_edit)
        form.addRow("密码", self.password_edit)
        layout.addLayout(form)
        return panel

    def _build_image_panel(self) -> QFrame:
        panel = self._make_panel("生图 / 改图", "恢复 PosAiImg、AI 改图接口和默认提示词相关设置。")
        layout = panel.layout()
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.addRow("图库目录", self._browse_row(self.posai_gallery_root_edit, self.choose_posai_gallery_root))
        form.addRow("产品图目录", self._browse_row(self.posai_mockup_root_edit, self.choose_posai_mockup_root))
        form.addRow("XLSX 目录", self._browse_row(self.posai_xlsx_root_edit, self.choose_posai_xlsx_root))
        form.addRow("AI 接口地址", self.ai_edit_api_base_edit)
        form.addRow("AI 模型", self.ai_edit_model_edit)
        form.addRow("默认尺寸", self.ai_edit_size_edit)
        form.addRow("默认改图要求", self.ai_edit_prompt_edit)
        layout.addLayout(form)
        return panel

    def _build_publish_panel(self) -> QFrame:
        panel = self._make_panel("发布模块", "固定产品标题和发布页默认模板都放回这里。")
        layout = panel.layout()
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.addRow("BO 固定产品标题", self.bo_product_title_edit)
        form.addRow("SZW 固定产品标题", self.szw_product_title_edit)
        form.addRow("默认店铺前缀", self.publish_prefix_combo)
        form.addRow("默认任务名", self.publish_task_name_edit)
        form.addRow("默认生图方式", self.publish_generation_mode_combo)
        form.addRow("本地生图默认张数", self.publish_local_count_spin)
        form.addRow("AI 改图默认轮数", self.publish_ai_count_spin)
        layout.addLayout(form)
        return panel

    def _build_program_panel(self) -> QFrame:
        panel = self._make_panel("程序模块", "恢复 PutawayAiRobot 对接目录、程序数据目录和窗口大小。")
        layout = panel.layout()
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.addRow("上架项目目录", self._browse_row(self.putaway_project_dir_edit, self.choose_putaway_project_dir))
        form.addRow("上架 data 目录", self._browse_row(self.putaway_data_dir_edit, self.choose_putaway_data_dir))
        form.addRow("上架日志目录", self._browse_row(self.putaway_log_dir_edit, self.choose_putaway_log_dir))
        form.addRow("程序数据目录", self._browse_row(self.program_data_dir_edit, self.choose_program_data_dir))
        form.addRow("启动宽度", self.startup_width_spin)
        form.addRow("启动高度", self.startup_height_spin)
        layout.addLayout(form)
        return panel

    def _line_edit(self, object_name: str, placeholder: str = "") -> QLineEdit:
        edit = QLineEdit()
        edit.setObjectName(object_name)
        if placeholder:
            edit.setPlaceholderText(placeholder)
        return edit

    def _browse_row(self, edit: QLineEdit, callback) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        button = QPushButton("选择")
        button.setObjectName("ghostButton")
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(callback)
        layout.addWidget(edit, 1)
        layout.addWidget(button)
        return row

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

        self.posai_gallery_root_edit.setText(settings.posai_gallery_root)
        self.posai_mockup_root_edit.setText(settings.posai_mockup_root)
        self.posai_xlsx_root_edit.setText(settings.posai_xlsx_root)
        self.ai_edit_api_base_edit.setText(settings.ai_edit_api_base)
        self.ai_edit_model_edit.setText(settings.ai_edit_model)
        self.ai_edit_size_edit.setText(settings.ai_edit_size)
        self.ai_edit_prompt_edit.setPlainText(settings.ai_edit_prompt or DEFAULT_AI_EDIT_PROMPT)

        self.bo_product_title_edit.setText(settings.bo_product_title)
        self.szw_product_title_edit.setText(settings.szw_product_title)
        self.publish_prefix_combo.setCurrentText(settings.publish_prefix or "BO")
        self.publish_task_name_edit.setText(settings.publish_task_name)
        self.publish_generation_mode_combo.setCurrentText(settings.publish_generation_mode or "本地生图")
        self.publish_local_count_spin.setValue(max(1, settings.publish_local_count))
        self.publish_ai_count_spin.setValue(max(1, settings.publish_ai_count))

        self.putaway_project_dir_edit.setText(settings.putaway_project_dir)
        self.putaway_data_dir_edit.setText(settings.putaway_data_dir)
        self.putaway_log_dir_edit.setText(settings.putaway_log_dir)
        self.program_data_dir_edit.setText(settings.program_data_dir)
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
            local_image_auto_start_comfyui=old_settings.local_image_auto_start_comfyui,
            local_image_keep_comfyui=old_settings.local_image_keep_comfyui,
            local_image_test_mode=old_settings.local_image_test_mode,
            ai_edit_api_key=old_settings.ai_edit_api_key,
            ai_edit_api_base=self.ai_edit_api_base_edit.text().strip() or "https://api.openai.com/v1",
            ai_edit_model=self.ai_edit_model_edit.text().strip() or "gpt-image-2",
            ai_edit_size=self.ai_edit_size_edit.text().strip() or "1024x1024",
            ai_edit_prompt=self.ai_edit_prompt_edit.toPlainText().strip() or DEFAULT_AI_EDIT_PROMPT,
            ai_edit_split_collage=old_settings.ai_edit_split_collage,
            ai_edit_split_count=old_settings.ai_edit_split_count,
            ai_edit_total_return_count=old_settings.ai_edit_total_return_count,
            ai_edit_reference_dir=old_settings.ai_edit_reference_dir,
            posai_gallery_root=self.posai_gallery_root_edit.text().strip() or "E:/1PythonProject/PosAiImg/图库",
            posai_mockup_root=self.posai_mockup_root_edit.text().strip() or "E:/1PythonProject/PosAiImg/批量贴图结果",
            posai_xlsx_root=self.posai_xlsx_root_edit.text().strip() or "E:/1PythonProject/PosAiImg/衣物对应的xlsx",
            putaway_project_dir=self.putaway_project_dir_edit.text().strip() or "E:/1PythonProject/PutawayAiRobot",
            putaway_data_dir=self.putaway_data_dir_edit.text().strip() or "E:/1PythonProject/PutawayAiRobot/data",
            putaway_log_dir=self.putaway_log_dir_edit.text().strip() or "E:/1PythonProject/PutawayAiRobot/log",
            program_data_dir=self.program_data_dir_edit.text().strip(),
            bo_product_title=self.bo_product_title_edit.text().strip() or "BO固定产品标题",
            szw_product_title=self.szw_product_title_edit.text().strip() or "SZW固定产品标题",
            publish_prefix=self.publish_prefix_combo.currentText(),
            publish_task_name=self.publish_task_name_edit.text().strip() or "默认产品发布任务",
            publish_start_number=old_settings.publish_start_number,
            publish_generation_mode=self.publish_generation_mode_combo.currentText(),
            publish_local_count=max(1, self.publish_local_count_spin.value()),
            publish_ai_count=max(1, self.publish_ai_count_spin.value()),
            publish_handoff_mode=old_settings.publish_handoff_mode,
            publish_test_mode=old_settings.publish_test_mode,
            publish_local_steps=old_settings.publish_local_steps,
            publish_local_seed=old_settings.publish_local_seed,
            publish_auto_start_comfyui=old_settings.publish_auto_start_comfyui,
            publish_keep_comfyui=old_settings.publish_keep_comfyui,
            publish_ai_prompt=old_settings.publish_ai_prompt,
            publish_ai_reference_images=list(old_settings.publish_ai_reference_images),
            startup_width=self.startup_width_spin.value(),
            startup_height=self.startup_height_spin.value(),
            accounts=accounts,
        )
        self.store.save(settings)
        self.status_label.setText(f"已保存到 {self.store.path}")

    def _choose_directory_for(self, edit: QLineEdit, title: str) -> None:
        path = QFileDialog.getExistingDirectory(self, title, edit.text())
        if path:
            edit.setText(path)

    def choose_export_dir(self) -> None:
        self._choose_directory_for(self.purchase_export_dir_edit, "选择拿货表导出目录")

    def choose_posai_gallery_root(self) -> None:
        self._choose_directory_for(self.posai_gallery_root_edit, "选择图库目录")

    def choose_posai_mockup_root(self) -> None:
        self._choose_directory_for(self.posai_mockup_root_edit, "选择产品图目录")

    def choose_posai_xlsx_root(self) -> None:
        self._choose_directory_for(self.posai_xlsx_root_edit, "选择 XLSX 目录")

    def choose_putaway_project_dir(self) -> None:
        self._choose_directory_for(self.putaway_project_dir_edit, "选择 Putaway 项目目录")

    def choose_putaway_data_dir(self) -> None:
        self._choose_directory_for(self.putaway_data_dir_edit, "选择 Putaway data 目录")

    def choose_putaway_log_dir(self) -> None:
        self._choose_directory_for(self.putaway_log_dir_edit, "选择 Putaway 日志目录")

    def choose_program_data_dir(self) -> None:
        self._choose_directory_for(self.program_data_dir_edit, "选择程序数据目录")

    def _load_account_for_shop(self, shop_name: str, settings: AppSettings | None = None) -> None:
        settings = settings or self.store.load()
        account = settings.accounts.get(shop_name) or ShopAccount(shop_name=shop_name)
        self.phone_edit.setText(account.phone)
        self.password_edit.setText(account.password)
