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


def test_theme_uses_blue_accent_instead_of_pink():
    assert "#fb78b7" not in APP_STYLE
    assert "#ffabd0" not in APP_STYLE
    assert "#eef6ff" in APP_STYLE
