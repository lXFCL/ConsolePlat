APP_STYLE = """
QMainWindow {
    background: #eef3f9;
}
QWidget {
    color: #1b2733;
    font-family: "Microsoft YaHei UI";
    font-size: 13px;
}
QPushButton {
    background: #ffffff;
    color: #243142;
    border: 1px solid #d7e2ee;
    border-radius: 6px;
    padding: 7px 12px;
}
QPushButton:hover {
    background: #eef6ff;
    border-color: #b8d5f4;
    color: #2f6fb4;
}
QPushButton:pressed {
    background: #dcecff;
    border-color: #8bb7e8;
}
QPushButton:disabled {
    background: #f3f6f9;
    border-color: #e1e7ed;
    color: #98a4b0;
}
QFrame#sidebar {
    background: #f8fbff;
    border-right: 1px solid #dfe8f3;
}
QLabel#brandMark {
    color: #2f6fb4;
    background: #e8f2fd;
    border: 1px solid #cfe1f5;
    border-radius: 7px;
    font-size: 13px;
    font-weight: 800;
}
QPushButton#navButton {
    background: transparent;
    border: none;
    border-radius: 8px;
    color: #5e6b78;
    outline: none;
    padding: 7px 4px;
    text-align: center;
}
QPushButton#navButton:focus {
    border: none;
}
QLabel#navIcon,
QLabel#navTitle {
    color: #5e6b78;
}
QLabel#navTitle {
    font-size: 11px;
}
QLabel#navBadge {
    color: #18794e;
    font-size: 9px;
    font-weight: 700;
}
QFrame#workbenchHeader {
    background: rgba(255, 255, 255, 0.72);
    border: 1px solid #e1e9f2;
    border-radius: 8px;
}
QPushButton#navButton:hover {
    background: #eef6ff;
    color: #2f6fb4;
}
QPushButton#navButton:hover QLabel#navIcon,
QPushButton#navButton:hover QLabel#navTitle,
QPushButton#navButton[active=true] QLabel#navIcon,
QPushButton#navButton[active=true] QLabel#navTitle {
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
    font-size: 11px;
    color: #6e7d8b;
}
QLabel#pageTitle {
    font-size: 19px;
    font-weight: 800;
    color: #142131;
}
QLabel#pageDescription {
    font-size: 11px;
    color: #6e7d8b;
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
QLabel#statusPill[hasUpdate="true"] {
    background: #fff4e5;
    color: #b45309;
    border: 1px solid #fcd9a8;
    font-weight: 700;
}
QLabel#statusPill[running="true"] {
    background: #e8f7ef;
    color: #18794e;
    border: 1px solid #b7e3ca;
    font-weight: 700;
}
QLabel#applyPageEyebrow {
    color: #5d96d8;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1px;
}
QFrame#panel,
QFrame#subPanel,
QFrame#monitorControlsAnchor,
QFrame#monitorMetricsAnchor,
QFrame#monitorOrdersAnchor,
QFrame#publishHeaderAnchor,
QFrame#publishFormAnchor,
QFrame#publishActionsAnchor,
QFrame#localImageConfigAnchor,
QFrame#localImageStatusAnchor,
QFrame#aiEditQueueAnchor,
QFrame#aiEditImagesAnchor,
QFrame#aiEditRequestAnchor,
QFrame#putawayStatusAnchor,
QFrame#putawayEmbedAnchor,
QFrame#settingsBrowserAnchor {
    background: #ffffff;
    border: 1px solid #e3ebf4;
    border-radius: 8px;
}
QFrame#subPanel {
    background: #f8fbfe;
    border-color: #e5edf5;
}
QFrame#applyHeaderPanel,
QFrame#applySafetyAnchor {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffffff, stop:1 #f4f8fd);
    border: 1px solid #dce6f1;
    border-radius: 12px;
}
QFrame#applyEmbedPanel,
QFrame#applyEmbedAnchor {
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
QTableWidget::item {
    padding: 5px 7px;
}
QTableWidget::item:selected {
    background: #dcecff;
    color: #1b2733;
}
QHeaderView::section {
    background: #f1f6fb;
    color: #5f7080;
    border: none;
    border-right: 1px solid #e1eaf3;
    padding: 7px;
    font-weight: 700;
}
QLineEdit,
QComboBox,
QSpinBox,
QTextEdit,
QPlainTextEdit {
    background: #ffffff;
    border: 1px solid #d9e4ef;
    border-radius: 6px;
    padding: 7px 10px;
    selection-background-color: #dcecff;
    selection-color: #1b2733;
}
QLineEdit:hover,
QComboBox:hover,
QSpinBox:hover,
QTextEdit:hover,
QPlainTextEdit:hover {
    border-color: #b8cce2;
}
QLineEdit:disabled,
QComboBox:disabled,
QSpinBox:disabled,
QTextEdit:disabled,
QPlainTextEdit:disabled {
    background: #f3f6f9;
    color: #8b98a5;
    border-color: #e1e7ed;
}
QComboBox {
    padding-right: 28px;
}
QComboBox::drop-down {
    width: 26px;
    border: none;
    border-left: 1px solid #e2eaf2;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    color: #1b2733;
    border: 1px solid #cbd9e7;
    selection-background-color: #dcecff;
    selection-color: #1b2733;
    outline: 0;
}
QCheckBox {
    spacing: 8px;
    color: #354454;
}
QCheckBox:disabled {
    color: #98a4b0;
}
QProgressBar {
    min-height: 10px;
    max-height: 10px;
    background: #e7edf4;
    border: none;
    border-radius: 5px;
    color: transparent;
}
QProgressBar::chunk {
    background: #4b89c8;
    border-radius: 5px;
}
QListWidget {
    background: #ffffff;
    border: 1px solid #e2ebf4;
    border-radius: 6px;
    padding: 4px;
    outline: 0;
}
QListWidget::item {
    min-height: 26px;
    padding: 5px 7px;
    border-radius: 4px;
}
QListWidget::item:hover {
    background: #eef5fc;
}
QListWidget::item:selected {
    background: #dcecff;
    color: #1b2733;
}
QTextEdit#taskLog,
QPlainTextEdit#taskLog {
    background: #f7fafc;
    color: #425466;
    font-family: Consolas, "Microsoft YaHei UI";
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
QListWidget#eventList::item:hover {
    background: #eef5fc;
}
QListWidget#eventList::item:selected {
    background: #dcecff;
    color: #1b2733;
}
QScrollArea#monitorScroll {
    background: transparent;
}
QWidget#monitorScrollContent {
    background: transparent;
}
QScrollArea#settingsModuleScroll {
    background: transparent;
    border: none;
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
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
}
QScrollBar:horizontal {
    background: #e8f0f8;
    height: 10px;
    margin: 2px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #c5d4e4;
    min-width: 32px;
    border-radius: 5px;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0;
}
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: transparent;
}
QToolTip {
    background: #243142;
    color: #ffffff;
    border: 1px solid #36485b;
    padding: 5px 7px;
}
QMenu {
    background: #ffffff;
    color: #243142;
    border: 1px solid #d7e2ee;
    padding: 5px;
}
QMenu::item {
    padding: 7px 24px 7px 10px;
    border-radius: 4px;
}
QMenu::item:selected {
    background: #eef5fc;
    color: #2f6fb4;
}
QSplitter::handle {
    background: #e3ebf4;
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
QPushButton:focus,
QComboBox:focus,
QLineEdit:focus,
QSpinBox:focus,
QTextEdit:focus,
QPlainTextEdit:focus,
QListWidget:focus,
QTableWidget:focus {
    border: 1px solid #5d96d8;
}
QPushButton#checkUpdateButton {
    background: #5d96d8;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 700;
}
QPushButton#checkUpdateButton:hover {
    background: #70a5e3;
}
QPushButton#checkUpdateButton:pressed {
    background: #457dbd;
}
QPushButton#checkUpdateButton:disabled {
    background: #bcd3ed;
    color: #f8fbff;
}
QPushButton#ghostButton,
QPushButton#settingsPathsAnchor {
    background: #ffffff;
    color: #243142;
    border: 1px solid #d7e2ee;
    border-radius: 6px;
    padding: 8px 14px;
}
QPushButton#downloadUpdateButton,
QPushButton#skipVersionButton {
    background: #ffffff;
    color: #243142;
    border: 1px solid #d7e2ee;
    border-radius: 6px;
    padding: 8px 14px;
}
QPushButton#downloadUpdateButton:hover,
QPushButton#skipVersionButton:hover {
    background: #eef6ff;
    border-color: #b8d5f4;
    color: #2f6fb4;
}
QPushButton#downloadUpdateButton:pressed,
QPushButton#skipVersionButton:pressed {
    background: #dcecff;
    border-color: #5d96d8;
}
QPushButton#downloadUpdateButton:disabled,
QPushButton#skipVersionButton:disabled {
    background: #f5f8fb;
    color: #9ca8b4;
}
QPushButton#ghostButton:hover,
QPushButton#settingsPathsAnchor:hover {
    background: #eef6ff;
    border-color: #b8d5f4;
    color: #2f6fb4;
}
QPushButton#ghostButton:pressed,
QPushButton#settingsPathsAnchor:pressed {
    background: #dcecff;
    border-color: #5d96d8;
}
QPushButton#ghostButton:disabled,
QPushButton#settingsPathsAnchor:disabled {
    background: #f5f8fb;
    color: #9ca8b4;
}
QLabel#settingsSecurityAnchor {
    color: #6e7d8b;
    font-size: 12px;
}
QPushButton#tutorialButton {
    background: #ffffff;
    color: #2f6fb4;
    border: 1px solid #c8d8ea;
    border-radius: 15px;
    min-width: 30px;
    max-width: 30px;
    min-height: 30px;
    max-height: 30px;
    font-weight: 900;
}
QPushButton#tutorialButton:hover {
    background: #eef6ff;
    border-color: #9fc4ef;
}
QFrame#tutorialCard {
    background: #ffffff;
    border: 1px solid #cbd9ea;
    border-radius: 8px;
}
QLabel#tutorialTitle {
    color: #142131;
    font-size: 16px;
    font-weight: 800;
}
QLabel#tutorialBody {
    color: #5f7080;
    line-height: 1.4;
}
QLabel#tutorialDetail {
    background: #f8fbff;
    border: 1px solid #e2ebf4;
    border-radius: 6px;
    color: #425466;
    padding: 7px 9px;
    line-height: 1.35;
}
QLabel#tutorialScreenshot {
    background: #f4f8fd;
    border: 1px solid #e2ebf4;
    border-radius: 6px;
}
QLabel#tutorialSafety {
    background: #fff7ed;
    border: 1px solid #fed7aa;
    border-radius: 6px;
    color: #9a3412;
    padding: 7px 9px;
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

DARK_STYLE = """
QMainWindow {
    background: #1a1f2e;
}
QWidget {
    color: #d4dce8;
    font-family: "Microsoft YaHei UI";
    font-size: 13px;
}
QPushButton {
    background: #1e2538;
    color: #d4dce8;
    border: 1px solid #3a4460;
    border-radius: 6px;
    padding: 7px 12px;
}
QPushButton:hover {
    background: #243050;
    border-color: #4b628d;
    color: #dbe3ee;
}
QPushButton:pressed {
    background: #2e4070;
    border-color: #5d79aa;
}
QPushButton:disabled {
    background: #202638;
    border-color: #2c3347;
    color: #758196;
}
QFrame#sidebar {
    background: #141827;
    border-right: 1px solid #2c3347;
}
QLabel#brandMark {
    color: #9bc6f2;
    background: #202d43;
    border: 1px solid #344867;
    border-radius: 7px;
    font-size: 13px;
    font-weight: 800;
}
QPushButton#navButton {
    background: transparent;
    border: none;
    border-radius: 8px;
    color: #8fa0b8;
    outline: none;
    padding: 7px 4px;
    text-align: center;
}
QPushButton#navButton:focus {
    border: none;
}
QLabel#navIcon,
QLabel#navTitle {
    color: #8fa0b8;
}
QLabel#navTitle {
    font-size: 11px;
}
QLabel#navBadge {
    color: #9de0bd;
    font-size: 9px;
    font-weight: 700;
}
QFrame#workbenchHeader {
    background: #1e2538;
    border: 1px solid #2c354b;
    border-radius: 8px;
}
QPushButton#navButton:hover {
    background: #1f2740;
    color: #9cb9df;
}
QPushButton#navButton:hover QLabel#navIcon,
QPushButton#navButton:hover QLabel#navTitle,
QPushButton#navButton[active=true] QLabel#navIcon,
QPushButton#navButton[active=true] QLabel#navTitle {
    color: #9cb9df;
}
QPushButton#navButton:pressed {
    background: #243050;
}
QPushButton#navButton[active="true"] {
    background: #243050;
    color: #7eb7f0;
    border-left: 4px solid #5d96d8;
}
QLabel#appTitle {
    font-size: 11px;
    color: #9eacbf;
}
QLabel#pageTitle {
    font-size: 19px;
    font-weight: 800;
    color: #edf2f8;
}
QLabel#pageDescription {
    font-size: 11px;
    color: #9eacbf;
}
QFrame#heroFrame {
    border-radius: 8px;
    background: #24304a;
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
    color: #f2f5fb;
}
QFrame#taskCard {
    background: #1e2538;
    border: 1px solid #2c3347;
    border-radius: 8px;
}
QFrame#taskCard:hover {
    border-color: #4b628d;
    background: #222a3f;
}
QLabel#cardTitle {
    font-size: 15px;
    font-weight: 700;
    color: #edf2f8;
}
QLabel#cardSubtitle {
    color: #9eacbf;
    font-size: 12px;
}
QLabel#statusPill {
    border-radius: 8px;
    padding: 3px 8px;
    background: #24304a;
    color: #9cb9df;
}
QLabel#statusPill[hasUpdate="true"] {
    background: #3a2e1a;
    color: #f5c97a;
    border: 1px solid #6b5226;
    font-weight: 700;
}
QLabel#statusPill[running="true"] {
    background: #193a2d;
    color: #9de0bd;
    border: 1px solid #2d6a4f;
    font-weight: 700;
}
QLabel#applyPageEyebrow {
    color: #7eb7f0;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1px;
}
QFrame#panel,
QFrame#subPanel,
QFrame#monitorControlsAnchor,
QFrame#monitorMetricsAnchor,
QFrame#monitorOrdersAnchor,
QFrame#publishHeaderAnchor,
QFrame#publishFormAnchor,
QFrame#publishActionsAnchor,
QFrame#localImageConfigAnchor,
QFrame#localImageStatusAnchor,
QFrame#aiEditQueueAnchor,
QFrame#aiEditImagesAnchor,
QFrame#aiEditRequestAnchor,
QFrame#putawayStatusAnchor,
QFrame#putawayEmbedAnchor,
QFrame#settingsBrowserAnchor {
    background: #1e2538;
    border: 1px solid #2c3347;
    border-radius: 8px;
}
QFrame#subPanel {
    background: #191f30;
    border-color: #2a3245;
}
QFrame#applyHeaderPanel,
QFrame#applySafetyAnchor {
    background: #1e2538;
    border: 1px solid #2c3347;
    border-radius: 12px;
}
QFrame#applyEmbedPanel,
QFrame#applyEmbedAnchor {
    background: #1e2538;
    border: 1px solid #2c3347;
    border-radius: 12px;
}
QFrame#applyEmbedShell {
    background: #171c2a;
    border: 1px solid #2c3347;
    border-radius: 10px;
}
QLabel#applyStatusBanner {
    background: #24304a;
    border: 1px solid #33415f;
    border-radius: 10px;
    color: #c0cde0;
    font-weight: 700;
    padding: 8px 12px;
}
QLabel#applyErrorLabel {
    background: #40252a;
    border: 1px solid #7d4451;
    border-radius: 10px;
    color: #f1b8c0;
    padding: 10px 12px;
}
QFrame#metricCard {
    background: #1e2538;
    border: 1px solid #2c3347;
    border-radius: 8px;
}
QLabel#metricValue {
    font-size: 28px;
    font-weight: 800;
    color: #f2f5fb;
}
QLabel#metricTitle {
    font-size: 12px;
    color: #9eacbf;
}
QLabel#panelTitle {
    font-size: 16px;
    font-weight: 800;
    color: #f2f5fb;
}
QLabel#monitorEmptyTitle {
    font-size: 18px;
    font-weight: 800;
    color: #f2f5fb;
    padding-top: 2px;
}
QLabel#monitorEmptyHint {
    color: #9eacbf;
    font-size: 12px;
    padding-top: 2px;
}
QTableWidget {
    background: #1e2538;
    alternate-background-color: #222a3f;
    border: 1px solid #2c3347;
    border-radius: 6px;
    gridline-color: #2c3347;
    selection-background-color: #2e4070;
    selection-color: #d4dce8;
}
QTableWidget::item {
    padding: 5px 7px;
}
QTableWidget::item:selected {
    background: #2e4070;
    color: #e4eaf2;
}
QHeaderView::section {
    background: #242a3d;
    color: #c0cde0;
    border: none;
    border-right: 1px solid #2c3347;
    padding: 7px;
    font-weight: 700;
}
QLineEdit,
QComboBox,
QSpinBox,
QTextEdit,
QPlainTextEdit {
    background: #242a3d;
    border: 1px solid #3a4460;
    border-radius: 6px;
    padding: 7px 10px;
    selection-background-color: #2e4070;
    selection-color: #edf2f8;
}
QLineEdit:hover,
QComboBox:hover,
QSpinBox:hover,
QTextEdit:hover,
QPlainTextEdit:hover {
    border-color: #536481;
}
QLineEdit:disabled,
QComboBox:disabled,
QSpinBox:disabled,
QTextEdit:disabled,
QPlainTextEdit:disabled {
    background: #1d2333;
    color: #758196;
    border-color: #2c3347;
}
QComboBox {
    padding-right: 28px;
}
QComboBox::drop-down {
    width: 26px;
    border: none;
    border-left: 1px solid #3a4460;
}
QComboBox QAbstractItemView {
    background: #242a3d;
    color: #d4dce8;
    border: 1px solid #46516d;
    selection-background-color: #2e4070;
    selection-color: #edf2f8;
    outline: 0;
}
QCheckBox {
    spacing: 8px;
    color: #c6d0de;
}
QCheckBox:disabled {
    color: #758196;
}
QProgressBar {
    min-height: 10px;
    max-height: 10px;
    background: #2b3347;
    border: none;
    border-radius: 5px;
    color: transparent;
}
QProgressBar::chunk {
    background: #4f83b8;
    border-radius: 5px;
}
QListWidget {
    background: #1e2538;
    border: 1px solid #2c3347;
    border-radius: 6px;
    padding: 4px;
    outline: 0;
}
QListWidget::item {
    min-height: 26px;
    padding: 5px 7px;
    border-radius: 4px;
}
QListWidget::item:hover {
    background: #243050;
}
QListWidget::item:selected {
    background: #2e4070;
    color: #edf2f8;
}
QTextEdit#taskLog,
QPlainTextEdit#taskLog {
    background: #171c2a;
    color: #b9c6d8;
    font-family: Consolas, "Microsoft YaHei UI";
}
QListWidget#eventList {
    background: #1e2538;
    border: 1px solid #2c3347;
    border-radius: 6px;
    padding: 6px;
}
QListWidget#eventList::item {
    padding: 7px;
    border-bottom: 1px solid #2c3347;
}
QListWidget#eventList::item:hover {
    background: #243050;
}
QListWidget#eventList::item:selected {
    background: #2e4070;
    color: #d4dce8;
}
QScrollArea#monitorScroll {
    background: transparent;
}
QWidget#monitorScrollContent {
    background: #1a1f2e;
}
QScrollArea#settingsModuleScroll {
    background: transparent;
    border: none;
}
QScrollArea#applyGoodsScroll {
    background: transparent;
}
QWidget#applyGoodsScrollContent {
    background: transparent;
}
QScrollBar:vertical {
    background: #2c3347;
    width: 10px;
    margin: 2px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #3a4a6a;
    min-height: 32px;
    border-radius: 5px;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
}
QScrollBar:horizontal {
    background: #2c3347;
    height: 10px;
    margin: 2px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #3a4a6a;
    min-width: 32px;
    border-radius: 5px;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0;
}
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: transparent;
}
QToolTip {
    background: #edf2f8;
    color: #1a1f2e;
    border: 1px solid #c4cfdd;
    padding: 5px 7px;
}
QMenu {
    background: #1e2538;
    color: #d4dce8;
    border: 1px solid #3a4460;
    padding: 5px;
}
QMenu::item {
    padding: 7px 24px 7px 10px;
    border-radius: 4px;
}
QMenu::item:selected {
    background: #243050;
    color: #dbe3ee;
}
QSplitter::handle {
    background: #2c3347;
}
QPushButton#primaryButton {
    background: #3a6fa8;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 700;
}
QPushButton#primaryButton:hover {
    background: #4a82c0;
}
QPushButton#primaryButton:pressed {
    background: #457dbd;
}
QPushButton#primaryButton:disabled {
    background: #2d3f5d;
    color: #a8b7ca;
}
QPushButton:focus,
QComboBox:focus,
QLineEdit:focus,
QSpinBox:focus,
QTextEdit:focus,
QPlainTextEdit:focus,
QListWidget:focus,
QTableWidget:focus {
    border: 1px solid #5d96d8;
}
QPushButton#checkUpdateButton {
    background: #3a6fa8;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 700;
}
QPushButton#checkUpdateButton:hover {
    background: #4a82c0;
}
QPushButton#checkUpdateButton:pressed {
    background: #457dbd;
}
QPushButton#checkUpdateButton:disabled {
    background: #2d3f5d;
    color: #a8b7ca;
}
QPushButton#ghostButton,
QPushButton#settingsPathsAnchor {
    background: #1e2538;
    color: #d4dce8;
    border: 1px solid #3a4460;
    border-radius: 6px;
    padding: 8px 14px;
}
QPushButton#downloadUpdateButton,
QPushButton#skipVersionButton {
    background: #1e2538;
    color: #d4dce8;
    border: 1px solid #3a4460;
    border-radius: 6px;
    padding: 8px 14px;
}
QPushButton#downloadUpdateButton:hover,
QPushButton#skipVersionButton:hover {
    background: #1f2740;
    border-color: #4b628d;
    color: #dbe3ee;
}
QPushButton#downloadUpdateButton:pressed,
QPushButton#skipVersionButton:pressed {
    background: #243050;
    border-color: #5d96d8;
}
QPushButton#downloadUpdateButton:disabled,
QPushButton#skipVersionButton:disabled {
    background: #20273a;
    color: #7a879a;
}
QPushButton#ghostButton:hover,
QPushButton#settingsPathsAnchor:hover {
    background: #1f2740;
    border-color: #4b628d;
    color: #dbe3ee;
}
QPushButton#ghostButton:pressed,
QPushButton#settingsPathsAnchor:pressed {
    background: #243050;
    border-color: #5d96d8;
}
QPushButton#ghostButton:disabled,
QPushButton#settingsPathsAnchor:disabled {
    background: #20273a;
    color: #7a879a;
}
QLabel#settingsSecurityAnchor {
    color: #9eacbf;
    font-size: 12px;
}
QPushButton#tutorialButton {
    background: #1e2538;
    color: #7eb7f0;
    border: 1px solid #3a4460;
    border-radius: 15px;
    min-width: 30px;
    max-width: 30px;
    min-height: 30px;
    max-height: 30px;
    font-weight: 900;
}
QPushButton#tutorialButton:hover {
    background: #243050;
    border-color: #4b628d;
}
QFrame#tutorialCard {
    background: #1e2538;
    border: 1px solid #3a4460;
    border-radius: 8px;
}
QLabel#tutorialTitle {
    color: #edf2f8;
    font-size: 16px;
    font-weight: 800;
}
QLabel#tutorialBody {
    color: #c0cde0;
    line-height: 1.4;
}
QLabel#tutorialDetail {
    background: #171c2a;
    border: 1px solid #2c3347;
    border-radius: 6px;
    color: #c0cde0;
    padding: 7px 9px;
    line-height: 1.35;
}
QLabel#tutorialScreenshot {
    background: #171c2a;
    border: 1px solid #2c3347;
    border-radius: 6px;
}
QLabel#tutorialSafety {
    background: #3a2e1a;
    border: 1px solid #6b5226;
    border-radius: 6px;
    color: #f5c97a;
    padding: 7px 9px;
}
QPushButton#settingsTabButton {
    background: #1e2538;
    color: #9eacbf;
    border: 1px solid #2c3347;
    border-radius: 8px;
    padding: 9px 22px;
    font-weight: 700;
}
QPushButton#settingsTabButton:hover {
    background: #243050;
    border-color: #4b628d;
    color: #dbe3ee;
}
QPushButton#settingsTabButton:pressed {
    background: #2e4070;
}
QPushButton#settingsTabButton[active="true"] {
    background: #3a6fa8;
    border-color: #3a6fa8;
    color: #ffffff;
}
"""


def get_app_style(theme_name: str = "light", bg_image_path: str = "") -> str:
    base = DARK_STYLE if theme_name == "dark" else APP_STYLE
    if not bg_image_path:
        return base
    escaped = bg_image_path.replace("\\", "/")
    return base + (
        f'\nQMainWindow {{ background-image: url("{escaped}"); '
        'background-repeat: no-repeat; background-position: center; }}\n'
    )
