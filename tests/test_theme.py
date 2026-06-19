from consoleplat.ui.theme import APP_STYLE


def test_primary_and_ghost_buttons_have_hover_feedback():
    assert "QPushButton#primaryButton:hover" in APP_STYLE
    assert "QPushButton#primaryButton:pressed" in APP_STYLE
    assert "QPushButton#ghostButton:hover" in APP_STYLE
    assert "QPushButton#ghostButton:pressed" in APP_STYLE


def test_settings_tab_buttons_have_hover_feedback():
    assert "QPushButton#settingsTabButton" in APP_STYLE
    assert "QPushButton#settingsTabButton:hover" in APP_STYLE
    assert 'QPushButton#settingsTabButton[active="true"]' in APP_STYLE
