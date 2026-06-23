import json

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


def test_settings_store_migrates_legacy_ai_provider_fields(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "ai_edit_api_key_dpapi": "",
                "ai_edit_api_base": "https://legacy.example/v1",
                "ai_edit_model": "legacy-model",
                "ai_edit_size": "1536x1024",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    loaded = SettingsStore(path).load()

    assert loaded.default_ai_provider_id
    assert len(loaded.ai_providers) == 1
    provider = loaded.ai_providers[0]
    assert provider.provider_id == loaded.default_ai_provider_id
    assert provider.name
    assert provider.api_base == "https://legacy.example/v1"
    assert provider.model == "legacy-model"
    assert provider.size == "1536x1024"


def test_settings_store_persists_multiple_ai_providers(tmp_path):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    settings = AppSettings(
        default_ai_provider_id="provider-2",
        ai_providers=[
            {
                "provider_id": "provider-1",
                "name": "主接口",
                "api_key": "key-1",
                "api_base": "https://one.example/v1",
                "model": "gpt-image-a",
                "size": "1024x1024",
            },
            {
                "provider_id": "provider-2",
                "name": "备用接口",
                "api_key": "key-2",
                "api_base": "https://two.example/v1",
                "model": "gpt-image-b",
                "size": "1536x1024",
            },
        ],
    )

    store.save(settings)
    raw = path.read_text(encoding="utf-8")
    loaded = store.load()

    assert "key-1" not in raw
    assert "key-2" not in raw
    assert loaded.default_ai_provider_id == "provider-2"
    assert [provider.name for provider in loaded.ai_providers] == ["主接口", "备用接口"]
    assert loaded.ai_providers[1].api_key == "key-2"
