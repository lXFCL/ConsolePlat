from consoleplat.config import AppSettings, ShopAccount, SettingsStore


def test_settings_store_does_not_write_plain_password(tmp_path):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    settings = AppSettings(
        active_shop="YUHOOBO",
        accounts={
            "YUHOOBO": ShopAccount(
                shop_name="YUHOOBO",
                phone="18800000000",
                password="secret-password",
            )
        },
    )

    store.save(settings)
    raw = path.read_text(encoding="utf-8")
    loaded = store.load()

    assert "secret-password" not in raw
    assert loaded.accounts["YUHOOBO"].phone == "18800000000"
    assert loaded.accounts["YUHOOBO"].password == "secret-password"


def test_settings_store_persists_purchase_export_dir(tmp_path):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    settings = AppSettings(purchase_export_dir="E:/exports/purchase")

    store.save(settings)
    loaded = store.load()

    assert loaded.purchase_export_dir == "E:/exports/purchase"


def test_settings_store_persists_startup_window_size(tmp_path):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    settings = AppSettings(startup_width=1280, startup_height=820)

    store.save(settings)
    loaded = store.load()

    assert loaded.startup_width == 1280
    assert loaded.startup_height == 820

