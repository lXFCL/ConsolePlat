from __future__ import annotations

import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

from consoleplat.paths import resource_path
from consoleplat.ui.main_window import MainWindow


def run() -> int:
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(resource_path("assets/images/app_icon.ico"))))
    window = MainWindow()
    window.show()
    return app.exec_()
