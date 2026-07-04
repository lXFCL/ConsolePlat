from PyQt5.QtWidgets import QApplication, QWidget

from consoleplat.config import AppSettings
from consoleplat.models import DEFAULT_NAV_ITEMS
from consoleplat.paths import resource_path


class FakeSettingsStore:
    def load(self):
        return AppSettings(startup_width=1280, startup_height=820)


def test_each_nav_page_has_tutorial_steps():
    from consoleplat.ui.tutorial_data import TUTORIALS, get_tutorial_steps

    page_keys = {item.key for item in DEFAULT_NAV_ITEMS}

    assert set(TUTORIALS) == page_keys
    for key in page_keys:
        assert get_tutorial_steps(key), key


def test_tutorial_steps_have_required_text():
    from consoleplat.ui.tutorial_data import TUTORIALS, TutorialStep

    for page_key, steps in TUTORIALS.items():
        for step in steps:
            assert isinstance(step, TutorialStep)
            assert step.title.strip(), page_key
            assert step.body.strip(), page_key
            assert step.target.strip(), page_key
            assert step.goal.strip(), page_key
            assert step.actions, page_key
            assert step.expected.strip(), page_key


def test_unknown_page_returns_empty_steps():
    from consoleplat.ui.tutorial_data import get_tutorial_steps

    assert get_tutorial_steps("missing") == ()


def test_tutorial_screenshot_references_exist():
    from consoleplat.ui.tutorial_data import TUTORIALS

    for page_key, steps in TUTORIALS.items():
        for step in steps:
            if step.screenshot:
                assert resource_path(step.screenshot).exists(), f"{page_key}:{step.screenshot}"


def test_tutorial_explains_where_to_change_key_folders():
    from consoleplat.ui.tutorial_data import TUTORIALS

    all_text = "\n".join(
        "\n".join(
            (
                step.title,
                step.body,
                step.goal,
                step.expected,
                step.safety_note,
                *step.actions,
                *step.tips,
            )
        )
        for steps in TUTORIALS.values()
        for step in steps
    )

    required_phrases = [
        "设置 > 生图 / 改图",
        "图库目录",
        "产品图目录",
        "XLSX 目录",
        "设置 > 上架",
        "上架 data 目录",
        "设置 > 监控",
        "拿货表导出目录",
        "Chrome 调试地址",
    ]
    for phrase in required_phrases:
        assert phrase in all_text


def test_tutorial_targets_exist_on_loaded_pages(monkeypatch):
    from consoleplat.ui.main_window import MainWindow
    from consoleplat.ui.tutorial_data import TUTORIALS

    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    for page_key, steps in TUTORIALS.items():
        window.activate_page(page_key)
        page = window.pages[page_key]
        for step in steps:
            assert page.findChild(QWidget, step.target) is not None, f"{page_key}:{step.target}"

    window.close()
