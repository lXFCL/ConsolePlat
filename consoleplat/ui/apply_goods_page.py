from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QLabel, QScrollArea, QVBoxLayout, QWidget

from consoleplat.adapters.applygoods_adapter import ApplyGoodsAdapter
from consoleplat.config import SettingsStore


class ApplyGoodsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = SettingsStore().load()
        self.adapter = ApplyGoodsAdapter(
            project_dir=Path(self.settings.applygoods_project_dir or r"E:\1PythonProject\ApplyGoods"),
        )
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.embedded_widget: QWidget | None = None

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setObjectName("applyGoodsScroll")
        outer.addWidget(self.scroll_area)

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("applyGoodsScrollContent")
        self.scroll_area.setWidget(self.scroll_content)

        root = QVBoxLayout(self.scroll_content)
        root.setContentsMargins(0, 8, 10, 18)
        root.setSpacing(16)

        header = QFrame()
        header.setObjectName("applyHeaderPanel")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(24, 22, 24, 22)
        header_layout.setSpacing(10)

        eyebrow = QLabel("合规工作台")
        eyebrow.setObjectName("applyPageEyebrow")
        title = QLabel("申请 / 合规")
        title.setObjectName("sectionTitle")
        hint = QLabel("当前页面直接内嵌 ApplyGoods 界面，已与控制台主题统一配色。可在此连接浏览器并执行套版组、合规上传、JIT 与库存等操作。")
        hint.setObjectName("cardSubtitle")
        hint.setWordWrap(True)

        header_layout.addWidget(eyebrow)
        header_layout.addWidget(title)
        header_layout.addWidget(hint)
        root.addWidget(header)

        self.container_panel = QFrame()
        self.container_panel.setObjectName("applyEmbedPanel")
        self.container_panel.setMinimumHeight(720)
        container_layout = QVBoxLayout(self.container_panel)
        container_layout.setContentsMargins(24, 20, 24, 24)
        container_layout.setSpacing(14)

        self.status_label = QLabel("正在加载内嵌合规界面…")
        self.status_label.setObjectName("applyStatusBanner")
        self.status_label.setWordWrap(True)
        container_layout.addWidget(self.status_label)

        self.error_label = QLabel("")
        self.error_label.setObjectName("applyErrorLabel")
        self.error_label.setWordWrap(True)
        self.error_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.error_label.hide()
        container_layout.addWidget(self.error_label)

        self.embed_shell = QFrame()
        self.embed_shell.setObjectName("applyEmbedShell")
        embed_layout = QVBoxLayout(self.embed_shell)
        embed_layout.setContentsMargins(18, 18, 18, 18)
        embed_layout.setSpacing(0)

        try:
            self.embedded_widget = self.adapter.build_embedded_widget(parent=self.embed_shell)
        except Exception as exc:
            self.embedded_widget = None
            self.status_label.setText("内嵌合规界面加载失败")
            self.error_label.setText(
                "无法加载 ApplyGoods 内嵌界面。\n"
                f"错误类型：{type(exc).__name__}\n"
                f"错误信息：{exc}"
            )
            self.error_label.show()
        else:
            self.status_label.setText("已加载 ApplyGoods 内嵌界面")
            embed_layout.addWidget(self.embedded_widget)

        container_layout.addWidget(self.embed_shell, stretch=1)
        root.addWidget(self.container_panel)
        root.addStretch(1)
