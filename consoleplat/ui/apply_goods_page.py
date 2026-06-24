from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

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
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)
        self.embedded_widget: QWidget | None = None

        header = QFrame()
        header.setObjectName("panel")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 18, 22, 18)
        header_layout.setSpacing(8)

        title = QLabel("申请 / 合规")
        title.setObjectName("sectionTitle")
        hint = QLabel("当前页面直接内嵌 ApplyGoods 界面；套版组、合规上传、JIT、库存等会改变真实店铺状态，请谨慎操作。")
        hint.setObjectName("cardSubtitle")
        hint.setWordWrap(True)

        header_layout.addWidget(title)
        header_layout.addWidget(hint)
        root.addWidget(header)

        self.container_panel = QFrame()
        self.container_panel.setObjectName("panel")
        container_layout = QVBoxLayout(self.container_panel)
        container_layout.setContentsMargins(22, 18, 22, 18)
        container_layout.setSpacing(12)

        self.status_label = QLabel("正在加载内嵌合规界面…")
        self.status_label.setObjectName("statusPill")
        container_layout.addWidget(self.status_label)

        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.error_label.hide()
        container_layout.addWidget(self.error_label)

        try:
            self.embedded_widget = self.adapter.build_embedded_widget(parent=self.container_panel)
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
            container_layout.addWidget(self.embedded_widget, stretch=1)

        root.addWidget(self.container_panel, stretch=1)
