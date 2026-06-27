from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from PyQt5.QtCore import QObject, Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from app_paths import runtime_root
from models import GoodsListResult
from settings import load_settings, save_settings
from temu_goods import (
    COMPLIANCE_INFO_URL,
    COMPLIANT_LIVE_PHOTOS_BATCH_URL,
    GOODS_LIST_URL,
    JIT_PRODUCT_SELECT_URL,
    STOCK_SALE_MANAGE_URL,
    TEMPLATE_GROUP_URL,
    TemuGoodsList,
)


ROOT = runtime_root()
APP_VERSION = "V1.9.3"


@dataclass(frozen=True)
class ChainStepResult:
    name: str
    success: bool
    message: str


@dataclass(frozen=True)
class TaskResult:
    summary: str
    level: str = "info"


def _short_status(level: str) -> str:
    return {"info": "已完成", "warning": "执行失败", "stopped": "已停止"}.get(level, "已完成")


@dataclass(frozen=True)
class WorkerTaskContext:
    worker: TemuGoodsList
    page_size: int
    logger: Callable[[str], None]
    should_stop: Callable[[], bool]


class WorkerTask(QObject):
    log_message = pyqtSignal(str)
    finished = pyqtSignal(object)
    failed = pyqtSignal(str, str)

    def __init__(
        self,
    task: Callable[[WorkerTaskContext], TaskResult],
    user_data_dir,
    cdp_endpoint: str,
    page_size: int,
    login_phone: str = "",
    login_password: str = "",
    ) -> None:
        super().__init__()
        self.task = task
        self.user_data_dir = user_data_dir
        self.cdp_endpoint = cdp_endpoint
        self.page_size = page_size
        self.login_phone = login_phone
        self.login_password = login_password
        self.worker: TemuGoodsList | None = None
        self.stop_requested = False

    def run(self) -> None:
        worker = TemuGoodsList(
            user_data_dir=self.user_data_dir,
            cdp_endpoint=self.cdp_endpoint,
            logger=self.log_message.emit,
        )
        worker.set_login_credentials(self.login_phone, self.login_password)
        self.worker = worker
        try:
            if self.stop_requested:
                self.finished.emit(TaskResult("任务已停止。", level="stopped"))
                return
            result = self.task(
                WorkerTaskContext(
                    worker=worker,
                    page_size=self.page_size,
                    logger=self.log_message.emit,
                    should_stop=lambda: self.stop_requested,
                )
            )
            if self.stop_requested:
                self.finished.emit(TaskResult("任务已停止。", level="stopped"))
            else:
                self.finished.emit(result)
        except Exception as exc:  # noqa: BLE001 - show task errors in the GUI.
            if self.stop_requested:
                self.finished.emit(TaskResult("任务已停止。", level="stopped"))
            else:
                self.failed.emit(type(exc).__name__, str(exc))
        finally:
            try:
                worker.session.detach()
            finally:
                self.worker = None

    def request_stop(self) -> None:
        self.stop_requested = True


def run_chain_steps(
    steps: list[tuple[str, Callable[[], str]]],
    logger: Callable[[str], None],
    should_stop: Callable[[], bool] | None = None,
) -> list[ChainStepResult]:
    results: list[ChainStepResult] = []
    should_stop = should_stop or (lambda: False)
    for name, action in steps:
        if should_stop():
            logger("任务已请求停止，跳过后续步骤。")
            break
        logger(f"开始：{name}")
        try:
            message = action() or "已完成"
        except Exception as exc:  # noqa: BLE001 - full-chain mode must keep later steps running.
            message = str(exc)
            logger(f"失败：{name}：{message}")
            results.append(ChainStepResult(name=name, success=False, message=message))
            continue
        logger(f"完成：{name}：{message}")
        results.append(ChainStepResult(name=name, success=True, message=message))
    return results


def cleanup_transient_site_popups(worker: TemuGoodsList, logger: Callable[[str], None]) -> None:
    closed_count = worker.dismiss_transient_site_popups()
    if closed_count:
        logger(f"已清理网站弹窗：{closed_count} 个。")


def run_guarded_chain_steps(
    steps: list[tuple[str, Callable[[], str]]],
    worker: TemuGoodsList,
    logger: Callable[[str], None],
    should_stop: Callable[[], bool] | None = None,
) -> list[ChainStepResult]:
    results: list[ChainStepResult] = []
    should_stop = should_stop or (lambda: False)
    cleanup_transient_site_popups(worker, logger)
    for name, action in steps:
        if should_stop():
            logger("任务已请求停止，跳过后续步骤。")
            break
        logger(f"开始：{name}")
        try:
            cleanup_transient_site_popups(worker, logger)
            message = action() or "已完成"
            cleanup_transient_site_popups(worker, logger)
        except Exception as exc:  # noqa: BLE001 - full-chain mode must keep later steps running.
            message = str(exc)
            logger(f"失败：{name}：{message}")
            results.append(ChainStepResult(name=name, success=False, message=message))
            cleanup_transient_site_popups(worker, logger)
            continue
        logger(f"完成：{name}：{message}")
        results.append(ChainStepResult(name=name, success=True, message=message))
    cleanup_transient_site_popups(worker, logger)
    return results


