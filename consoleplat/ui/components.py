from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from consoleplat.models import TaskCard


class HeroBanner(QFrame):
    def __init__(self, image_path: str, parent: QWidget | None = None, background_y_offset: int = 0) -> None:
        super().__init__(parent)
        self.setObjectName("heroFrame")
        self.setMinimumHeight(320)
        self._pixmap = QPixmap(image_path)
        self.background_y_offset = background_y_offset

        layout = QVBoxLayout(self)
        layout.setContentsMargins(38, 34, 38, 34)
        layout.setSpacing(8)
        layout.addStretch(1)

        title = QLabel("ConsolePlat")
        title.setObjectName("heroTitle")
        subtitle = QLabel("跨店铺自动化工作台")
        subtitle.setObjectName("heroSubtitle")
        caption = QLabel("监控、出图、上架、申请，先把流程装进一个清楚的壳里。")
        caption.setStyleSheet("color: rgba(255, 255, 255, 0.92); font-size: 14px;")
        caption.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(caption)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        rect = self.rect()
        if not self._pixmap.isNull():
            scaled = self._pixmap.scaled(rect.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = (rect.width() - scaled.width()) // 2
            y = (rect.height() - scaled.height()) // 2 + self.background_y_offset
            painter.drawPixmap(x, y, scaled)
        painter.fillRect(rect, QColor(22, 31, 48, 78))
        super().paintEvent(event)


class TaskCardWidget(QFrame):
    def __init__(self, card: TaskCard, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("taskCard")
        self.setFixedHeight(142)
        self.setMinimumWidth(136)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        marker = QLabel()
        marker.setFixedSize(34, 34)
        marker.setStyleSheet(f"background: {card.accent}; border-radius: 17px;")

        title = QLabel(card.title)
        title.setObjectName("cardTitle")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel(card.subtitle)
        subtitle.setObjectName("cardSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)

        pill = QLabel(card.status)
        pill.setObjectName("statusPill")
        pill.setAlignment(Qt.AlignCenter)

        top = QHBoxLayout()
        top.addStretch(1)
        top.addWidget(marker)
        top.addStretch(1)

        layout.addLayout(top)
        layout.addWidget(title)
        layout.addWidget(subtitle, stretch=1)
        layout.addWidget(pill)


def make_page_panel(title: str, body: str) -> QFrame:
    panel = QFrame()
    panel.setObjectName("panel")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(22, 20, 22, 20)
    layout.setSpacing(12)

    heading = QLabel(title)
    heading.setObjectName("sectionTitle")
    text = QLabel(body)
    text.setWordWrap(True)
    text.setStyleSheet("color: #607081; line-height: 1.4;")

    primary = QPushButton("开始配置")
    primary.setObjectName("primaryButton")
    ghost = QPushButton("查看日志")
    ghost.setObjectName("ghostButton")
    row = QHBoxLayout()
    row.addWidget(primary)
    row.addWidget(ghost)
    row.addStretch(1)

    layout.addWidget(heading)
    layout.addWidget(text)
    layout.addLayout(row)
    return panel
