from consoleplat import APP_VERSION


def test_app_version_uses_three_part_semver():
    assert APP_VERSION == "1.7.0"
