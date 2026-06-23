from consoleplat.models import DEFAULT_NAV_ITEMS, DEFAULT_TASK_CARDS, ShellState
from consoleplat.paths import resource_path


def test_default_navigation_starts_on_monitor_page():
    state = ShellState()

    assert state.active_page == "monitor"
    assert [item.key for item in DEFAULT_NAV_ITEMS] == [
        "monitor",
        "publish",
        "local_image",
        "ai_edit",
        "putaway",
        "apply",
        "settings",
    ]


def test_publish_page_is_in_front_of_image_pages():
    assert [item.title for item in DEFAULT_NAV_ITEMS[:4]] == ["监控", "发布", "生图", "改图"]


def test_task_cards_cover_four_source_projects():
    project_keys = {card.project_key for card in DEFAULT_TASK_CARDS}

    assert {"sendgoods", "posaiimg", "putaway", "applygoods"}.issubset(project_keys)


def test_application_icon_assets_exist():
    assert resource_path("assets/images/app_icon.png").exists()
    assert resource_path("assets/images/app_icon.ico").exists()
