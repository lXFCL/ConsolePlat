from PyQt5.QtWidgets import QApplication, QLabel

from consoleplat.paths import resource_path
from consoleplat.ui.components import HeroBanner


def test_hero_banner_keeps_background_lower_for_character_face():
    app = QApplication.instance() or QApplication([])

    banner = HeroBanner(str(resource_path("assets/images/dashboard_hero.png")), background_y_offset=56)

    assert banner.background_y_offset == 56

    banner.close()


def test_hero_banner_can_hide_marketing_copy_for_dense_workspaces():
    app = QApplication.instance() or QApplication([])

    banner = HeroBanner(str(resource_path("assets/images/dashboard_hero.png")), show_copy=False)

    assert banner.show_copy is False
    assert not banner.findChildren(QLabel)

    banner.close()
