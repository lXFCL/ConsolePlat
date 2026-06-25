from consoleplat.ui.theme import APP_STYLE, DARK_STYLE, get_app_style


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


def test_theme_factory_switches_between_light_and_dark_and_background_image():
    dark_style = get_app_style("dark", r"C:\tmp\bg image.png")

    assert DARK_STYLE in dark_style
    assert 'background-image: url("C:/tmp/bg image.png")' in dark_style
    assert get_app_style("light", "") == APP_STYLE


def test_theme_has_update_status_pill_styles_for_light_and_dark():
    assert 'QLabel#statusPill[hasUpdate="true"]' in APP_STYLE
    assert 'QLabel#statusPill[hasUpdate="true"]' in DARK_STYLE
