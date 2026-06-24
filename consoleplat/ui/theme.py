APP_STYLE = """
QMainWindow {
    background: #eef3f9;
}
QWidget {
    color: #1b2733;
    font-family: "Microsoft YaHei UI";
    font-size: 13px;
}
QFrame#sidebar {
    background: #f8fbff;
    border-right: 1px solid #dfe8f3;
}
QPushButton#navButton {
    border: none;
    border-radius: 8px;
    color: #5e6b78;
    padding: 7px 4px;
    text-align: center;
}
QPushButton#navButton:hover {
    background: #eef6ff;
    color: #2f6fb4;
}
QPushButton#navButton:pressed {
    background: #dcecff;
}
QPushButton#navButton[active="true"] {
    background: #ffffff;
    color: #2f6fb4;
    border-left: 4px solid #5d96d8;
}
QLabel#appTitle {
    font-size: 13px;
    color: #142131;
}
QFrame#heroFrame {
    border-radius: 8px;
    background: #dce8f8;
}
QLabel#heroTitle {
    font-size: 34px;
    font-weight: 800;
    color: white;
}
QLabel#heroSubtitle {
    font-size: 18px;
    font-weight: 700;
    color: white;
}
QLabel#sectionTitle {
    font-size: 22px;
    font-weight: 700;
    color: #111d2c;
}
QFrame#taskCard {
    background: #ffffff;
    border: 1px solid #e3ebf4;
    border-radius: 8px;
}
QFrame#taskCard:hover {
    border-color: #b8d5f4;
    background: #fafdff;
}
QLabel#cardTitle {
    font-size: 15px;
    font-weight: 700;
    color: #172434;
}
QLabel#cardSubtitle {
    color: #6e7d8b;
    font-size: 12px;
}
QLabel#statusPill {
    border-radius: 8px;
    padding: 3px 8px;
    background: #eef5fc;
    color: #5f7390;
}
QLabel#applyPageEyebrow {
    color: #5d96d8;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1px;
}
QFrame#panel {
    background: #ffffff;
    border: 1px solid #e3ebf4;
    border-radius: 8px;
}
QFrame#applyHeaderPanel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffffff, stop:1 #f4f8fd);
    border: 1px solid #dce6f1;
    border-radius: 12px;
}
QFrame#applyEmbedPanel {
    background: #ffffff;
    border: 1px solid #dce6f1;
    border-radius: 12px;
}
QFrame#applyEmbedShell {
    background: #f8fbff;
    border: 1px solid #e4edf6;
    border-radius: 10px;
}
QLabel#applyStatusBanner {
    background: #eef5fc;
    border: 1px solid #d9e7f6;
    border-radius: 10px;
    color: #56708d;
    font-weight: 700;
    padding: 8px 12px;
}
QLabel#applyErrorLabel {
    background: #fff4f2;
    border: 1px solid #f3c8bf;
    border-radius: 10px;
    color: #a34b3d;
    padding: 10px 12px;
}
QFrame#metricCard {
    background: #ffffff;
    border: 1px solid #e3ebf4;
    border-radius: 8px;
}
QLabel#metricValue {
    font-size: 28px;
    font-weight: 800;
    color: #142131;
}
QLabel#metricTitle {
    font-size: 12px;
    color: #6d7d8d;
}
QLabel#panelTitle {
    font-size: 16px;
    font-weight: 800;
    color: #162538;
}
QLabel#monitorEmptyTitle {
    font-size: 18px;
    font-weight: 800;
    color: #142131;
    padding-top: 2px;
}
QLabel#monitorEmptyHint {
    color: #6e7d8b;
    font-size: 12px;
    padding-top: 2px;
}
QTableWidget {
    background: #ffffff;
    alternate-background-color: #f8fbff;
    border: 1px solid #e4edf6;
    border-radius: 6px;
    gridline-color: #edf3f8;
    selection-background-color: #dcecff;
    selection-color: #1b2733;
}
QHeaderView::section {
    background: #f1f6fb;
    color: #5f7080;
    border: none;
    border-right: 1px solid #e1eaf3;
    padding: 7px;
    font-weight: 700;
}
QSpinBox {
    background: #ffffff;
    border: 1px solid #d9e4ef;
    border-radius: 6px;
    padding: 7px 10px;
}
QListWidget#eventList {
    background: #f8fbff;
    border: 1px solid #e2ebf4;
    border-radius: 6px;
    padding: 6px;
}
QListWidget#eventList::item {
    padding: 7px;
    border-bottom: 1px solid #ecf2f8;
}
QScrollArea#monitorScroll {
    background: transparent;
}
QScrollArea#applyGoodsScroll {
    background: transparent;
}
QWidget#applyGoodsScrollContent {
    background: transparent;
}
QScrollBar:vertical {
    background: #e8f0f8;
    width: 10px;
    margin: 2px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #c5d4e4;
    min-height: 32px;
    border-radius: 5px;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}
QPushButton#primaryButton {
    background: #5d96d8;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 700;
}
QPushButton#primaryButton:hover {
    background: #70a5e3;
}
QPushButton#primaryButton:pressed {
    background: #457dbd;
}
QPushButton#primaryButton:disabled {
    background: #bcd3ed;
    color: #f8fbff;
}
QPushButton#ghostButton {
    background: #ffffff;
    color: #243142;
    border: 1px solid #d7e2ee;
    border-radius: 6px;
    padding: 8px 14px;
}
QPushButton#ghostButton:hover {
    background: #eef6ff;
    border-color: #b8d5f4;
    color: #2f6fb4;
}
QPushButton#ghostButton:pressed {
    background: #dcecff;
    border-color: #5d96d8;
}
QPushButton#ghostButton:disabled {
    background: #f5f8fb;
    color: #9ca8b4;
}
QPushButton#settingsTabButton {
    background: #ffffff;
    color: #4f6070;
    border: 1px solid #dce6f1;
    border-radius: 8px;
    padding: 9px 22px;
    font-weight: 700;
}
QPushButton#settingsTabButton:hover {
    background: #eef6ff;
    border-color: #b8d5f4;
    color: #2f6fb4;
}
QPushButton#settingsTabButton:pressed {
    background: #dcecff;
}
QPushButton#settingsTabButton[active="true"] {
    background: #5d96d8;
    border-color: #5d96d8;
    color: #ffffff;
}
"""
