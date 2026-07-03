from PyQt5.QtWidgets import QApplication, QLabel, QWidget

from consoleplat.ui.tutorial_data import TutorialStep
from consoleplat.ui.tutorial_overlay import TutorialOverlay


def test_tutorial_overlay_shows_first_step():
    app = QApplication.instance() or QApplication([])
    parent = QWidget()
    parent.resize(640, 420)
    parent.show()
    target = QLabel("target", parent)
    target.setObjectName("targetAnchor")
    target.setGeometry(40, 50, 160, 60)
    target.show()
    overlay = TutorialOverlay(
        parent,
        (TutorialStep("targetAnchor", "第一步", "说明文字"), TutorialStep("missing", "第二步", "后续说明")),
    )

    overlay.start()

    assert overlay.isVisible()
    assert overlay.title_label.text() == "1/2 第一步"
    assert overlay.body_label.text() == "说明文字"
    assert overlay.highlight_rect.isValid()


def test_tutorial_overlay_navigation_and_finish():
    app = QApplication.instance() or QApplication([])
    parent = QWidget()
    parent.resize(640, 420)
    parent.show()
    overlay = TutorialOverlay(
        parent,
        (TutorialStep("missing", "第一步", "说明"), TutorialStep("missing", "第二步", "更多")),
    )

    overlay.start()
    overlay.next_step()
    assert overlay.title_label.text() == "2/2 第二步"

    overlay.previous_step()
    assert overlay.title_label.text() == "1/2 第一步"

    overlay.finish()
    assert overlay.isHidden()


def test_tutorial_overlay_shows_empty_message_without_steps():
    app = QApplication.instance() or QApplication([])
    parent = QWidget()
    parent.resize(640, 420)
    parent.show()
    overlay = TutorialOverlay(parent, ())

    overlay.start()

    assert overlay.isVisible()
    assert overlay.title_label.text() == "暂无教程"
    assert "暂未配置教程" in overlay.body_label.text()
