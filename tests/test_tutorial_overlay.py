from PyQt5.QtWidgets import QApplication, QLabel, QWidget

from consoleplat.ui.tutorial_data import TutorialStep
from consoleplat.ui.tutorial_overlay import TutorialOverlay
from consoleplat.ui.theme import get_app_style


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


def test_tutorial_overlay_detail_labels_are_tall_enough_for_wrapped_text():
    app = QApplication.instance() or QApplication([])
    parent = QWidget()
    parent.resize(1280, 820)
    parent.setStyleSheet(get_app_style())
    parent.show()
    overlay = TutorialOverlay(
        parent,
        (
            TutorialStep(
                "missing",
                "外观、更新与敏感信息",
                "设置页还包含程序外观、更新检查和敏感信息相关配置。",
                goal="区分普通偏好设置和可能泄露账号状态的配置。",
                actions=(
                    "外观 Tab 维护主题和背景图。",
                    "更新 Tab 维护版本检查和代理。",
                    "账号、Cookie、Token、API Key、浏览器 profile 不应进入 Git、日志或教程截图。",
                ),
                expected="普通配置可保存，敏感信息不会出现在提交记录或截图材料中。",
                tips=("如果临时写入配置文件，先确认 `.gitignore` 覆盖。",),
            ),
        ),
    )

    overlay.start()
    app.processEvents()

    for label in (overlay.goal_label, overlay.actions_label, overlay.expected_label, overlay.tips_label):
        assert label.height() >= label.heightForWidth(label.width()), label.text()
