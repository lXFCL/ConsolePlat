from PyQt5 import QtCore, QtWidgets


class CleanupControlWindow(QtWidgets.QWidget):
    def __init__(self, get_cleanup_every, set_cleanup_every, trigger_manual_cleanup):
        super().__init__()
        self._get_cleanup_every = get_cleanup_every
        self._set_cleanup_every = set_cleanup_every
        self._trigger_manual_cleanup = trigger_manual_cleanup
        self.setWindowTitle("图片空间清理窗口")
        self.setWindowFlag(QtCore.Qt.Window, True)
        self.resize(420, 160)

        layout = QtWidgets.QVBoxLayout(self)

        row1 = QtWidgets.QHBoxLayout()
        row1.addWidget(QtWidgets.QLabel("每成功多少条后自动清理一次："))
        self.cleanup_every_input = QtWidgets.QSpinBox()
        self.cleanup_every_input.setRange(1, 1000)
        self.cleanup_every_input.setValue(int(self._get_cleanup_every() or 50))
        row1.addWidget(self.cleanup_every_input)
        self.apply_btn = QtWidgets.QPushButton("保存设置")
        row1.addWidget(self.apply_btn)
        layout.addLayout(row1)

        row2 = QtWidgets.QHBoxLayout()
        self.manual_cleanup_btn = QtWidgets.QPushButton("立即清理图片空间")
        row2.addWidget(self.manual_cleanup_btn)
        row2.addStretch(1)
        layout.addLayout(row2)

        self.status = QtWidgets.QLabel("")
        self.status.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(self.status)
        layout.addStretch(1)

        self.apply_btn.clicked.connect(self._apply)
        self.manual_cleanup_btn.clicked.connect(self._manual_cleanup)

    def _apply(self):
        value = int(self.cleanup_every_input.value())
        self._set_cleanup_every(value)
        self.status.setText(f"已设置：每成功{value}条自动清理一次")

    def _manual_cleanup(self):
        self._trigger_manual_cleanup()
        self.status.setText("已触发清理任务，请查看主窗口状态")