def run_template_group_management(
    worker: TemuGoodsList,
    page_size: int,
) -> tuple[GoodsListResult, int]:
    result = worker.prepare_and_collect_skc_ids(
        copy_to_clipboard=True,
        target_page_size=page_size,
    )
    if not result.raw_skc_text:
        raise RuntimeError("缺少 SKC ID，请检查批量复制结果。")
    added_count = worker.apply_to_template_group(result.raw_skc_text)
    return result, added_count


def compliance_upload_steps(worker: TemuGoodsList, target_page_size: int) -> list[tuple[str, Callable[[], str]]]:
    return [
        ("批量上传加州65号提案", lambda: f"已上传 {worker.upload_california_65_compliance_info(target_page_size=target_page_size)} 个商品"),
        ("批量上传制造商属性", lambda: f"已上传 {worker.upload_manufacturer_attribute_compliance_info(target_page_size=target_page_size)} 个商品"),
        ("批量上传生产/保质期", lambda: f"已上传 {worker.upload_production_shelf_life_compliance_info(target_page_size=target_page_size)} 个商品"),
        ("批量上传警告或安全信息", lambda: f"已上传 {worker.upload_warning_safety_supplement_compliance_info(target_page_size=target_page_size)} 个商品"),
        ("批量上传包装材料信息", lambda: f"已上传 {worker.upload_packaging_material_compliance_info(target_page_size=target_page_size)} 个商品"),
        ("批量上传土耳其负责人", lambda: f"已上传 {worker.upload_turkey_responsible_person_compliance_info(target_page_size=target_page_size)} 个商品"),
        ("批量上传制造商信息", lambda: f"已上传 {worker.upload_manufacturer_info_compliance_info(target_page_size=target_page_size)} 个商品"),
        ("批量上传欧盟负责人", lambda: f"已上传 {worker.upload_eu_responsible_person_compliance_info(target_page_size=target_page_size)} 个商品"),
        ("批量上传商品识别码", lambda: f"已导入 SPU {worker.upload_product_identifier_file(target_page_size=target_page_size).spu_count} 个"),
        ("批量上传商品合规图", lambda: f"已提交 {worker.upload_compliant_live_photos(submit=True)} 个商品"),
    ]


def run_compliance_upload_steps(
    worker: TemuGoodsList,
    logger: Callable[[str], None],
    target_page_size: int,
    should_stop: Callable[[], bool] | None = None,
) -> list[ChainStepResult]:
    return run_chain_steps(compliance_upload_steps(worker, target_page_size), logger, should_stop=should_stop)


def run_full_chain_steps(
    worker: TemuGoodsList,
    logger: Callable[[str], None],
    target_page_size: int,
    should_stop: Callable[[], bool] | None = None,
) -> list[ChainStepResult]:
    def template_group_management() -> str:
        result, added_count = run_template_group_management(worker, target_page_size)
        return f"已获取 {result.skc_count} 个 SKC ID，搜索结果检测到 {added_count} 个"

    def upload_all_compliance() -> str:
        results = run_compliance_upload_steps(
            worker,
            logger,
            target_page_size,
            should_stop=should_stop,
        )
        summary = summarize_step_results("批量上传合规信息", results)
        if any(not result.success for result in results):
            raise RuntimeError(summary.summary)
        return summary.summary

    def open_jit() -> str:
        selected_count = worker.batch_open_jit_management(submit=True, target_page_size=target_page_size)
        return f"已开通 {selected_count} 个商品"

    steps: list[tuple[str, Callable[[], str]]] = [
        ("套版组管理", template_group_management),
        ("批量上传合规信息", upload_all_compliance),
        ("批量开通JIT管理", open_jit),
    ]
    return run_guarded_chain_steps(steps, worker, logger, should_stop=should_stop)


def summarize_step_results(title: str, results: list[ChainStepResult]) -> TaskResult:
    failed = [result for result in results if not result.success]
    succeeded = [result for result in results if result.success]
    if failed:
        failed_text = "；".join(f"{result.name}：{result.message}" for result in failed)
        return TaskResult(
            summary=f"{title}完成：成功 {len(succeeded)} 项，失败 {len(failed)} 项。失败步骤：{failed_text}",
            level="warning",
        )
    return TaskResult(summary=f"{title}完成：全部 {len(succeeded)} 项成功。")


class ApplyGoodsEmbeddedWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.worker = TemuGoodsList(user_data_dir=ROOT / ".browser-profile", logger=self.log)
        self.last_result: GoodsListResult | None = None
        self.action_buttons: list[QPushButton] = []
        self.stop_button: QPushButton | None = None
        self.current_thread: QThread | None = None
        self.current_task: WorkerTask | None = None
        self.settings_path = ROOT / "settings.json"
        self.settings = load_settings(self.settings_path)
        self._loading_settings = True

        self.goods_url_edit = QLineEdit(GOODS_LIST_URL)
        self.goods_url_edit.setReadOnly(True)
        self.template_url_edit = QLineEdit(TEMPLATE_GROUP_URL)
        self.template_url_edit.setReadOnly(True)
        self.compliance_url_edit = QLineEdit(COMPLIANCE_INFO_URL)
        self.compliance_url_edit.setReadOnly(True)
        self.live_photos_url_edit = QLineEdit(COMPLIANT_LIVE_PHOTOS_BATCH_URL)
        self.live_photos_url_edit.setReadOnly(True)
        self.jit_url_edit = QLineEdit(JIT_PRODUCT_SELECT_URL)
        self.jit_url_edit.setReadOnly(True)
        self.stock_sale_url_edit = QLineEdit(STOCK_SALE_MANAGE_URL)
        self.stock_sale_url_edit.setReadOnly(True)
        self.cdp_edit = QLineEdit("http://127.0.0.1:9222")
        self.login_phone_edit = QLineEdit()
        self.login_phone_edit.setPlaceholderText("用于需要重新登录时自动填写")
        self.login_password_edit = QLineEdit()
        self.login_password_edit.setEchoMode(QLineEdit.Password)
        self.login_password_edit.setPlaceholderText("用于需要重新登录时自动填写")
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["50", "100", "自定义"])
        self.custom_page_size = QSpinBox()
        self.custom_page_size.setRange(1, 500)
        self.custom_page_size.setValue(50)
        self.custom_page_size.setEnabled(False)
        self._apply_settings_to_ui()
        self.page_size_combo.currentTextChanged.connect(self.on_page_size_mode_changed)
        self.custom_page_size.valueChanged.connect(self.save_ui_settings)
        self.login_phone_edit.textChanged.connect(self.save_ui_settings)
        self.login_password_edit.textChanged.connect(self.save_ui_settings)
        self._loading_settings = False

        self.summary_label = QLabel("尚未执行")
        self.summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.summary_label.setMaximumWidth(120)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumBlockCount(1000)

        self._build_ui()

    def _build_ui(self) -> None:
        self.setObjectName("appRoot")
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 18)
        root.setSpacing(14)

        header = QFrame()
        header.setObjectName("headerPanel")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 20, 24, 20)
        header_layout.setSpacing(22)

        title_col = QVBoxLayout()
        title_col.setSpacing(6)
        eyebrow_label = QLabel("真实流程工作台")
        eyebrow_label.setObjectName("headerEyebrow")
        title_label = QLabel("ApplyGoods 商品申请自动化")
        title_label.setObjectName("appTitle")
        subtitle_label = QLabel("简洁工具台：连接浏览器、批量处理商品申请资料，并跟踪执行日志")
        subtitle_label.setObjectName("appSubtitle")
        subtitle_label.setWordWrap(True)
        subtitle_label.setMaximumWidth(520)
        title_col.addWidget(eyebrow_label)
        title_col.addWidget(title_label)
        title_col.addWidget(subtitle_label)
        header_layout.addLayout(title_col, stretch=1)

        status_col = QVBoxLayout()
        status_col.setSpacing(8)
        status_col.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        version_label = QLabel(APP_VERSION)
        version_label.setObjectName("versionPill")
        self.summary_label.setObjectName("summaryPill")
        status_col.addWidget(version_label, alignment=Qt.AlignRight)
        status_col.addWidget(self.summary_label, alignment=Qt.AlignRight)
        header_layout.addLayout(status_col)
        root.addWidget(header)

        left_form = QGridLayout()
        left_form.setHorizontalSpacing(10)
        left_form.setVerticalSpacing(12)
        left_form.addWidget(QLabel("商品列表页面"), 0, 0)
        left_form.addWidget(self.goods_url_edit, 0, 1)
        left_form.addWidget(QLabel("合规信息页面"), 1, 0)
        left_form.addWidget(self.compliance_url_edit, 1, 1)
        left_form.addWidget(QLabel("JIT商品选择页面"), 2, 0)
        left_form.addWidget(self.jit_url_edit, 2, 1)
        left_form.addWidget(QLabel("Chrome 调试地址"), 3, 0)
        left_form.addWidget(self.cdp_edit, 3, 1)
        left_form.addWidget(QLabel("登录账号"), 4, 0)
        left_form.addWidget(self.login_phone_edit, 4, 1)
        left_form.setColumnStretch(1, 1)

        right_form = QGridLayout()
        right_form.setHorizontalSpacing(10)
        right_form.setVerticalSpacing(12)
        right_form.addWidget(QLabel("套版组页面"), 0, 0)
        right_form.addWidget(self.template_url_edit, 0, 1)
        right_form.addWidget(QLabel("商品合规图页面"), 1, 0)
        right_form.addWidget(self.live_photos_url_edit, 1, 1)
        right_form.addWidget(QLabel("销售管理库存页面"), 2, 0)
        right_form.addWidget(self.stock_sale_url_edit, 2, 1)
        right_form.addWidget(QLabel("分页数量设置"), 3, 0)
        page_size_row = QHBoxLayout()
        page_size_row.addWidget(self.page_size_combo)
        page_size_row.addWidget(self.custom_page_size)
        page_size_row.addStretch(1)
        right_form.addLayout(page_size_row, 3, 1)
        right_form.addWidget(QLabel("登录密码"), 4, 0)
        right_form.addWidget(self.login_password_edit, 4, 1)
        right_form.setColumnStretch(1, 1)

        form_cards = QVBoxLayout()
        form_cards.setSpacing(14)
        left_form_card = self._create_subsection("浏览器与登录", "连接入口、调试地址和登录回填。", left_form)
        right_form_card = self._create_subsection("目标页面与分页", "套版组、合规图、库存页和分页控制。", right_form)
        form_cards.addWidget(left_form_card)
        form_cards.addWidget(right_form_card)
        root.addWidget(self._create_section("连接与页面设置", "固定页面入口和执行分页，便于核对自动化目标。", form_cards))

        open_btn = QPushButton("打开/连接浏览器")
        self._create_action_button(open_btn, "secondary")
        open_btn.clicked.connect(self.open_browser)
        full_chain_btn = QPushButton("批量一条龙操作")
        self._create_action_button(full_chain_btn, "primary")
        full_chain_btn.clicked.connect(self.run_full_chain)
        template_btn = QPushButton("套版组管理")
        self._create_action_button(template_btn, "secondary")
        template_btn.clicked.connect(self.apply_template_group)
        compliance_btn = QPushButton("批量上传合规信息")
        self._create_action_button(compliance_btn, "secondary")
        compliance_btn.clicked.connect(self.upload_all_compliance_info)
        compliance_single_btn = QPushButton("单项合规上传")
        self._create_action_button(compliance_single_btn, "ghost")
        compliance_single_btn.clicked.connect(self.open_single_compliance_dialog)
        stop_btn = QPushButton("停止当前任务")
        self._create_action_button(stop_btn, "danger")
        stop_btn.setEnabled(False)
        stop_btn.clicked.connect(self.stop_current_task)
        self.stop_button = stop_btn
        jit_btn = QPushButton("批量开通JIT管理")
        self._create_action_button(jit_btn, "secondary")
        jit_btn.clicked.connect(self.batch_open_jit_management)
        expected_area_btn = QPushButton("批量设置期望到货区域")
        self._create_action_button(expected_area_btn, "secondary")
        expected_area_btn.clicked.connect(self.batch_set_expected_arrival_area)
        inventory_btn = QPushButton("批量导入库存设置")
        self._create_action_button(inventory_btn, "secondary")
        inventory_btn.clicked.connect(self.upload_inventory_setting)

        operations_card = QFrame()
        operations_card.setObjectName("actionBoard")
        operations = QVBoxLayout(operations_card)
        operations.setContentsMargins(18, 16, 18, 16)
        operations.setSpacing(12)
        operations.addWidget(
            self._create_operation_group(
                "核心流程",
                "先连接浏览器，再执行整链路或单独套版组流程。",
                [open_btn, full_chain_btn, template_btn, stop_btn],
            )
        )
        operations.addWidget(
            self._create_operation_group(
                "资料上传",
                "合规资料分成批量和单项入口，便于人工补救。",
                [compliance_btn, compliance_single_btn],
            )
        )
        operations.addWidget(
            self._create_operation_group(
                "后置管理",
                "把 JIT、到货区域和库存设置集中到最后，避免和前置动作混在一起。",
                [jit_btn, expected_area_btn, inventory_btn],
            )
        )
        root.addWidget(self._create_section("操作中心", "常用流程按业务分组排列，正式执行前请确认页面和分页设置。", operations_card))

        action_buttons = [
            open_btn,
            full_chain_btn,
            template_btn,
            compliance_btn,
            compliance_single_btn,
            jit_btn,
            expected_area_btn,
            inventory_btn,
        ]
        self.action_buttons = action_buttons

        log_layout = QVBoxLayout()
        log_layout.setSpacing(10)
        log_note = QLabel("保留最近 1000 条日志，便于回查失败步骤、页面状态和收尾结果。")
        log_note.setObjectName("logNote")
        log_note.setWordWrap(True)
        self.log_box.setMinimumHeight(220)
        log_layout.addWidget(log_note)
        log_layout.addWidget(self.log_box, stretch=1)
        root.addWidget(self._create_section("运行日志", "运行过程、失败原因和完成摘要会保留在这里。", log_layout), stretch=1)
        self._apply_visual_style()

    def _create_section(self, title: str, subtitle: str, content_layout) -> QFrame:
        section = QFrame()
        section.setObjectName("sectionPanel")
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(14, 11, 14, 13)
        section_layout.setSpacing(7)

        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("sectionSubtitle")
        section_layout.addWidget(title_label)
        section_layout.addWidget(subtitle_label)
        if isinstance(content_layout, QWidget):
            section_layout.addWidget(content_layout)
        else:
            section_layout.addLayout(content_layout)
        return section

    # 已停用：内嵌与独立运行均不再展示「流程总览」步骤卡。保留以备将来复用。
    def _create_workflow_step(self, number: str, title: str, hint: str) -> QFrame:
        step = QFrame()
        step.setObjectName("workflowStep")
        step.setMinimumWidth(170)
        step_layout = QHBoxLayout(step)
        step_layout.setContentsMargins(16, 14, 16, 14)
        step_layout.setSpacing(12)

        number_label = QLabel(number)
        number_label.setObjectName("workflowNumber")
        title_label = QLabel(title)
        title_label.setObjectName("workflowText")
        hint_label = QLabel(hint)
        hint_label.setObjectName("workflowHint")
        hint_label.setWordWrap(True)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        text_layout.addWidget(title_label)
        text_layout.addWidget(hint_label)

        step_layout.addWidget(number_label, alignment=Qt.AlignTop)
        step_layout.addLayout(text_layout, stretch=1)
        return step

    def _create_subsection(self, title: str, subtitle: str, content_layout) -> QFrame:
        section = QFrame()
        section.setObjectName("subSectionCard")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("subSectionTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("subSectionSubtitle")
        subtitle_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addLayout(content_layout)
        return section

    def _create_operation_group(
        self,
        title: str,
        subtitle: str,
        buttons: list[QPushButton],
        columns: int = 2,
    ) -> QFrame:
        button_grid = QGridLayout()
        button_grid.setHorizontalSpacing(12)
        button_grid.setVerticalSpacing(10)
        for index, button in enumerate(buttons):
            row = index // columns
            column = index % columns
            button_grid.addWidget(button, row, column)
        for column in range(columns):
            button_grid.setColumnStretch(column, 1)
        return self._create_subsection(title, subtitle, button_grid)

    def _create_action_button(self, button: QPushButton, role: str) -> QPushButton:
        button.setProperty("role", role)
        button.setMinimumHeight(38)
        button.setCursor(Qt.PointingHandCursor)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return button

    def _apply_visual_style(self) -> None:
        self.setStyleSheet(
            """
            QWidget#appRoot {
                background: transparent;
                color: #1f2937;
                font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI";
                font-size: 13px;
            }
            QFrame#headerPanel, QFrame#sectionPanel {
                background: #ffffff;
                border: 1px solid #d9e2ef;
                border-radius: 14px;
            }
            QFrame#headerPanel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffffff, stop:1 #f4f8fd);
            }
            QLabel#headerEyebrow {
                color: #457dbd;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 1px;
            }
            QLabel#appTitle {
                color: #111827;
                font-size: 25px;
                font-weight: 700;
            }
            QLabel#appSubtitle, QLabel#sectionSubtitle {
                color: #6b7280;
                font-size: 12px;
            }
            QLabel#versionPill, QLabel#summaryPill {
                background: #eef6ff;
                border: 1px solid #d9e7f6;
                border-radius: 10px;
                color: #457dbd;
                font-weight: 600;
                padding: 8px 12px;
            }
            QLabel#summaryPill {
                background: #ecfdf5;
                border-color: #bbf7d0;
                color: #047857;
            }
            QLabel#sectionTitle {
                color: #111827;
                font-size: 16px;
                font-weight: 700;
            }
            QLabel#sectionSubtitle {
                color: #6b7280;
                font-size: 12px;
                padding-bottom: 2px;
            }
            QLabel#groupTitle {
                color: #475569;
                font-size: 12px;
                font-weight: 700;
            }
            QFrame#subSectionCard {
                background: #f9fbff;
                border: 1px solid #e1e9f4;
                border-radius: 12px;
            }
            QLabel#subSectionTitle {
                color: #1f2937;
                font-size: 14px;
                font-weight: 700;
            }
            QLabel#subSectionSubtitle {
                color: #7b8794;
                font-size: 11px;
            }
            QFrame#actionBoard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f8fbff, stop:1 #f1f6ff);
                border: 1px solid #d9e6f6;
                border-radius: 12px;
            }
            QLabel#logNote {
                color: #64748b;
                font-size: 11px;
            }
            QLineEdit, QComboBox, QSpinBox {
                background: #ffffff;
                border: 1px solid #d9e2ef;
                border-radius: 8px;
                min-height: 34px;
                padding: 5px 10px;
                selection-background-color: #5d96d8;
            }
            QLineEdit:read-only {
                color: #4b5563;
            }
            QPushButton {
                border: 1px solid #d9e2ef;
                border-radius: 9px;
                color: #243042;
                font-weight: 600;
                padding: 10px 12px;
            }
            QPushButton:hover {
                border-color: #70a5e3;
            }
            QPushButton:disabled {
                background: #eef1f5;
                color: #9aa3b2;
            }
            QPushButton[role="primary"] {
                background: #5d96d8;
                border-color: #5d96d8;
                color: #ffffff;
            }
            QPushButton[role="primary"]:hover {
                background: #70a5e3;
            }
            QPushButton[role="primary"]:pressed {
                background: #457dbd;
            }
            QPushButton[role="secondary"] {
                background: #ffffff;
            }
            QPushButton[role="ghost"] {
                background: #f8fafc;
                color: #475569;
            }
            QPushButton[role="danger"] {
                background: #fff1f2;
                border-color: #fecdd3;
                color: #be123c;
            }
            QPushButton[role="danger"]:hover {
                background: #ffe4e6;
                border-color: #fb7185;
            }
            QPushButton[role="danger"]:disabled {
                background: #f3f4f6;
                border-color: #e5e7eb;
                color: #a1a1aa;
            }
            QPlainTextEdit {
                background: #0b1220;
                border: 1px solid #1c2940;
                border-radius: 10px;
                color: #dbeafe;
                font-family: "Cascadia Mono", "Consolas", monospace;
                font-size: 12px;
                padding: 12px;
            }
            """
        )

    def refresh_worker(self) -> None:
        self.worker.session.cdp_endpoint = self.cdp_edit.text().strip() or "http://127.0.0.1:9222"
        self.worker.set_login_credentials(self.login_phone_edit.text().strip(), self.login_password_edit.text())

    def on_page_size_mode_changed(self, value: str) -> None:
        self.custom_page_size.setEnabled(value == "自定义")
        self.save_ui_settings()

    def selected_page_size(self) -> int:
        value = self.page_size_combo.currentText()
        if value == "自定义":
            return int(self.custom_page_size.value())
        return int(value)

    def _apply_settings_to_ui(self) -> None:
        mode = str(self.settings.get("page_size_mode", "50"))
        if mode not in {"50", "100", "自定义"}:
            mode = "50"
        custom_size = int(self.settings.get("custom_page_size", 50) or 50)
        custom_size = max(1, min(500, custom_size))
        self.page_size_combo.setCurrentText(mode)
        self.custom_page_size.setValue(custom_size)
        self.custom_page_size.setEnabled(mode == "自定义")
        self.login_phone_edit.setText(str(self.settings.get("login_phone", "")))
        self.login_password_edit.setText(str(self.settings.get("login_password", "")))

    def save_ui_settings(self, *_args) -> None:
        if self._loading_settings:
            return
        self.settings["page_size_mode"] = self.page_size_combo.currentText()
        self.settings["custom_page_size"] = int(self.custom_page_size.value())
        self.settings["login_phone"] = self.login_phone_edit.text().strip()
        self.settings["login_password"] = self.login_password_edit.text()
        save_settings(self.settings_path, self.settings)

    def run_worker_task(
        self,
        title: str,
        task: Callable[[WorkerTaskContext], TaskResult],
    ) -> None:
        if self.current_thread and self.current_thread.isRunning():
            QMessageBox.warning(self, "任务正在运行", "当前已有任务在运行，请等待完成后再执行新的操作。")
            return
        self.refresh_worker()
        self.summary_label.setText("执行中")
        self.summary_label.setToolTip(f"{title}：运行中…")
        self.set_actions_enabled(False)
        self.set_stop_enabled(True)
        thread = QThread(self)
        worker_task = WorkerTask(
            task=task,
            user_data_dir=ROOT / ".browser-profile",
            cdp_endpoint=self.cdp_edit.text().strip() or "http://127.0.0.1:9222",
            page_size=self.selected_page_size(),
            login_phone=self.login_phone_edit.text().strip(),
            login_password=self.login_password_edit.text(),
        )
        worker_task.moveToThread(thread)
        thread.started.connect(worker_task.run)
        worker_task.log_message.connect(self.log)
        worker_task.finished.connect(lambda result, task_title=title: self.on_worker_finished(task_title, result))
        worker_task.failed.connect(lambda error_type, message, task_title=title: self.on_worker_failed(task_title, error_type, message))
        worker_task.finished.connect(thread.quit)
        worker_task.failed.connect(thread.quit)
        thread.finished.connect(worker_task.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self.clear_worker_task)
        self.current_thread = thread
        self.current_task = worker_task
        thread.start()

    def set_actions_enabled(self, enabled: bool) -> None:
        for button in self.action_buttons:
            button.setEnabled(enabled)

    def set_stop_enabled(self, enabled: bool) -> None:
        if self.stop_button is not None:
            self.stop_button.setEnabled(enabled)

    def clear_worker_task(self) -> None:
        self.current_thread = None
        self.current_task = None
        self.set_actions_enabled(True)
        self.set_stop_enabled(False)

    def stop_current_task(self, show_message: bool = True) -> None:
        if not self.current_thread or not self.current_thread.isRunning():
            return
        self.summary_label.setText("停止中")
        self.summary_label.setToolTip("正在停止当前任务…")
        self.log("正在停止当前任务。")
        self.set_stop_enabled(False)
        if self.current_task is not None:
            self.current_task.request_stop()
        self.current_thread.requestInterruption()
        self.force_stop_worker_thread()

    def force_stop_worker_thread(self, log_once: bool = True) -> None:
        if not self.current_thread or not self.current_thread.isRunning():
            return
        if log_once:
            self.log("任务未及时退出，强制停止后台线程。")
        self.current_thread.terminate()
        if self.current_thread.wait(300):
            self.clear_worker_task()
            return
        QTimer.singleShot(300, lambda: self.force_stop_worker_thread(log_once=False))

    def on_worker_finished(self, title: str, result: TaskResult) -> None:
        self.summary_label.setText(_short_status(result.level))
        self.summary_label.setToolTip(result.summary)
        self.log(result.summary)
        if result.level == "stopped":
            return
        if result.level == "warning":
            QMessageBox.warning(self, f"{title}完成，有失败步骤", result.summary)
        else:
            QMessageBox.information(self, f"{title}完成", result.summary)

    def on_worker_failed(self, title: str, error_type: str, message: str) -> None:
        self.show_error(f"{title}失败", RuntimeError(f"{error_type}：{message}"))

    def open_browser(self) -> None:
        def task(context: WorkerTaskContext) -> TaskResult:
            page = context.worker.open_goods_list()
            context.logger(f"浏览器已准备好：{page.url}")
            if "auth/authentication" in page.url:
                context.logger("页面需要登录，请先在浏览器中完成登录。")
            return TaskResult(f"打开/连接浏览器：已准备好。当前页面：{page.url}")

        self.run_worker_task("打开/连接浏览器", task)

    def apply_template_group(self) -> None:
        def task(context: WorkerTaskContext) -> TaskResult:
            result, added_count = run_template_group_management(context.worker, context.page_size)
            return TaskResult(
                f"套版组管理：已提交。批量复制获取 {result.skc_count} 个，"
                f"搜索结果检测到 {added_count} 个。"
            )

        self.run_worker_task("套版组管理", task)

    def run_full_chain(self) -> None:
        def task(context: WorkerTaskContext) -> TaskResult:
            context.logger("开始执行批量一条龙操作。")
            results = run_full_chain_steps(
                context.worker,
                context.logger,
                context.page_size,
                should_stop=context.should_stop,
            )
            return summarize_step_results("一条龙操作", results)

        self.run_worker_task("批量一条龙操作", task)

    def upload_all_compliance_info(self) -> None:
        def task(context: WorkerTaskContext) -> TaskResult:
            results = run_compliance_upload_steps(
                context.worker,
                context.logger,
                context.page_size,
                should_stop=context.should_stop,
            )
            return summarize_step_results("批量上传合规信息", results)

        self.run_worker_task("批量上传合规信息", task)

    def open_single_compliance_dialog(self) -> None:
        dialog = SingleComplianceDialog(self)
        dialog.exec_()

    def upload_compliance_info(self) -> None:
        self.run_single_count_task(
            "批量上传加州65号提案",
            lambda context: context.worker.upload_california_65_compliance_info(target_page_size=context.page_size),
            "已确认上传",
        )

    def upload_manufacturer_attribute(self) -> None:
        self.run_single_count_task(
            "批量上传制造商属性",
            lambda context: context.worker.upload_manufacturer_attribute_compliance_info(target_page_size=context.page_size),
            "已确认上传",
        )

    def upload_production_shelf_life(self) -> None:
        self.run_single_count_task(
            "批量上传生产/保质期",
            lambda context: context.worker.upload_production_shelf_life_compliance_info(target_page_size=context.page_size),
            "已确认上传",
        )

    def upload_warning_safety_supplement(self) -> None:
        self.run_single_count_task(
            "批量上传警告或安全信息",
            lambda context: context.worker.upload_warning_safety_supplement_compliance_info(target_page_size=context.page_size),
            "已确认上传",
        )

    def upload_packaging_material(self) -> None:
        self.run_single_count_task(
            "批量上传包装材料信息",
            lambda context: context.worker.upload_packaging_material_compliance_info(target_page_size=context.page_size),
            "已确认上传",
        )

    def upload_turkey_responsible_person(self) -> None:
        self.run_single_count_task(
            "批量上传土耳其负责人",
            lambda context: context.worker.upload_turkey_responsible_person_compliance_info(target_page_size=context.page_size),
            "已确认上传",
        )

    def upload_manufacturer_info(self) -> None:
        self.run_single_count_task(
            "批量上传制造商信息",
            lambda context: context.worker.upload_manufacturer_info_compliance_info(target_page_size=context.page_size),
            "已确认上传",
        )

    def upload_eu_responsible_person(self) -> None:
        self.run_single_count_task(
            "批量上传欧盟负责人",
            lambda context: context.worker.upload_eu_responsible_person_compliance_info(target_page_size=context.page_size),
            "已确认上传",
        )

    def upload_product_identifier(self) -> None:
        def task(context: WorkerTaskContext) -> TaskResult:
            result = context.worker.upload_product_identifier_file(target_page_size=context.page_size)
            return TaskResult(
                f"批量上传商品识别码：已导入，SPU {result.spu_count} 个。文件：{result.upload_file}"
            )

        self.run_worker_task("批量上传商品识别码", task)

    def upload_compliant_live_photos(self) -> None:
        self.run_single_count_task(
            "批量上传商品合规图",
            lambda context: context.worker.upload_compliant_live_photos(submit=True),
            "已提交",
        )

    def batch_open_jit_management(self) -> None:
        self.run_single_count_task(
            "批量开通JIT管理",
            lambda context: context.worker.batch_open_jit_management(submit=True, target_page_size=context.page_size),
            "已确认开通",
        )

    def batch_set_expected_arrival_area(self) -> None:
        self.run_single_count_task(
            "批量设置期望到货区域",
            lambda context: context.worker.batch_set_expected_arrival_area(submit=True, target_page_size=context.page_size),
            "已确认设置为义乌",
        )

    def upload_inventory_setting(self) -> None:
        def task(context: WorkerTaskContext) -> TaskResult:
            result = context.worker.upload_inventory_setting_file(target_page_size=context.page_size)
            return TaskResult(f"批量导入库存设置：已上传并保存，SKU {result.sku_count} 个。文件：{result.upload_file}")

        self.run_worker_task("批量导入库存设置", task)

    def run_single_count_task(
        self,
        title: str,
        action: Callable[[WorkerTaskContext], int],
        done_text: str,
    ) -> None:
        def task(context: WorkerTaskContext) -> TaskResult:
            selected_count = action(context)
            return TaskResult(f"{title}：{done_text}，选中 {selected_count} 个商品。")

        self.run_worker_task(title, task)

    def log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.appendPlainText(f"[{timestamp}] {message}")

    def show_error(self, title: str, exc: Exception) -> None:
        self.log(f"{title}：{exc}")
        QMessageBox.critical(self, title, str(exc))

    def close_controlled_browser(self) -> None:
        self.refresh_worker()
        try:
            self.worker.close()
        except Exception as exc:  # noqa: BLE001 - close should be best-effort on exit.
            self.log(f"关闭浏览器连接时出现提示：{exc}")
        try:
            self.worker.session.close_remote_browser()
        except Exception as exc:  # noqa: BLE001 - no running browser is fine.
            self.log(f"未检测到可关闭的 Chrome 调试浏览器：{exc}")

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.current_thread and self.current_thread.isRunning():
            self.stop_current_task(show_message=False)
            self.current_thread.wait(3000)
            if self.current_thread.isRunning():
                self.current_thread.terminate()
                self.current_thread.wait(3000)
        super().closeEvent(event)


def create_apply_goods_widget(parent=None):
    return ApplyGoodsEmbeddedWidget(parent)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"ApplyGoods 商品申请自动化 {APP_VERSION}")
        self.resize(1080, 760)
        self.embedded_widget = create_apply_goods_widget(self)
        self.setCentralWidget(self.embedded_widget)

    def closeEvent(self, event) -> None:  # noqa: N802
        try:
            self.embedded_widget.close_controlled_browser()
        finally:
            super().closeEvent(event)


