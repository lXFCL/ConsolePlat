import json

import json

from consoleplat.config import AppSettings, ShopAccount, SettingsStore, encrypt_secret


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


def test_settings_store_persists_ordered_monitor_shops_and_shared_account(tmp_path):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    settings = AppSettings(
        active_shop="THIRD_SHOP",
        monitor_shops=["YUHOOBO", "YUHAOBO", "THIRD_SHOP"],
        monitor_account=ShopAccount(
            shop_name="THIRD_SHOP",
            phone="18800000000",
            password="shared-secret",
        ),
    )

    store.save(settings)
    raw = path.read_text(encoding="utf-8")
    loaded = store.load()

    assert loaded.monitor_shops == ["YUHOOBO", "YUHAOBO", "THIRD_SHOP"]
    assert loaded.active_shop == "THIRD_SHOP"
    assert loaded.monitor_account.phone == "18800000000"
    assert loaded.monitor_account.password == "shared-secret"
    assert "shared-secret" not in raw
    assert raw.count("password_dpapi") == 1


def test_settings_store_migrates_legacy_shop_accounts_to_shared_account(tmp_path):
    path = tmp_path / "settings.json"
    payload = {
        "active_shop": "YUHAOBO",
        "accounts": {
            "YUHOOBO": {
                "shop_name": "YUHOOBO",
                "phone": "first",
                "password_dpapi": encrypt_secret("first-pass"),
            },
            "YUHAOBO": {
                "shop_name": "YUHAOBO",
                "phone": "active",
                "password_dpapi": encrypt_secret("active-pass"),
            },
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = SettingsStore(path).load()

    assert loaded.monitor_shops == ["YUHOOBO", "YUHAOBO"]
    assert loaded.monitor_account.phone == "active"
    assert loaded.monitor_account.password == "active-pass"


def test_settings_store_persists_purchase_export_dir(tmp_path):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    settings = AppSettings(purchase_export_dir="E:/exports/purchase")

    store.save(settings)
    loaded = store.load()

    assert loaded.purchase_export_dir == "E:/exports/purchase"


def test_settings_store_persists_ai_selection_keywords(tmp_path):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    settings = AppSettings(ai_selection_keywords=["黑白T恤", "oversized tee"])

    store.save(settings)
    loaded = store.load()

    assert loaded.ai_selection_keywords == ["黑白T恤", "oversized tee"]


def test_settings_store_persists_print_gallery_preferences(tmp_path):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    settings = AppSettings(
        print_gallery_source="github",
        print_gallery_local_dir="E:/prints/cache",
        print_gallery_github_raw_base_url="https://raw.githubusercontent.com/demo/gallery/main",
    )

    store.save(settings)
    loaded = store.load()

    assert loaded.print_gallery_source == "github"
    assert loaded.print_gallery_local_dir == "E:/prints/cache"
    assert loaded.print_gallery_github_raw_base_url == "https://raw.githubusercontent.com/demo/gallery/main"


def test_settings_store_persists_startup_window_size(tmp_path):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    settings = AppSettings(startup_width=1280, startup_height=820)

    store.save(settings)
    loaded = store.load()

    assert loaded.startup_width == 1280
    assert loaded.startup_height == 820


def test_settings_store_persists_publish_handoff_preferences(tmp_path):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    settings = AppSettings(
        publish_handoff_delay_seconds=90,
        publish_pause_before_putaway=False,
    )

    store.save(settings)
    loaded = store.load()

    assert loaded.publish_handoff_delay_seconds == 90
    assert loaded.publish_pause_before_putaway is False


def test_settings_store_persists_theme_preferences(tmp_path):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    settings = AppSettings(theme_name="dark", bg_image_path="E:/images/bg.png")

    store.save(settings)
    loaded = store.load()

    assert loaded.theme_name == "dark"
    assert loaded.bg_image_path == "E:/images/bg.png"


def test_settings_store_persists_update_preferences(tmp_path):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    settings = AppSettings(
        check_update_on_startup=False,
        last_update_check="2026-06-25T12:00:00",
        skipped_update_version="1.5.0",
        update_download_dir="E:/downloads",
    )

    store.save(settings)
    loaded = store.load()

    assert loaded.check_update_on_startup is False
    assert loaded.last_update_check == "2026-06-25T12:00:00"
    assert loaded.skipped_update_version == "1.5.0"
    assert loaded.update_download_dir == "E:/downloads"
    assert loaded.update_proxy_enabled is True
    assert loaded.update_proxy_host == "127.0.0.1"
    assert loaded.update_proxy_port == 7890


def test_settings_store_persists_update_proxy_preferences(tmp_path):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    settings = AppSettings(
        update_proxy_enabled=False,
        update_proxy_host="127.0.0.2",
        update_proxy_port=10809,
    )

    store.save(settings)
    loaded = store.load()

    assert loaded.update_proxy_enabled is False
    assert loaded.update_proxy_host == "127.0.0.2"
    assert loaded.update_proxy_port == 10809


def test_settings_store_persists_posai_resource_download_preferences(tmp_path):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    settings = AppSettings(
        posai_comfyui_dir="E:/ConsolePlat/modules/PosAiImg/ComfyUI",
        posai_resource_download_dir="E:/ConsolePlat/runtime/downloads/posai",
        posai_comfyui_download_url="https://example.invalid/comfyui.zip",
        posai_models_download_url="https://example.invalid/models.zip",
    )

    store.save(settings)
    loaded = store.load()

    assert loaded.posai_comfyui_dir == "E:/ConsolePlat/modules/PosAiImg/ComfyUI"
    assert loaded.posai_resource_download_dir == "E:/ConsolePlat/runtime/downloads/posai"
    assert loaded.posai_comfyui_download_url == "https://example.invalid/comfyui.zip"
    assert loaded.posai_models_download_url == "https://example.invalid/models.zip"


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
