from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QObject, QThread, Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from consoleplat import APP_VERSION
from consoleplat.config import (
    AIProviderConfig,
    AppSettings,
    DEFAULT_AI_EDIT_PROMPT,
    SettingsStore,
    ShopAccount,
    default_project_search_roots,
    resolve_project_dir,
)
from consoleplat.paths import default_download_dir, default_prints_dir
from consoleplat.services.posai_resource_downloader import PosAiResourceDefinition, install_posai_resource
from consoleplat.services.version_check_service import UpdateCheckWorker, download_asset
from consoleplat.services.version_check_service import UpdateProxyConfig
from consoleplat.services.print_gallery_service import GithubPrintTestResult, pull_random_github_print

_UpdateCheckWorker = UpdateCheckWorker
_PrintGalleryGithubTest = pull_random_github_print


class _DownloadWorker(QObject):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(bool, str)

    def __init__(self, url: str, dest: str, proxy: UpdateProxyConfig | None = None) -> None:
        super().__init__()
        self.url = url
        self.dest = dest
        self.proxy = proxy

    def run(self) -> None:
        try:
            path = download_asset(self.url, self.dest, progress_cb=self.progress.emit, proxy=self.proxy)
        except Exception as exc:  # noqa: BLE001 - UI 只显示失败文案，不让后台异常穿透
            self.finished.emit(False, str(exc))
            return
        self.finished.emit(True, path)


class _PrintGalleryGithubTestWorker(QObject):
    finished = pyqtSignal(object)

    def __init__(self, github_url: str, local_gallery_dir: str, proxy: UpdateProxyConfig | None = None) -> None:
        super().__init__()
        self.github_url = github_url
        self.local_gallery_dir = local_gallery_dir
        self.proxy = proxy

    def run(self) -> None:
        result = _PrintGalleryGithubTest(
            github_url=self.github_url,
            local_gallery_dir=self.local_gallery_dir,
            proxy=self.proxy,
        )
        self.finished.emit(result)


class _PosAiResourceDownloadWorker(QObject):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(object)

    def __init__(self, resource: PosAiResourceDefinition, download_dir: str, resources_dir: str) -> None:
        super().__init__()
        self.resource = resource
        self.download_dir = download_dir
        self.resources_dir = resources_dir
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        result = install_posai_resource(
            self.resource,
            download_dir=self.download_dir,
            resources_dir=self.resources_dir,
            progress_cb=self.progress.emit,
            should_cancel=lambda: self._cancelled,
        )
        self.finished.emit(result)