class SingleComplianceDialog(QDialog):
    def __init__(self, parent: MainWindow) -> None:
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("单项合规上传")
        self.setModal(True)
        self.resize(620, 280)

        root = QVBoxLayout(self)
        grid = QGridLayout()
        actions: list[tuple[str, Callable[[], None]]] = [
            ("批量上传加州65号提案", parent.upload_compliance_info),
            ("批量上传制造商属性", parent.upload_manufacturer_attribute),
            ("批量上传生产/保质期", parent.upload_production_shelf_life),
            ("批量上传警告或安全信息", parent.upload_warning_safety_supplement),
            ("批量上传包装材料信息", parent.upload_packaging_material),
            ("批量上传土耳其负责人", parent.upload_turkey_responsible_person),
            ("批量上传制造商信息", parent.upload_manufacturer_info),
            ("批量上传欧盟负责人", parent.upload_eu_responsible_person),
            ("批量上传商品识别码", parent.upload_product_identifier),
            ("批量上传商品合规图", parent.upload_compliant_live_photos),
        ]
        for index, (label, action) in enumerate(actions):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, selected_action=action: self.run_action(selected_action))
            grid.addWidget(button, index // 2, index % 2)
        root.addLayout(grid)

        close_buttons = QDialogButtonBox(QDialogButtonBox.Close)
        close_buttons.rejected.connect(self.reject)
        root.addWidget(close_buttons)

    def run_action(self, action: Callable[[], None]) -> None:
        self.accept()
        action()


def main() -> int:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
