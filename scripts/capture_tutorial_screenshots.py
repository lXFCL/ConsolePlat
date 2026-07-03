from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt5.QtWidgets import QApplication, QLabel  # noqa: E402

from consoleplat.config import AppSettings  # noqa: E402
from consoleplat.models import DEFAULT_NAV_ITEMS  # noqa: E402


class TutorialScreenshotSettingsStore:
    def load(self) -> AppSettings:
        return AppSettings(
            startup_width=1280,
            startup_height=820,
            check_update_on_startup=False,
            active_shop="YUHOOBO",
            refresh_interval_seconds=5,
        )

    def save(self, settings: AppSettings) -> None:
        return None


def _patch_settings_store() -> None:
    import consoleplat.ui.ai_edit_page as ai_edit_page
    import consoleplat.ui.apply_goods_page as apply_goods_page
    import consoleplat.ui.local_image_page as local_image_page
    import consoleplat.ui.main_window as main_window
    import consoleplat.ui.monitor_page as monitor_page
    import consoleplat.ui.product_publish_page as product_publish_page
    import consoleplat.ui.putaway_page as putaway_page
    import consoleplat.ui.settings_page as settings_page

    factory = lambda: TutorialScreenshotSettingsStore()
    for module in (
        ai_edit_page,
        apply_goods_page,
        local_image_page,
        main_window,
        monitor_page,
        product_publish_page,
        putaway_page,
        settings_page,
    ):
        module.SettingsStore = factory


def _patch_embedded_widgets() -> None:
    import consoleplat.ui.apply_goods_page as apply_goods_page
    import consoleplat.ui.putaway_page as putaway_page

    def build_putaway_placeholder(self, parent=None):
        label = QLabel("PutawayAiRobot 内嵌界面占位截图", parent)
        label.setMinimumHeight(420)
        label.setObjectName("tutorialEmbeddedPlaceholder")
        return label

    def build_apply_placeholder(self, parent=None):
        label = QLabel("ApplyGoods 内嵌界面占位截图", parent)
        label.setMinimumHeight(520)
        label.setObjectName("tutorialEmbeddedPlaceholder")
        return label

    putaway_page.PutawayAdapter.build_embedded_widget = build_putaway_placeholder
    apply_goods_page.ApplyGoodsAdapter.build_embedded_widget = build_apply_placeholder


def main() -> int:
    _patch_settings_store()
    _patch_embedded_widgets()

    from consoleplat.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.resize(1280, 820)
    window.show()

    output_dir = Path("assets/images/tutorial")
    output_dir.mkdir(parents=True, exist_ok=True)

    for item in DEFAULT_NAV_ITEMS:
        window.activate_page(item.key)
        app.processEvents()
        pixmap = window.grab()
        pixmap.save(str(output_dir / f"{item.key}.png"), "PNG")

    window.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