class SettingsPage(QWidget):
    settings_saved = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = SettingsStore()
        self.tab_buttons: dict[str, QPushButton] = {}
        self._provider_records: list[AIProviderConfig] = []
        self._provider_loading = False
        self._update_thread: QThread | None = None
        self._update_worker: UpdateCheckWorker | None = None
        self._latest_release: dict | None = None
        self._download_thread: QThread | None = None
        self._download_worker: _DownloadWorker | None = None
        self._print_gallery_test_thread: QThread | None = None
        self._print_gallery_test_worker: _PrintGalleryGithubTestWorker | None = None
        self._posai_download_thread: QThread | None = None
        self._posai_download_worker: _PosAiResourceDownloadWorker | None = None
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

        self.purchase_export_dir_edit = self._line_edit("purchaseExportDirEdit", "留空则自动使用 SendGoods/outputs")
        self.print_gallery_source_combo = QComboBox()
        self.print_gallery_source_combo.setObjectName("printGallerySourceCombo")
        self.print_gallery_source_combo.addItems(["本地图集中采集", "来自 GitHub"])
        self.print_gallery_local_dir_edit = self._line_edit("printGalleryLocalDirEdit", "留空则自动使用 PosAiImg/图库")
        self.print_gallery_github_raw_base_edit = self._line_edit(
            "printGalleryGithubRawBaseEdit",
            "例如 https://raw.githubusercontent.com/owner/repo/main/gallery",
        )
        self.test_print_gallery_github_button = QPushButton("测试拉取")
        self.test_print_gallery_github_button.setObjectName("testPrintGalleryGithubButton")
        self.test_print_gallery_github_button.setCursor(Qt.PointingHandCursor)
        self.test_print_gallery_github_button.clicked.connect(self.test_print_gallery_github)
        self.print_gallery_github_test_status_label = QLabel("")
        self.print_gallery_github_test_status_label.setObjectName("printGalleryGithubTestStatusLabel")
        self.print_gallery_github_test_status_label.setWordWrap(True)
        self.posai_gallery_root_edit = self._line_edit("posaiGalleryRootEdit", "留空则自动探测 PosAiImg/图库")
        self.posai_mockup_root_edit = self._line_edit("posaiMockupRootEdit", "留空则自动探测 PosAiImg/批量贴图结果")
        self.posai_xlsx_root_edit = self._line_edit("posaiXlsxRootEdit", "留空则自动探测 PosAiImg/衣物对应的xlsx")
        self.posai_model_root_edit = self._line_edit("posaiModelRootEdit", "留空则自动探测 PosAiImg/模特图-干净")
        self.posai_comfyui_dir_edit = self._line_edit("posaiComfyuiDirEdit", "留空则自动使用 PosAiImg/ComfyUI")
        self.posai_resource_download_dir_edit = self._line_edit(
            "posaiResourceDownloadDirEdit",
            "留空则使用 runtime/downloads/posai",
        )
        self.posai_comfyui_download_url_edit = self._line_edit("posaiComfyuiDownloadUrlEdit", "ComfyUI zip 下载地址")
        self.posai_models_download_url_edit = self._line_edit("posaiModelsDownloadUrlEdit", "PosAiImg 模型 zip 下载地址")
        self.download_posai_comfyui_button = QPushButton("下载 / 安装 ComfyUI")
        self.download_posai_comfyui_button.setObjectName("downloadPosaiComfyuiButton")
        self.download_posai_comfyui_button.setCursor(Qt.PointingHandCursor)
        self.download_posai_comfyui_button.clicked.connect(self.download_posai_comfyui)
        self.download_posai_models_button = QPushButton("下载 / 安装模型")
        self.download_posai_models_button.setObjectName("downloadPosaiModelsButton")
        self.download_posai_models_button.setCursor(Qt.PointingHandCursor)
        self.download_posai_models_button.clicked.connect(self.download_posai_models)
        self.detect_posai_resources_button = QPushButton("重新检测资源")
        self.detect_posai_resources_button.setObjectName("detectPosaiResourcesButton")
        self.detect_posai_resources_button.setCursor(Qt.PointingHandCursor)
        self.detect_posai_resources_button.clicked.connect(self.detect_posai_resources)
        self.clear_posai_resources_button = QPushButton("清除资源路径")
        self.clear_posai_resources_button.setObjectName("clearPosaiResourcesButton")
        self.clear_posai_resources_button.setCursor(Qt.PointingHandCursor)
        self.clear_posai_resources_button.clicked.connect(self.clear_posai_resources)
        self.posai_resource_download_progress = QProgressBar()
        self.posai_resource_download_progress.setObjectName("posaiResourceDownloadProgress")
        self.posai_resource_download_progress.setRange(0, 100)
        self.posai_resource_download_progress.setValue(0)
        self.posai_resource_download_progress.hide()
        self.posai_resource_status_label = QLabel("")
        self.posai_resource_status_label.setObjectName("posaiResourceStatusLabel")
        self.posai_resource_status_label.setWordWrap(True)

        self.ai_provider_combo = QComboBox()
        self.ai_provider_combo.setObjectName("aiProviderCombo")
        self.ai_provider_combo.setMaximumWidth(260)
        self.ai_provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        self.ai_provider_name_edit = self._line_edit("aiProviderNameEdit", "默认接口")
        self.ai_edit_api_key_edit = self._line_edit("aiEditApiKeyEdit")
        self.ai_edit_api_key_edit.setEchoMode(QLineEdit.Password)
        self.ai_edit_api_base_edit = self._line_edit("aiEditApiBaseEdit", "https://api.openai.com/v1")
        self.ai_edit_model_edit = self._line_edit("aiEditModelEdit", "gpt-image-2")
        self.ai_edit_size_edit = self._line_edit("aiEditSizeEdit", "1024x1024")
        self.ai_edit_prompt_edit = QTextEdit()
        self.ai_edit_prompt_edit.setObjectName("aiEditPromptEdit")
        self.ai_edit_prompt_edit.setMaximumHeight(96)

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

        self.putaway_project_dir_edit = self._line_edit("putawayProjectDirEdit", "留空则自动探测 PutawayAiRobot")
        self.putaway_data_dir_edit = self._line_edit("putawayDataDirEdit", "留空则使用上架项目 data")
        self.putaway_log_dir_edit = self._line_edit("putawayLogDirEdit", "留空则使用上架项目 log")
        self.applygoods_project_dir_edit = self._line_edit("applyGoodsProjectDirEdit", "留空则自动探测 ApplyGoods")
        self.program_data_dir_edit = self._line_edit("programDataDirEdit")
        self.path_status_labels: dict[str, QLabel] = {}

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
            ("putaway", "上架"),
            ("apply", "合规"),
            ("program", "程序"),
            ("appearance", "外观"),
            ("update", "更新"),
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
        self.stack.addWidget(self._build_putaway_panel())
        self.stack.addWidget(self._build_apply_panel())
        self.stack.addWidget(self._build_program_panel())
        self.stack.addWidget(self._build_appearance_panel())
        self.stack.addWidget(self._build_update_panel())

        actions = QHBoxLayout()
        self.save_button = QPushButton("保存设置")
        self.save_button.setObjectName("primaryButton")
        self.save_button.setCursor(Qt.PointingHandCursor)
        self.save_button.clicked.connect(self.save_settings)
        self.status_label = QLabel("")
        self.status_label.setObjectName("cardSubtitle")
        actions.addWidget(self.save_button)
        self.detect_paths_button = QPushButton("自动定位源项目")
        self.detect_paths_button.setObjectName("settingsPathsAnchor")
        self.detect_paths_button.setCursor(Qt.PointingHandCursor)
        self.detect_paths_button.clicked.connect(self.detect_project_paths)
        self.security_hint_label = QLabel("敏感信息不要写入日志或仓库；API Key、Cookie、Token 应使用安全存储或临时输入。")
        self.security_hint_label.setObjectName("settingsSecurityAnchor")
        self.security_hint_label.setWordWrap(True)
        actions.addWidget(self.detect_paths_button)
        actions.addWidget(self.security_hint_label)
        actions.addWidget(self.status_label)
        actions.addStretch(1)

        root.addLayout(tabs)
        root.addWidget(self.stack, 1)
        root.addLayout(actions)
        self.activate_module(0)

    def _build_monitor_panel(self) -> QFrame:
        panel = self._make_panel("监控模块", "这里集中放 Temu 监控、浏览器连接和拿货表导出目录。", compact=True)
        panel.setObjectName("settingsBrowserAnchor")
        layout = panel.layout()
        form = QFormLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        form.setLabelAlignment(Qt.AlignRight)
        form.addRow("监控店铺", self.shop_combo)
        form.addRow("Chrome 调试地址", self.cdp_edit)
        form.addRow("刷新间隔", self.interval_spin)
        form.addRow("拿货表导出目录", self._browse_row(self.purchase_export_dir_edit, self.choose_export_dir))
        form.addRow("印花来源", self.print_gallery_source_combo)
        form.addRow("本地图集目录", self._browse_row(self.print_gallery_local_dir_edit, self.choose_print_gallery_local_dir))
        form.addRow(
            "GitHub Raw 目录",
            self._button_row(self.print_gallery_github_raw_base_edit, self.test_print_gallery_github_button),
        )
        form.addRow("拉取测试", self.print_gallery_github_test_status_label)
        layout.addLayout(form)
        return self._wrap_scroll_panel(panel, fill_viewport=False)

    def _build_account_panel(self) -> QFrame:
        panel = self._make_panel("账号模块", "账号密码仅保存在当前机器，密码继续走 Windows DPAPI。", compact=True)
        layout = panel.layout()
        form = QFormLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        form.setLabelAlignment(Qt.AlignRight)
        form.addRow("账号", self.phone_edit)
        form.addRow("密码", self.password_edit)
        layout.addLayout(form)
        return self._wrap_scroll_panel(panel, fill_viewport=False)

    def _build_image_panel(self) -> QFrame:
        panel = self._make_panel("生图 / 改图", "恢复多套 AI 接口配置、PosAiImg 路径和默认改图提示词。")
        layout = panel.layout()
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        path_form = QFormLayout()
        path_form.setLabelAlignment(Qt.AlignRight)
        path_form.addRow("图库目录", self._browse_row(self.posai_gallery_root_edit, self.choose_posai_gallery_root))
        path_form.addRow("产品图目录", self._browse_row(self.posai_mockup_root_edit, self.choose_posai_mockup_root))
        path_form.addRow("XLSX 目录", self._browse_row(self.posai_xlsx_root_edit, self.choose_posai_xlsx_root))
        path_form.addRow("PosAiImg 状态", self._path_status_label("posaiimg"))
        layout.addLayout(path_form)

        resource_panel = QFrame()
        resource_panel.setObjectName("subPanel")
        resource_layout = QVBoxLayout(resource_panel)
        resource_layout.setContentsMargins(12, 10, 12, 10)
        resource_layout.setSpacing(8)
        resource_layout.addWidget(QLabel("PosAiImg 资源"))
        resource_form = QFormLayout()
        resource_form.setLabelAlignment(Qt.AlignRight)
        resource_form.addRow("ComfyUI 安装目录", self._browse_row(self.posai_comfyui_dir_edit, self.choose_posai_comfyui_dir))
        resource_form.addRow("模型目录", self._browse_row(self.posai_model_root_edit, self.choose_posai_model_root))
        resource_form.addRow(
            "下载目录",
            self._browse_row(self.posai_resource_download_dir_edit, self.choose_posai_resource_download_dir),
        )
        resource_form.addRow("ComfyUI 下载地址", self.posai_comfyui_download_url_edit)
        resource_form.addRow("模型下载地址", self.posai_models_download_url_edit)
        resource_layout.addLayout(resource_form)
        resource_actions = QHBoxLayout()
        resource_actions.addWidget(self.download_posai_comfyui_button)
        resource_actions.addWidget(self.download_posai_models_button)
        resource_actions.addWidget(self.detect_posai_resources_button)
        resource_actions.addWidget(self.clear_posai_resources_button)
        resource_actions.addStretch(1)
        resource_layout.addLayout(resource_actions)
        resource_layout.addWidget(self.posai_resource_download_progress)
        resource_layout.addWidget(self.posai_resource_status_label)
        layout.addWidget(resource_panel)

        provider_panel = QFrame()
        provider_panel.setObjectName("subPanel")
        provider_layout = QVBoxLayout(provider_panel)
        provider_layout.setContentsMargins(12, 10, 12, 10)
        provider_layout.setSpacing(8)
        provider_layout.addWidget(QLabel("AI 接口配置"))

        provider_toolbar = QHBoxLayout()
        provider_toolbar.setSpacing(8)
        self.add_provider_button = QPushButton("新增接口")
        self.add_provider_button.setObjectName("ghostButton")
        self.add_provider_button.clicked.connect(self._add_provider)
        self.duplicate_provider_button = QPushButton("复制当前")
        self.duplicate_provider_button.setObjectName("ghostButton")
        self.duplicate_provider_button.clicked.connect(self._duplicate_provider)
        self.delete_provider_button = QPushButton("删除当前")
        self.delete_provider_button.setObjectName("ghostButton")
        self.delete_provider_button.clicked.connect(self._delete_provider)
        provider_toolbar.addWidget(self.ai_provider_combo, 1)
        provider_toolbar.addWidget(self.add_provider_button)
        provider_toolbar.addWidget(self.duplicate_provider_button)
        provider_toolbar.addWidget(self.delete_provider_button)
        provider_layout.addLayout(provider_toolbar)

        provider_form = QFormLayout()
        provider_form.setLabelAlignment(Qt.AlignRight)
        provider_form.addRow("接口名称", self.ai_provider_name_edit)
        provider_form.addRow("API Key", self.ai_edit_api_key_edit)
        provider_form.addRow("接口地址", self.ai_edit_api_base_edit)
        provider_form.addRow("模型", self.ai_edit_model_edit)
        provider_form.addRow("默认尺寸", self.ai_edit_size_edit)
        provider_layout.addLayout(provider_form)
        layout.addWidget(provider_panel)

        prompt_form = QFormLayout()
        prompt_form.setLabelAlignment(Qt.AlignRight)
        prompt_form.addRow("默认改图要求", self.ai_edit_prompt_edit)
        layout.addLayout(prompt_form)
        return self._wrap_scroll_panel(panel, fill_viewport=True)

    def _build_publish_panel(self) -> QFrame:
        panel = self._make_panel("发布模块", "固定产品标题和发布页默认模板都放回这里。", compact=True)
        layout = panel.layout()
        form = QFormLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        form.setLabelAlignment(Qt.AlignRight)
        form.addRow("BO 固定产品标题", self.bo_product_title_edit)
        form.addRow("SZW 固定产品标题", self.szw_product_title_edit)
        form.addRow("默认店铺前缀", self.publish_prefix_combo)
        form.addRow("默认任务名", self.publish_task_name_edit)
        form.addRow("默认生图方式", self.publish_generation_mode_combo)
        form.addRow("本地生图默认张数", self.publish_local_count_spin)
        form.addRow("AI 改图默认轮数", self.publish_ai_count_spin)
        layout.addLayout(form)
        return self._wrap_scroll_panel(panel, fill_viewport=False)

    def _build_putaway_panel(self) -> QFrame:
        panel = self._make_panel("上架模块", "PutawayAiRobot 的项目目录、data 目录和日志目录集中放在这里管理。", compact=True)
        layout = panel.layout()
        form = QFormLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        form.setLabelAlignment(Qt.AlignRight)
        form.addRow("上架项目目录", self._browse_row(self.putaway_project_dir_edit, self.choose_putaway_project_dir))
        form.addRow("上架 data 目录", self._browse_row(self.putaway_data_dir_edit, self.choose_putaway_data_dir))
        form.addRow("上架日志目录", self._browse_row(self.putaway_log_dir_edit, self.choose_putaway_log_dir))
        form.addRow("上架路径状态", self._path_status_label("putaway"))
        layout.addLayout(form)
        return self._wrap_scroll_panel(panel, fill_viewport=False)

    def _build_apply_panel(self) -> QFrame:
        panel = self._make_panel("合规模块", "ApplyGoods 的项目目录放在这里，内嵌合规页面会从该目录加载界面。", compact=True)
        layout = panel.layout()
        form = QFormLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        form.setLabelAlignment(Qt.AlignRight)
        form.addRow("合规项目目录", self._browse_row(self.applygoods_project_dir_edit, self.choose_applygoods_project_dir))
        form.addRow("合规路径状态", self._path_status_label("applygoods"))
        layout.addLayout(form)
        return self._wrap_scroll_panel(panel, fill_viewport=False)

    def _build_program_panel(self) -> QFrame:
        panel = self._make_panel("程序模块", "这里仅保留 ConsolePlat 自身的数据目录和启动窗口大小。", compact=True)
        layout = panel.layout()
        form = QFormLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        form.setLabelAlignment(Qt.AlignRight)
        form.addRow("程序数据目录", self._browse_row(self.program_data_dir_edit, self.choose_program_data_dir))
        form.addRow("启动宽度", self.startup_width_spin)
        form.addRow("启动高度", self.startup_height_spin)
        layout.addLayout(form)
        return self._wrap_scroll_panel(panel, fill_viewport=False)

    def _build_appearance_panel(self) -> QFrame:
        panel = self._make_panel("外观模块", "切换浅色 / 深色主题，并可选设置主窗口背景图。", compact=True)
        layout = panel.layout()
        form = QFormLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        form.setLabelAlignment(Qt.AlignRight)

        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("themeCombo")
        self.theme_combo.addItems(["浅色 (light)", "深色 (dark)"])
        form.addRow("主题", self.theme_combo)
        form.addRow("背景图", self._browse_row(self._build_bg_image_edit(), self.choose_bg_image))
        layout.addLayout(form)
        return self._wrap_scroll_panel(panel, fill_viewport=False)

    def _build_update_panel(self) -> QFrame:
        panel = self._make_panel("软件更新", "从 GitHub 检查并下载新版本，不会自动覆盖运行中的程序。", compact=True)
        layout = panel.layout()

        self.current_version_label = QLabel(f"当前版本：v{APP_VERSION}")
        self.current_version_label.setObjectName("sectionTitle")
        self.latest_version_label = QLabel("最新版本：尚未检查")
        self.update_status_label = QLabel("")
        self.update_status_label.setObjectName("cardSubtitle")
        self.update_status_label.setWordWrap(True)

        self.check_update_on_startup_check = QCheckBox("启动时自动检查更新")
        self.check_update_on_startup_check.setObjectName("checkUpdateOnStartupCheck")
        self.update_proxy_enabled_check = QCheckBox("使用代理访问 GitHub")
        self.update_proxy_enabled_check.setObjectName("updateProxyEnabledCheck")
        option_row = QWidget()
        option_row.setObjectName("updateOptionRow")
        option_layout = QHBoxLayout(option_row)
        option_layout.setContentsMargins(0, 0, 0, 0)
        option_layout.setSpacing(28)
        option_layout.addWidget(self.check_update_on_startup_check)
        option_layout.addWidget(self.update_proxy_enabled_check)
        option_layout.addStretch(1)
        self.update_proxy_host_edit = self._line_edit("updateProxyHostEdit", "127.0.0.1")
        self.update_proxy_port_spin = QSpinBox()
        self.update_proxy_port_spin.setObjectName("updateProxyPortSpin")
        self.update_proxy_port_spin.setRange(1, 65535)
        self.update_proxy_port_spin.setValue(7890)

        proxy_form = QFormLayout()
        proxy_form.setHorizontalSpacing(10)
        proxy_form.setVerticalSpacing(8)
        proxy_form.setLabelAlignment(Qt.AlignRight)
        proxy_form.addRow("代理地址", self.update_proxy_host_edit)
        proxy_form.addRow("代理端口", self.update_proxy_port_spin)

        self.release_notes_edit = QTextEdit()
        self.release_notes_edit.setObjectName("releaseNotesEdit")
        self.release_notes_edit.setReadOnly(True)
        self.release_notes_edit.setMaximumHeight(180)
        self.release_notes_edit.setPlaceholderText("更新日志会显示在这里")

        self.download_progress = QProgressBar()
        self.download_progress.setObjectName("downloadProgress")
        self.download_progress.setRange(0, 100)
        self.download_progress.setValue(0)
        self.download_progress.hide()

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        self.check_update_button = QPushButton("检查更新")
        self.check_update_button.setObjectName("checkUpdateButton")
        self.check_update_button.setProperty("variant", "primary")
        self.check_update_button.setStyleSheet("")
        self.check_update_button.setCursor(Qt.PointingHandCursor)
        self.check_update_button.clicked.connect(self.check_for_update)
        self.download_update_button = QPushButton("下载更新")
        self.download_update_button.setObjectName("downloadUpdateButton")
        self.download_update_button.setCursor(Qt.PointingHandCursor)
        self.download_update_button.clicked.connect(self.download_update)
        self.download_update_button.setEnabled(False)
        self.skip_version_button = QPushButton("跳过此版本")
        self.skip_version_button.setObjectName("skipVersionButton")
        self.skip_version_button.setCursor(Qt.PointingHandCursor)
        self.skip_version_button.clicked.connect(self.skip_current_version)
        self.skip_version_button.setEnabled(False)
        for button in (self.check_update_button, self.download_update_button, self.skip_version_button):
            if not button.property("variant"):
                button.setProperty("variant", "ghost")
            button.setObjectName(button.objectName())
        button_row.addWidget(self.check_update_button)
        button_row.addWidget(self.download_update_button)
        button_row.addWidget(self.skip_version_button)
        button_row.addStretch(1)

        layout.addWidget(self.current_version_label)
        layout.addWidget(self.latest_version_label)
        layout.addWidget(option_row)
        layout.addLayout(proxy_form)
        layout.addLayout(button_row)
        layout.addWidget(self.download_progress)
        layout.addWidget(QLabel("更新日志"))
        layout.addWidget(self.release_notes_edit)
        layout.addWidget(self.update_status_label)
        return self._wrap_scroll_panel(panel, fill_viewport=False)

    def _line_edit(self, object_name: str, placeholder: str = "") -> QLineEdit:
        edit = QLineEdit()
        edit.setObjectName(object_name)
        if placeholder:
            edit.setPlaceholderText(placeholder)
        return edit

    def _browse_row(self, edit: QLineEdit, callback) -> QWidget:
        button = QPushButton("选择")
        button.setObjectName("ghostButton")
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(callback)
        return self._button_row(edit, button)

    def _button_row(self, edit: QLineEdit, button: QPushButton) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(edit, 1)
        layout.addWidget(button)
        return row

    def _path_status_label(self, key: str) -> QLabel:
        label = QLabel("")
        label.setObjectName(f"{key}PathStatusLabel")
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.path_status_labels[key] = label
        return label

    def _build_bg_image_edit(self) -> QLineEdit:
        self.bg_image_edit = self._line_edit("bgImageEdit", "留空则无背景图")
        return self.bg_image_edit

    def _make_panel(self, title: str, hint: str, compact: bool = False) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        if compact:
            layout.setContentsMargins(18, 16, 18, 16)
            layout.setSpacing(8)
        else:
            layout.setContentsMargins(20, 18, 20, 18)
            layout.setSpacing(12)
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        hint_label = QLabel(hint)
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: #607081;")
        layout.addWidget(title_label)
        layout.addWidget(hint_label)
        return panel

    def _wrap_scroll_panel(self, panel: QFrame, *, fill_viewport: bool = False) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(fill_viewport)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("settingsModuleScroll")
        scroll.setProperty("fillViewport", "true" if fill_viewport else "false")
        scroll.setWidget(panel)
        scroll.viewport().installEventFilter(self)
        if fill_viewport:
            panel.setMinimumHeight(scroll.viewport().height())
        return scroll

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if event.type() == event.Resize:
            for index in range(self.stack.count()):
                scroll = self.stack.widget(index)
                if isinstance(scroll, QScrollArea) and scroll.viewport() is watched:
                    widget = scroll.widget()
                    if widget is not None and scroll.property("fillViewport") == "true":
                        widget.setMinimumHeight(scroll.viewport().height())
                    elif widget is not None:
                        widget.setMinimumHeight(0)
                        widget.resize(scroll.viewport().width(), widget.sizeHint().height())
                    if scroll is self.stack.currentWidget():
                        self._sync_current_module_height()
                    break
        return super().eventFilter(watched, event)

    def activate_module(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for button_index, button in enumerate(self.tab_group.buttons()):
            is_active = button_index == index
            button.setChecked(is_active)
            button.setProperty("active", "true" if is_active else "false")
            button.style().unpolish(button)
            button.style().polish(button)
        self._sync_current_module_height()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._sync_current_module_height()

    def _sync_current_module_height(self) -> None:
        scroll = self.stack.currentWidget()
        if not isinstance(scroll, QScrollArea):
            self.stack.setMaximumHeight(16777215)
            return
        widget = scroll.widget()
        if widget is None:
            self.stack.setMaximumHeight(16777215)
            return
        if scroll.property("fillViewport") == "true":
            self.stack.setMaximumHeight(16777215)
            widget.setMinimumHeight(scroll.viewport().height())
            return
        widget.setMinimumHeight(0)
        widget.resize(scroll.viewport().width(), widget.sizeHint().height())
        self.stack.setMaximumHeight(widget.sizeHint().height() + 2)

    def activate_update_tab(self) -> None:
        keys = list(self.tab_buttons)
        if "update" in keys:
            self.activate_module(keys.index("update"))

    def test_print_gallery_github(self) -> None:
        if self._print_gallery_test_thread is not None:
            return
        github_url = self.print_gallery_github_raw_base_edit.text().strip()
        if not github_url:
            self.print_gallery_github_test_status_label.setText("请先填写 GitHub 图集地址")
            return
        local_gallery_dir = str(self._current_print_gallery_local_dir())
        self.test_print_gallery_github_button.setEnabled(False)
        self.print_gallery_github_test_status_label.setText("正在从 GitHub 随机拉取印花…")

        thread = QThread(self)
        worker = _PrintGalleryGithubTestWorker(github_url, local_gallery_dir, self._proxy_config_from_form())
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_print_gallery_test_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._cleanup_print_gallery_test_worker(thread, worker))
        self._print_gallery_test_thread = thread
        self._print_gallery_test_worker = worker
        thread.start()

    def _current_print_gallery_local_dir(self) -> Path:
        configured = self.print_gallery_local_dir_edit.text().strip()
        if configured:
            return Path(configured)
        posai_gallery_root = self.posai_gallery_root_edit.text().strip()
        if posai_gallery_root:
            return Path(posai_gallery_root)
        posai_dir = resolve_project_dir("posaiimg")
        if posai_dir:
            return posai_dir / "图库"
        return default_prints_dir()

    def _cleanup_print_gallery_test_worker(self, thread: QThread, worker: _PrintGalleryGithubTestWorker) -> None:
        if self._print_gallery_test_thread is thread:
            self._print_gallery_test_thread = None
        if self._print_gallery_test_worker is worker:
            self._print_gallery_test_worker = None

    def _on_print_gallery_test_finished(self, result: GithubPrintTestResult) -> None:
        self.test_print_gallery_github_button.setEnabled(True)
        message = getattr(result, "message", "") or "测试完成"
        saved_path = getattr(result, "saved_path", "")
        if getattr(result, "ok", False) and saved_path:
            self.print_gallery_github_test_status_label.setText(f"拉取成功：{saved_path}")
            return
        self.print_gallery_github_test_status_label.setText(message)

    def check_for_update(self) -> None:
        if self._update_thread is not None:
            return
        self.check_update_button.setEnabled(False)
        self.update_status_label.setText("正在连接 GitHub…")
        proxy = self._proxy_config_from_form()
        thread = QThread(self)
        worker = _UpdateCheckWorker(proxy)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_check_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._cleanup_update_worker(thread, worker))
        self._update_thread = thread
        self._update_worker = worker
        thread.start()

    def _cleanup_update_worker(self, thread: QThread, worker: UpdateCheckWorker) -> None:
        if self._update_thread is thread:
            self._update_thread = None
        if self._update_worker is worker:
            self._update_worker = None

    def _on_check_finished(self, result: dict) -> None:
        self.check_update_button.setEnabled(True)
        self._persist_last_check_time()
        self._apply_update_check_result(result)

    def _apply_update_check_result(self, result: dict) -> None:
        if not result.get("ok"):
            kind = result.get("kind")
            text = {
                "offline": "无法连接 GitHub，请检查网络",
                "proxy_error": result.get("message") or "代理连接失败，请检查代理设置",
                "no_release": result.get("message") or "GitHub 已连通，但仓库还没有发布 Release",
                "rate_limited": "GitHub 访问受限，请稍后再试",
            }.get(kind, "检查更新失败")
            self.update_status_label.setText(text)
            self.download_update_button.setEnabled(False)
            self.skip_version_button.setEnabled(False)
            return

        release = result.get("release") or {}
        self._latest_release = release
        self.latest_version_label.setText(f"最新版本：v{release.get('version', '?')}（{release.get('tag_name', '')}）")
        self.release_notes_edit.setPlainText(release.get("body") or "（无更新日志）")
        if result.get("has_update"):
            self.update_status_label.setText("发现新版本，可下载更新")
            self.download_update_button.setEnabled(True)
            self.skip_version_button.setEnabled(True)
        else:
            self.update_status_label.setText("已是最新版本")
            self.download_update_button.setEnabled(False)
            self.skip_version_button.setEnabled(False)

    def _persist_last_check_time(self) -> None:
        settings = self.store.load()
        settings.last_update_check = datetime.now().isoformat(timespec="seconds")
        self.store.save(settings)

    def download_update(self) -> None:
        release = self._latest_release or {}
        download_url = str(release.get("download_url") or "")
        asset_name = str(release.get("asset_name") or "")
        if not download_url:
            return
        if not asset_name:
            QDesktopServices.openUrl(QUrl(release.get("html_url") or download_url))
            self.update_status_label.setText("已打开下载页面，请在浏览器中下载")
            return

        settings = self.store.load()
        target_dir = Path(settings.update_download_dir or (Path.home() / "Downloads"))
        target_dir.mkdir(parents=True, exist_ok=True)
        dest = target_dir / asset_name
        self.download_progress.show()
        self.download_progress.setValue(0)
        self.download_update_button.setEnabled(False)
        self.update_status_label.setText(f"正在下载 {asset_name} …")
        self._start_download_worker(download_url, str(dest), self._proxy_config_from_form())

    def _proxy_config_from_settings(self, settings: AppSettings) -> UpdateProxyConfig:
        return UpdateProxyConfig(
            enabled=settings.update_proxy_enabled,
            host=settings.update_proxy_host,
            port=settings.update_proxy_port,
        )

    def _proxy_config_from_form(self) -> UpdateProxyConfig:
        return UpdateProxyConfig(
            enabled=self.update_proxy_enabled_check.isChecked(),
            host=self.update_proxy_host_edit.text().strip() or "127.0.0.1",
            port=self.update_proxy_port_spin.value(),
        )

    def _start_download_worker(self, url: str, dest: str, proxy: UpdateProxyConfig | None = None) -> None:
        if self._download_thread is not None:
            return
        thread = QThread(self)
        worker = _DownloadWorker(url, dest, proxy)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_download_progress)
        worker.finished.connect(self._on_download_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._cleanup_download_worker(thread, worker))
        self._download_thread = thread
        self._download_worker = worker
        thread.start()

    def _cleanup_download_worker(self, thread: QThread, worker: _DownloadWorker) -> None:
        if self._download_thread is thread:
            self._download_thread = None
        if self._download_worker is worker:
            self._download_worker = None

    def _on_download_progress(self, received: int, total: int) -> None:
        if total <= 0:
            self.download_progress.setRange(0, 0)
            return
        self.download_progress.setRange(0, 100)
        self.download_progress.setValue(min(100, int(received * 100 / total)))

    def _on_download_finished(self, ok: bool, message: str) -> None:
        self.download_progress.setRange(0, 100)
        if ok:
            self.download_progress.setValue(100)
            self.update_status_label.setText("下载完成，请关闭程序后手动安装")
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(message).parent)))
            return
        self.download_update_button.setEnabled(True)
        self.update_status_label.setText(f"下载失败：{message}")
        release = self._latest_release or {}
        asset_name = str(release.get("asset_name") or "")
        if asset_name:
            target_dir = Path(self.store.load().update_download_dir or (Path.home() / "Downloads"))
            partial = target_dir / asset_name
            if partial.exists():
                partial.unlink(missing_ok=True)

    def download_posai_comfyui(self) -> None:
        resource = PosAiResourceDefinition(
            key="comfyui",
            label="ComfyUI",
            url=self.posai_comfyui_download_url_edit.text().strip(),
            install_dir_name="ComfyUI",
            min_free_bytes=5 * 1024 * 1024 * 1024,
        )
        self._start_posai_resource_download(resource)

    def download_posai_models(self) -> None:
        resource = PosAiResourceDefinition(
            key="posai_models",
            label="PosAiImg 模型",
            url=self.posai_models_download_url_edit.text().strip(),
            install_dir_name="models",
            min_free_bytes=5 * 1024 * 1024 * 1024,
        )
        self._start_posai_resource_download(resource)

    def _start_posai_resource_download(self, resource: PosAiResourceDefinition) -> None:
        if self._posai_download_thread is not None:
            self.posai_resource_status_label.setText("已有 PosAiImg 资源下载任务正在运行")
            return
        if not resource.url.strip():
            self.posai_resource_status_label.setText(f"{resource.label} 下载地址待配置")
            return
        download_dir = self._posai_download_dir()
        resources_dir = self._posai_resources_dir()
        self.posai_resource_download_progress.show()
        self.posai_resource_download_progress.setRange(0, 100)
        self.posai_resource_download_progress.setValue(0)
        self.download_posai_comfyui_button.setEnabled(False)
        self.download_posai_models_button.setEnabled(False)
        self.posai_resource_status_label.setText(f"正在下载 {resource.label}...")
        thread = QThread(self)
        worker = _PosAiResourceDownloadWorker(resource, str(download_dir), str(resources_dir))
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_posai_resource_progress)
        worker.finished.connect(self._on_posai_resource_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._cleanup_posai_resource_worker(thread, worker))
        self._posai_download_thread = thread
        self._posai_download_worker = worker
        thread.start()

    def _cleanup_posai_resource_worker(self, thread: QThread, worker: _PosAiResourceDownloadWorker) -> None:
        if self._posai_download_thread is thread:
            self._posai_download_thread = None
        if self._posai_download_worker is worker:
            self._posai_download_worker = None

    def _on_posai_resource_progress(self, received: int, total: int) -> None:
        if total <= 0:
            self.posai_resource_download_progress.setRange(0, 0)
            return
        self.posai_resource_download_progress.setRange(0, 100)
        self.posai_resource_download_progress.setValue(min(100, int(received * 100 / total)))

    def _on_posai_resource_finished(self, result) -> None:
        self.download_posai_comfyui_button.setEnabled(True)
        self.download_posai_models_button.setEnabled(True)
        self.posai_resource_download_progress.setRange(0, 100)
        self.posai_resource_download_progress.setValue(100 if result.ok else 0)
        self.posai_resource_status_label.setText(result.message)
        if result.ok and result.installed_path:
            path = Path(result.installed_path)
            if path.name.lower() == "comfyui":
                self.posai_comfyui_dir_edit.setText(str(path))
            else:
                self.posai_model_root_edit.setText(str(path))

    def _posai_download_dir(self) -> Path:
        configured = self.posai_resource_download_dir_edit.text().strip()
        path = Path(configured) if configured else default_download_dir("posai")
        self.posai_resource_download_dir_edit.setText(str(path))
        return path

    def _posai_resources_dir(self) -> Path:
        posai = resolve_project_dir("posaiimg", self._configured_posai_project_dir())
        if posai:
            return posai
        model_text = self.posai_model_root_edit.text().strip()
        return Path(model_text).parent if model_text else Path.cwd()

    def skip_current_version(self) -> None:
        release = self._latest_release or {}
        version = str(release.get("version") or "")
        if not version:
            return
        settings = self.store.load()
        settings.skipped_update_version = version
        self.store.save(settings)
        self.update_status_label.setText(f"已跳过 v{version}，启动时不再提示该版本")
        self.skip_version_button.setEnabled(False)

    def _provider_from_form(self, provider_id: str) -> AIProviderConfig:
        return AIProviderConfig(
            provider_id=provider_id,
            name=self.ai_provider_name_edit.text().strip() or "未命名接口",
            api_key=self.ai_edit_api_key_edit.text(),
            api_base=self.ai_edit_api_base_edit.text().strip() or "https://api.openai.com/v1",
            model=self.ai_edit_model_edit.text().strip() or "gpt-image-2",
            size=self.ai_edit_size_edit.text().strip() or "1024x1024",
        )

    def _sync_provider_form_into_memory(self) -> None:
        if self._provider_loading:
            return
        index = self.ai_provider_combo.currentIndex()
        if index < 0 or index >= len(self._provider_records):
            return
        self._provider_records[index] = self._provider_from_form(self._provider_records[index].provider_id)
        self.ai_provider_combo.setItemText(index, self._provider_records[index].name)

    def _load_provider_into_form(self, provider: AIProviderConfig) -> None:
        self._provider_loading = True
        self.ai_provider_name_edit.setText(provider.name)
        self.ai_edit_api_key_edit.setText(provider.api_key)
        self.ai_edit_api_base_edit.setText(provider.api_base)
        self.ai_edit_model_edit.setText(provider.model)
        self.ai_edit_size_edit.setText(provider.size)
        self._provider_loading = False

    def _load_providers(self, settings: AppSettings) -> None:
        self._provider_records = [AIProviderConfig(**provider.__dict__) for provider in settings.ai_providers]
        self.ai_provider_combo.blockSignals(True)
        self.ai_provider_combo.clear()
        for provider in self._provider_records:
            self.ai_provider_combo.addItem(provider.name, provider.provider_id)
        target_index = next(
            (index for index, provider in enumerate(self._provider_records) if provider.provider_id == settings.default_ai_provider_id),
            0,
        )
        self.ai_provider_combo.setCurrentIndex(target_index)
        self.ai_provider_combo.blockSignals(False)
        self._load_provider_into_form(self._provider_records[target_index])

    def _on_provider_changed(self, index: int) -> None:
        if self._provider_loading:
            return
        if index < 0 or index >= len(self._provider_records):
            return
        self._load_provider_into_form(self._provider_records[index])

    def _add_provider(self) -> None:
        self._sync_provider_form_into_memory()
        next_index = len(self._provider_records) + 1
        provider = AIProviderConfig(provider_id=f"provider-{next_index}", name=f"接口 {next_index}")
        self._provider_records.append(provider)
        self.ai_provider_combo.addItem(provider.name, provider.provider_id)
        self.ai_provider_combo.setCurrentIndex(len(self._provider_records) - 1)

    def _duplicate_provider(self) -> None:
        self._sync_provider_form_into_memory()
        index = self.ai_provider_combo.currentIndex()
        if index < 0 or index >= len(self._provider_records):
            return
        source = self._provider_records[index]
        duplicate_index = len(self._provider_records) + 1
        duplicate = AIProviderConfig(
            provider_id=f"provider-{duplicate_index}",
            name=f"{source.name} 副本",
            api_key=source.api_key,
            api_base=source.api_base,
            model=source.model,
            size=source.size,
        )
        self._provider_records.append(duplicate)
        self.ai_provider_combo.addItem(duplicate.name, duplicate.provider_id)
        self.ai_provider_combo.setCurrentIndex(len(self._provider_records) - 1)

    def _delete_provider(self) -> None:
        if len(self._provider_records) <= 1:
            return
        index = self.ai_provider_combo.currentIndex()
        if index < 0 or index >= len(self._provider_records):
            return
        del self._provider_records[index]
        self.ai_provider_combo.removeItem(index)
        self.ai_provider_combo.setCurrentIndex(max(0, min(index, len(self._provider_records) - 1)))

    def load_settings(self) -> None:
        settings = self.store.load()
        index = self.shop_combo.findText(settings.active_shop)
        self.shop_combo.blockSignals(True)
        self.shop_combo.setCurrentIndex(max(0, index))
        self.shop_combo.blockSignals(False)

        self.cdp_edit.setText(settings.cdp_endpoint)
        self.interval_spin.setValue(settings.refresh_interval_seconds)
        self.purchase_export_dir_edit.setText(settings.purchase_export_dir)
        self.print_gallery_source_combo.setCurrentText(
            "来自 GitHub" if settings.print_gallery_source == "github" else "本地图集中采集"
        )
        self.print_gallery_local_dir_edit.setText(settings.print_gallery_local_dir)
        self.print_gallery_github_raw_base_edit.setText(settings.print_gallery_github_raw_base_url)

        self.posai_gallery_root_edit.setText(settings.posai_gallery_root)
        self.posai_mockup_root_edit.setText(settings.posai_mockup_root)
        self.posai_xlsx_root_edit.setText(settings.posai_xlsx_root)
        self.posai_model_root_edit.setText(settings.posai_model_root)
        self.posai_comfyui_dir_edit.setText(settings.posai_comfyui_dir)
        self.posai_resource_download_dir_edit.setText(settings.posai_resource_download_dir)
        self.posai_comfyui_download_url_edit.setText(settings.posai_comfyui_download_url)
        self.posai_models_download_url_edit.setText(settings.posai_models_download_url)
        self._load_providers(settings)
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
        self.applygoods_project_dir_edit.setText(settings.applygoods_project_dir)
        self.program_data_dir_edit.setText(settings.program_data_dir)
        if hasattr(self, "theme_combo"):
            self.theme_combo.setCurrentIndex(0 if (settings.theme_name or "light") == "light" else 1)
        if hasattr(self, "bg_image_edit"):
            self.bg_image_edit.setText(settings.bg_image_path or "")
        if hasattr(self, "check_update_on_startup_check"):
            self.check_update_on_startup_check.setChecked(settings.check_update_on_startup)
        if hasattr(self, "update_proxy_enabled_check"):
            self.update_proxy_enabled_check.setChecked(settings.update_proxy_enabled)
        if hasattr(self, "update_proxy_host_edit"):
            self.update_proxy_host_edit.setText(settings.update_proxy_host or "127.0.0.1")
        if hasattr(self, "update_proxy_port_spin"):
            self.update_proxy_port_spin.setValue(max(1, min(65535, int(settings.update_proxy_port or 7890))))
        self.startup_width_spin.setValue(settings.startup_width)
        self.startup_height_spin.setValue(settings.startup_height)

        self._load_account_for_shop(self.shop_combo.currentText(), settings)
        self._refresh_path_status_labels()

    def save_settings(self) -> None:
        old_settings = self.store.load()
        self._sync_provider_form_into_memory()
        shop_name = self.shop_combo.currentText().strip() or "YUHOOBO"
        accounts = dict(old_settings.accounts)
        accounts[shop_name] = ShopAccount(
            shop_name=shop_name,
            phone=self.phone_edit.text().strip(),
            password=self.password_edit.text(),
        )
        provider_index = self.ai_provider_combo.currentIndex()
        default_provider = self._provider_records[max(0, provider_index)]
        settings = AppSettings(
            active_shop=shop_name,
            cdp_endpoint=self.cdp_edit.text().strip() or "http://127.0.0.1:9222",
            refresh_interval_seconds=self.interval_spin.value(),
            purchase_export_dir=self.purchase_export_dir_edit.text().strip(),
            print_gallery_source=(
                "github" if self.print_gallery_source_combo.currentText() == "来自 GitHub" else "local"
            ),
            print_gallery_local_dir=self.print_gallery_local_dir_edit.text().strip(),
            print_gallery_github_raw_base_url=self.print_gallery_github_raw_base_edit.text().strip(),
            local_image_auto_start_comfyui=old_settings.local_image_auto_start_comfyui,
            local_image_keep_comfyui=old_settings.local_image_keep_comfyui,
            local_image_test_mode=old_settings.local_image_test_mode,
            ai_edit_api_key=default_provider.api_key,
            ai_edit_api_base=default_provider.api_base,
            ai_edit_model=default_provider.model,
            ai_edit_size=default_provider.size,
            default_ai_provider_id=default_provider.provider_id,
            ai_providers=[AIProviderConfig(**provider.__dict__) for provider in self._provider_records],
            ai_edit_prompt=self.ai_edit_prompt_edit.toPlainText().strip() or DEFAULT_AI_EDIT_PROMPT,
            ai_edit_split_collage=old_settings.ai_edit_split_collage,
            ai_edit_split_count=old_settings.ai_edit_split_count,
            ai_edit_total_return_count=old_settings.ai_edit_total_return_count,
            ai_edit_reference_dir=old_settings.ai_edit_reference_dir,
            posai_gallery_root=self.posai_gallery_root_edit.text().strip(),
            posai_mockup_root=self.posai_mockup_root_edit.text().strip(),
            posai_xlsx_root=self.posai_xlsx_root_edit.text().strip(),
            posai_model_root=self.posai_model_root_edit.text().strip(),
            posai_comfyui_dir=self.posai_comfyui_dir_edit.text().strip(),
            posai_resource_download_dir=self.posai_resource_download_dir_edit.text().strip(),
            posai_comfyui_download_url=self.posai_comfyui_download_url_edit.text().strip(),
            posai_models_download_url=self.posai_models_download_url_edit.text().strip(),
            putaway_project_dir=self.putaway_project_dir_edit.text().strip(),
            putaway_data_dir=self.putaway_data_dir_edit.text().strip(),
            putaway_log_dir=self.putaway_log_dir_edit.text().strip(),
            applygoods_project_dir=self.applygoods_project_dir_edit.text().strip(),
            program_data_dir=self.program_data_dir_edit.text().strip(),
            theme_name="light" if self.theme_combo.currentIndex() == 0 else "dark",
            bg_image_path=self.bg_image_edit.text().strip(),
            check_update_on_startup=self.check_update_on_startup_check.isChecked(),
            last_update_check=old_settings.last_update_check,
            skipped_update_version=old_settings.skipped_update_version,
            update_download_dir=old_settings.update_download_dir,
            update_proxy_enabled=self.update_proxy_enabled_check.isChecked(),
            update_proxy_host=self.update_proxy_host_edit.text().strip() or "127.0.0.1",
            update_proxy_port=self.update_proxy_port_spin.value(),
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
        self._refresh_path_status_labels()
        self.settings_saved.emit(settings)

    def _resolved_project_status(self, key: str, configured: str) -> str:
        resolved = resolve_project_dir(key, configured, search_roots=default_project_search_roots())
        if configured.strip():
            return f"已配置：{resolved or configured}"
        if resolved:
            return f"自动探测到：{resolved}"
        project_names = {"posaiimg": "PosAiImg", "putaway": "PutawayAiRobot", "applygoods": "ApplyGoods"}
        return f"未找到 {project_names.get(key, key)}，请手动选择目录"

    def _refresh_path_status_labels(self) -> None:
        if "posaiimg" in self.path_status_labels:
            self.path_status_labels["posaiimg"].setText(
                self._resolved_project_status("posaiimg", self._configured_posai_project_dir())
            )
        if "putaway" in self.path_status_labels:
            self.path_status_labels["putaway"].setText(
                self._resolved_project_status("putaway", self.putaway_project_dir_edit.text())
            )
        if "applygoods" in self.path_status_labels:
            self.path_status_labels["applygoods"].setText(
                self._resolved_project_status("applygoods", self.applygoods_project_dir_edit.text())
            )

    def _configured_posai_project_dir(self) -> str:
        for edit in (
            self.posai_gallery_root_edit,
            self.posai_mockup_root_edit,
            self.posai_xlsx_root_edit,
            self.posai_model_root_edit,
            self.posai_comfyui_dir_edit,
        ):
            path = Path(edit.text().strip())
            if path.parts:
                return str(path if path.name == "PosAiImg" else path.parent)
        return ""

    def detect_project_paths(self) -> None:
        posai = resolve_project_dir("posaiimg", self._configured_posai_project_dir())
        if posai and not self._configured_posai_project_dir():
            self.posai_gallery_root_edit.setText(str(posai / "图库"))
            self.posai_mockup_root_edit.setText(str(posai / "批量贴图结果"))
            self.posai_xlsx_root_edit.setText(str(posai / "衣物对应的xlsx"))
            self.posai_model_root_edit.setText(str(posai / "模特图-干净"))
        if posai and not self.posai_comfyui_dir_edit.text().strip():
            self.posai_comfyui_dir_edit.setText(str(posai / "ComfyUI"))
        if posai and not self.posai_resource_download_dir_edit.text().strip():
            self.posai_resource_download_dir_edit.setText(str(default_download_dir("posai")))
        putaway = resolve_project_dir("putaway", self.putaway_project_dir_edit.text())
        if putaway and not self.putaway_project_dir_edit.text().strip():
            self.putaway_project_dir_edit.setText(str(putaway))
            self.putaway_data_dir_edit.setText(str(putaway / "data"))
            self.putaway_log_dir_edit.setText(str(putaway / "log"))
        applygoods = resolve_project_dir("applygoods", self.applygoods_project_dir_edit.text())
        if applygoods and not self.applygoods_project_dir_edit.text().strip():
            self.applygoods_project_dir_edit.setText(str(applygoods))
        self._refresh_path_status_labels()

    def detect_posai_resources(self) -> None:
        posai = resolve_project_dir("posaiimg", self._configured_posai_project_dir())
        if posai:
            self.posai_comfyui_dir_edit.setText(str(posai / "ComfyUI"))
            if not self.posai_model_root_edit.text().strip():
                self.posai_model_root_edit.setText(str(posai / "models"))
            if not self.posai_resource_download_dir_edit.text().strip():
                self.posai_resource_download_dir_edit.setText(str(default_download_dir("posai")))
            self.posai_resource_status_label.setText(f"已按 PosAiImg 目录检测资源：{posai}")
        else:
            self.posai_resource_status_label.setText("未找到 PosAiImg 目录，请先选择模块目录或下载资源")

    def clear_posai_resources(self) -> None:
        self.posai_comfyui_dir_edit.clear()
        self.posai_model_root_edit.clear()
        self.posai_resource_status_label.setText("已清除 PosAiImg 资源路径")

    def _choose_directory_for(self, edit: QLineEdit, title: str) -> None:
        path = QFileDialog.getExistingDirectory(self, title, edit.text())
        if path:
            edit.setText(path)

    def choose_export_dir(self) -> None:
        self._choose_directory_for(self.purchase_export_dir_edit, "选择拿货表导出目录")

    def choose_print_gallery_local_dir(self) -> None:
        self._choose_directory_for(self.print_gallery_local_dir_edit, "选择印花图集目录")

    def choose_posai_gallery_root(self) -> None:
        self._choose_directory_for(self.posai_gallery_root_edit, "选择图库目录")

    def choose_posai_mockup_root(self) -> None:
        self._choose_directory_for(self.posai_mockup_root_edit, "选择产品图目录")

    def choose_posai_xlsx_root(self) -> None:
        self._choose_directory_for(self.posai_xlsx_root_edit, "选择 XLSX 目录")

    def choose_posai_model_root(self) -> None:
        self._choose_directory_for(self.posai_model_root_edit, "选择模特底图目录")

    def choose_posai_comfyui_dir(self) -> None:
        self._choose_directory_for(self.posai_comfyui_dir_edit, "选择 ComfyUI 目录")

    def choose_posai_resource_download_dir(self) -> None:
        self._choose_directory_for(self.posai_resource_download_dir_edit, "选择 PosAiImg 资源下载目录")

    def choose_putaway_project_dir(self) -> None:
        self._choose_directory_for(self.putaway_project_dir_edit, "选择 Putaway 项目目录")

    def choose_putaway_data_dir(self) -> None:
        self._choose_directory_for(self.putaway_data_dir_edit, "选择 Putaway data 目录")

    def choose_putaway_log_dir(self) -> None:
        self._choose_directory_for(self.putaway_log_dir_edit, "选择 Putaway 日志目录")

    def choose_applygoods_project_dir(self) -> None:
        self._choose_directory_for(self.applygoods_project_dir_edit, "选择 ApplyGoods 项目目录")

    def choose_program_data_dir(self) -> None:
        self._choose_directory_for(self.program_data_dir_edit, "选择程序数据目录")

    def choose_bg_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择背景图", "", "图片 (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.bg_image_edit.setText(path)

    def _load_account_for_shop(self, shop_name: str, settings: AppSettings | None = None) -> None:
        settings = settings or self.store.load()
        account = settings.accounts.get(shop_name) or ShopAccount(shop_name=shop_name)
        self.phone_edit.setText(account.phone)
        self.password_edit.setText(account.password)
