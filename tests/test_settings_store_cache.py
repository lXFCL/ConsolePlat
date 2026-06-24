import json
import os

from consoleplat import config
from consoleplat.config import AIProviderConfig, AppSettings, SettingsStore


def test_settings_store_load_uses_cache_when_file_is_unchanged(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "ai_providers": [
                    {
                        "provider_id": "provider-1",
                        "name": "provider one",
                        "api_key_dpapi": "encrypted-key-1",
                        "api_base": "https://one.example/v1",
                        "model": "model-one",
                        "size": "1024x1024",
                    }
                ],
                "default_ai_provider_id": "provider-1",
            }
        ),
        encoding="utf-8",
    )
    calls: list[str] = []

    def fake_decrypt(cipher_b64: str) -> str:
        calls.append(cipher_b64)
        return f"plain:{cipher_b64}"

    monkeypatch.setattr(config, "decrypt_secret", fake_decrypt)
    store = SettingsStore(path)

    first = store.load()
    first.ai_providers[0].api_key = "mutated-by-caller"
    second = store.load()

    assert calls == ["encrypted-key-1"]
    assert second.ai_providers[0].api_key == "plain:encrypted-key-1"
    assert second is not first


def test_settings_store_save_refreshes_cache_for_next_load(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    decrypt_calls: list[str] = []

    monkeypatch.setattr(config, "encrypt_secret", lambda value: f"encrypted:{value}")

    def fake_decrypt(cipher_b64: str) -> str:
        decrypt_calls.append(cipher_b64)
        return cipher_b64.removeprefix("encrypted:")

    monkeypatch.setattr(config, "decrypt_secret", fake_decrypt)
    store = SettingsStore(path)

    store.save(
        AppSettings(
            default_ai_provider_id="provider-1",
            ai_providers=[
                AIProviderConfig(
                    provider_id="provider-1",
                    name="provider one",
                    api_key="fresh-key",
                    api_base="https://fresh.example/v1",
                    model="fresh-model",
                    size="1536x1024",
                )
            ],
        )
    )
    loaded = store.load()

    assert decrypt_calls == []
    assert loaded.ai_providers[0].api_key == "fresh-key"
    assert loaded.ai_providers[0].api_base == "https://fresh.example/v1"


def test_settings_store_reloads_when_file_mtime_changes(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "ai_providers": [
                    {
                        "provider_id": "provider-1",
                        "name": "provider one",
                        "api_key_dpapi": "encrypted-key-1",
                    }
                ],
                "default_ai_provider_id": "provider-1",
            }
        ),
        encoding="utf-8",
    )
    decrypt_calls: list[str] = []

    def fake_decrypt(cipher_b64: str) -> str:
        decrypt_calls.append(cipher_b64)
        return f"plain:{cipher_b64}"

    monkeypatch.setattr(config, "decrypt_secret", fake_decrypt)
    store = SettingsStore(path)

    first = store.load()
    first_mtime = path.stat().st_mtime
    path.write_text(
        json.dumps(
            {
                "ai_providers": [
                    {
                        "provider_id": "provider-1",
                        "name": "provider one",
                        "api_key_dpapi": "encrypted-key-2",
                    }
                ],
                "default_ai_provider_id": "provider-1",
            }
        ),
        encoding="utf-8",
    )
    os.utime(path, (first_mtime + 10, first_mtime + 10))

    second = store.load()

    assert decrypt_calls == ["encrypted-key-1", "encrypted-key-2"]
    assert first.ai_providers[0].api_key == "plain:encrypted-key-1"
    assert second.ai_providers[0].api_key == "plain:encrypted-key-2"
