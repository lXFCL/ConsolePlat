from __future__ import annotations

from PyQt5.QtCore import QPoint, QRect, Qt
from PyQt5.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from consoleplat.paths import resource_path
from consoleplat.ui.tutorial_data import TutorialStep


class TutorialOverlay(QWidget):
    def __init__(self, host: QWidget, steps: tuple[TutorialStep, ...]) -> None:
        super().__init__(host)
        self.host = host
        self.steps = steps
        self.current_index = 0
        self.highlight_rect = QRect()
        self.setObjectName("tutorialOverlay")
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setGeometry(host.rect())
        self.hide()

        self.card = QFrame(self)
        self.card.setObjectName("tutorialCard")
        self.card.setFixedWidth(360)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)

        self.title_label = QLabel()
        self.title_label.setObjectName("tutorialTitle")
        self.title_label.setWordWrap(True)
        self.body_label = QLabel()
        self.body_label.setObjectName("tutorialBody")
        self.body_label.setWordWrap(True)
        self.goal_label = QLabel()
        self.goal_label.setObjectName("tutorialDetail")
        self.goal_label.setWordWrap(True)
        self.actions_label = QLabel()
        self.actions_label.setObjectName("tutorialDetail")
        self.actions_label.setWordWrap(True)
        self.expected_label = QLabel()
        self.expected_label.setObjectName("tutorialDetail")
        self.expected_label.setWordWrap(True)
        self.tips_label = QLabel()
        self.tips_label.setObjectName("tutorialDetail")
        self.tips_label.setWordWrap(True)
        self.screenshot_label = QLabel()
        self.screenshot_label.setObjectName("tutorialScreenshot")
        self.screenshot_label.setAlignment(Qt.AlignCenter)
        self.screenshot_label.setMaximumHeight(120)
        self.safety_label = QLabel()
        self.safety_label.setObjectName("tutorialSafety")
        self.safety_label.setWordWrap(True)

        button_row = QHBoxLayout()
        self.finish_button = QPushButton("结束")
        self.finish_button.setObjectName("ghostButton")
        self.previous_button = QPushButton("上一步")
        self.previous_button.setObjectName("ghostButton")
        self.next_button = QPushButton("下一步")
        self.next_button.setObjectName("primaryButton")
        button_row.addWidget(self.finish_button)
        button_row.addStretch(1)
        button_row.addWidget(self.previous_button)
        button_row.addWidget(self.next_button)

        card_layout.addWidget(self.title_label)
        card_layout.addWidget(self.screenshot_label)
        card_layout.addWidget(self.body_label)
        card_layout.addWidget(self.goal_label)
        card_layout.addWidget(self.actions_label)
        card_layout.addWidget(self.expected_label)
        card_layout.addWidget(self.tips_label)
        card_layout.addWidget(self.safety_label)
        card_layout.addLayout(button_row)

        self.finish_button.clicked.connect(self.finish)
        self.previous_button.clicked.connect(self.previous_step)
        self.next_button.clicked.connect(self.next_step)

    def start(self) -> None:
        self.setGeometry(self.host.rect())
        self.show()
        self.raise_()
        self.show_step(0)

    def show_step(self, index: int) -> None:
        if not self.steps:
            self.current_index = 0
            self.highlight_rect = QRect()
            self.title_label.setText("暂无教程")
            self.body_label.setText("当前页面暂未配置教程。")
            self.screenshot_label.hide()
            self.goal_label.hide()
            self.actions_label.hide()
            self.expected_label.hide()
            self.tips_label.hide()
            self.safety_label.hide()
            self.previous_button.setEnabled(False)
            self.next_button.setEnabled(False)
            self._place_card()
            self.update()
            return

        self.current_index = max(0, min(index, len(self.steps) - 1))
        step = self.steps[self.current_index]
        self.highlight_rect = self._target_rect(step.target)
        self.title_label.setText(f"{self.current_index + 1}/{len(self.steps)} {step.title}")
        self.body_label.setText(step.body)
        self._set_detail_label(self.goal_label, "目的", step.goal)
        self._set_detail_label(self.actions_label, "怎么做", "\n".join(f"{index + 1}. {text}" for index, text in enumerate(step.actions)))
        self._set_detail_label(self.expected_label, "完成后看什么", step.expected)
        self._set_detail_label(self.tips_label, "提示", "\n".join(f"- {text}" for text in step.tips))
        self._set_screenshot(step.screenshot)
        self.safety_label.setText(step.safety_note)
        self.safety_label.setVisible(bool(step.safety_note))
        self.previous_button.setEnabled(self.current_index > 0)
        self.next_button.setEnabled(self.current_index < len(self.steps) - 1)
        self.next_button.setText("完成" if self.current_index == len(self.steps) - 1 else "下一步")
        self._place_card()
        self.update()

    def next_step(self) -> None:
        if not self.steps or self.current_index >= len(self.steps) - 1:
            self.finish()
            return
        self.show_step(self.current_index + 1)

    def previous_step(self) -> None:
        if not self.steps:
            return
        self.show_step(self.current_index - 1)

    def finish(self) -> None:
        self.hide()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self.isVisible():
            self.show_step(self.current_index)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(15, 23, 42, 135))
        if self.highlight_rect.isValid():
            painter.setBrush(QColor(255, 255, 255, 45))
            painter.setPen(QPen(QColor(93, 150, 216), 3))
            painter.drawRoundedRect(self.highlight_rect, 10, 10)
        super().paintEvent(event)

    def _target_rect(self, target_name: str) -> QRect:
        target = self.host.findChild(QWidget, target_name)
        if target is None or not target.isVisible():
            return QRect()
        top_left = target.mapTo(self.host, QPoint(0, 0))
        rect = QRect(top_left, target.size())
        return rect.adjusted(-8, -8, 8, 8).intersected(self.rect())

    def _set_screenshot(self, screenshot: str) -> None:
        if not screenshot:
            self.screenshot_label.hide()
            return
        path = resource_path(screenshot)
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.screenshot_label.hide()
            return
        self.screenshot_label.setPixmap(
            pixmap.scaled(320, 110, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        self.screenshot_label.show()

    def _set_detail_label(self, label: QLabel, heading: str, text: str) -> None:
        clean = str(text or "").strip()
        if not clean:
            label.setMinimumHeight(0)
            label.hide()
            return
        label.setText(f"{heading}：\n{clean}")
        label.show()

    def _place_card(self) -> None:
        self._sync_wrapped_label_heights()
        self.card.adjustSize()
        margin = 18
        card_size = self.card.sizeHint()
        if self.highlight_rect.isValid():
            x = self.highlight_rect.right() + margin
            y = self.highlight_rect.top()
            if x + card_size.width() > self.width() - margin:
                x = max(margin, self.highlight_rect.left() - card_size.width() - margin)
            if y + card_size.height() > self.height() - margin:
                y = max(margin, self.height() - card_size.height() - margin)
        else:
            x = max(margin, (self.width() - card_size.width()) // 2)
            y = max(margin, (self.height() - card_size.height()) // 2)
        self.card.setGeometry(x, y, card_size.width(), card_size.height())
        self._sync_wrapped_label_heights()
        self.card.adjustSize()
        card_size = self.card.sizeHint()
        if self.highlight_rect.isValid():
            if y + card_size.height() > self.height() - margin:
                y = max(margin, self.height() - card_size.height() - margin)
        else:
            y = max(margin, (self.height() - card_size.height()) // 2)
        self.card.setGeometry(x, y, card_size.width(), card_size.height())

    def _sync_wrapped_label_heights(self) -> None:
        layout = self.card.layout()
        margins = layout.contentsMargins() if layout is not None else None
        fallback_width = self.card.width()
        if margins is not None:
            fallback_width -= margins.left() + margins.right()
        for label in (self.goal_label, self.actions_label, self.expected_label, self.tips_label):
            if not label.isVisible():
                label.setMinimumHeight(0)
                continue
            width = label.width() if label.width() > 0 else max(1, fallback_width)
            required = label.heightForWidth(width)
            if required > 0:
                label.setMinimumHeight(required)
