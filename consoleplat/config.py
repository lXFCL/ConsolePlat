from __future__ import annotations

import base64
import ctypes
import json
import os
from ctypes import wintypes
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_AI_EDIT_PROMPT = "保留主体，整理成适合印花的透明底效果。"
DEFAULT_AI_PROVIDER_ID = "default-ai-provider"


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob_from_bytes(data: bytes) -> DATA_BLOB:
    buf = ctypes.create_string_buffer(data)
    return DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))


def _bytes_from_blob(blob: DATA_BLOB) -> bytes:
    if not blob.cbData:
        return b""
    return ctypes.string_at(blob.pbData, blob.cbData)


def encrypt_secret(plaintext: str) -> str:
    raw = (plaintext or "").encode("utf-8")
    if not raw:
        return ""
    in_blob = _blob_from_bytes(raw)
    out_blob = DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(in_blob), None, None, None, None, 0x1, ctypes.byref(out_blob)
    )
    if not ok:
        raise RuntimeError("无法加密配置密码")
    try:
        return base64.b64encode(_bytes_from_blob(out_blob)).decode("ascii")
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def decrypt_secret(cipher_b64: str) -> str:
    cipher_b64 = (cipher_b64 or "").strip()
    if not cipher_b64:
        return ""
    enc = base64.b64decode(cipher_b64)
    in_blob = _blob_from_bytes(enc)
    out_blob = DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(in_blob), None, None, None, None, 0x1, ctypes.byref(out_blob)
    )
    if not ok:
        return ""
    try:
        return _bytes_from_blob(out_blob).decode("utf-8", errors="ignore")
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


@dataclass
class ShopAccount:
    shop_name: str
    phone: str = ""
    password: str = ""


@dataclass
class AIProviderConfig:
    provider_id: str = DEFAULT_AI_PROVIDER_ID
    name: str = "默认接口"
    api_key: str = ""
    api_base: str = "https://api.openai.com/v1"
    model: str = "gpt-image-2"
    size: str = "1024x1024"


def _coerce_provider(item: object, fallback_index: int = 1) -> AIProviderConfig | None:
    if isinstance(item, AIProviderConfig):
        return item
    if not isinstance(item, dict):
        return None
    provider_id = str(item.get("provider_id") or f"provider-{fallback_index}").strip() or f"provider-{fallback_index}"
    name = str(item.get("name") or f"接口 {fallback_index}").strip() or f"接口 {fallback_index}"
    return AIProviderConfig(
        provider_id=provider_id,
        name=name,
        api_key=str(item.get("api_key") or ""),
        api_base=str(item.get("api_base") or "https://api.openai.com/v1"),
        model=str(item.get("model") or "gpt-image-2"),
        size=str(item.get("size") or "1024x1024"),
    )


def _normalize_providers(items: list[object] | None) -> list[AIProviderConfig]:
    providers: list[AIProviderConfig] = []
    seen: set[str] = set()
    for index, item in enumerate(items or [], start=1):
        provider = _coerce_provider(item, index)
        if provider is None or provider.provider_id in seen:
            continue
        seen.add(provider.provider_id)
        providers.append(provider)
    if providers:
        return providers
    return [AIProviderConfig()]


def _build_legacy_provider(data: dict) -> AIProviderConfig:
    return AIProviderConfig(
        provider_id=DEFAULT_AI_PROVIDER_ID,
        name="默认接口",
        api_key=decrypt_secret(str(data.get("ai_edit_api_key_dpapi") or "")),
        api_base=str(data.get("ai_edit_api_base") or "https://api.openai.com/v1"),
        model=str(data.get("ai_edit_model") or "gpt-image-2"),
        size=str(data.get("ai_edit_size") or "1024x1024"),
    )


@dataclass
class AppSettings:
    active_shop: str = "YUHOOBO"
    cdp_endpoint: str = "http://127.0.0.1:9222"
    refresh_interval_seconds: int = 5
    purchase_export_dir: str = "E:/1PythonProject/SendGoods/outputs"
    local_image_auto_start_comfyui: bool = True
    local_image_keep_comfyui: bool = True
    local_image_test_mode: bool = True
    ai_edit_api_key: str = ""
    ai_edit_api_base: str = "https://api.openai.com/v1"
    ai_edit_model: str = "gpt-image-2"
    ai_edit_size: str = "1024x1024"
    default_ai_provider_id: str = DEFAULT_AI_PROVIDER_ID
    ai_providers: list[AIProviderConfig] = field(default_factory=lambda: [AIProviderConfig()])
    ai_edit_prompt: str = DEFAULT_AI_EDIT_PROMPT
    ai_edit_split_collage: bool = False
    ai_edit_split_count: int = 10
    ai_edit_total_return_count: int = 10
    ai_edit_reference_dir: str = ""
    posai_gallery_root: str = "E:/1PythonProject/PosAiImg/图库"
    posai_mockup_root: str = "E:/1PythonProject/PosAiImg/批量贴图结果"
    posai_xlsx_root: str = "E:/1PythonProject/PosAiImg/衣物对应的xlsx"
    posai_model_root: str = "E:/1PythonProject/PosAiImg/模特图-干净"
    putaway_project_dir: str = "E:/1PythonProject/PutawayAiRobot"
    putaway_data_dir: str = "E:/1PythonProject/PutawayAiRobot/data"
    putaway_log_dir: str = "E:/1PythonProject/PutawayAiRobot/log"
    applygoods_project_dir: str = "E:/1PythonProject/ApplyGoods"
    program_data_dir: str = ""
    bo_product_title: str = "BO固定产品标题"
    szw_product_title: str = "SZW固定产品标题"
    publish_prefix: str = "BO"
    publish_task_name: str = "默认产品发布任务"
    publish_start_number: int = 0
    publish_generation_mode: str = "本地生图"
    publish_local_count: int = 10
    publish_ai_count: int = 2
    publish_handoff_mode: str = "同步并唤起"
    publish_handoff_delay_seconds: int = 0
    publish_pause_before_putaway: bool = True
    publish_test_mode: bool = True
    publish_local_steps: int = 28
    publish_local_seed: int = 2026061702
    publish_auto_start_comfyui: bool = True
    publish_keep_comfyui: bool = True
    publish_ai_prompt: str = DEFAULT_AI_EDIT_PROMPT
    publish_ai_reference_images: list[str] = field(default_factory=list)
    startup_width: int = 1180
    startup_height: int = 760
    accounts: dict[str, ShopAccount] = field(default_factory=dict)

    def __post_init__(self) -> None:
        providers = _normalize_providers(list(self.ai_providers or []))
        self.ai_providers = providers
        provider_ids = {provider.provider_id for provider in providers}
        if self.default_ai_provider_id not in provider_ids:
            self.default_ai_provider_id = providers[0].provider_id
        default_provider = self.default_ai_provider()
        self.ai_edit_api_key = default_provider.api_key
        self.ai_edit_api_base = default_provider.api_base
        self.ai_edit_model = default_provider.model
        self.ai_edit_size = default_provider.size

    def default_ai_provider(self) -> AIProviderConfig:
        for provider in self.ai_providers:
            if provider.provider_id == self.default_ai_provider_id:
                return provider
        return self.ai_providers[0]


def default_settings_path() -> Path:
    base = Path(os.environ.get("APPDATA") or Path.home()) / "ConsolePlat"
    base.mkdir(parents=True, exist_ok=True)
    return base / "settings.json"


class SettingsStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else default_settings_path()

    def load(self) -> AppSettings:
        if not self.path.exists():
            return AppSettings()
        data = json.loads(self.path.read_text(encoding="utf-8") or "{}")
        accounts: dict[str, ShopAccount] = {}
        for key, item in (data.get("accounts") or {}).items():
            if not isinstance(item, dict):
                continue
            shop_name = str(item.get("shop_name") or key)
            accounts[key] = ShopAccount(
                shop_name=shop_name,
                phone=str(item.get("phone") or ""),
                password=decrypt_secret(str(item.get("password_dpapi") or "")),
            )

        provider_payloads = data.get("ai_providers")
        if isinstance(provider_payloads, list) and provider_payloads:
            providers: list[AIProviderConfig] = []
            for index, item in enumerate(provider_payloads, start=1):
                if not isinstance(item, dict):
                    continue
                provider = AIProviderConfig(
                    provider_id=str(item.get("provider_id") or f"provider-{index}"),
                    name=str(item.get("name") or f"接口 {index}"),
                    api_key=decrypt_secret(str(item.get("api_key_dpapi") or "")),
                    api_base=str(item.get("api_base") or "https://api.openai.com/v1"),
                    model=str(item.get("model") or "gpt-image-2"),
                    size=str(item.get("size") or "1024x1024"),
                )
                providers.append(provider)
        else:
            providers = [_build_legacy_provider(data)]

        default_provider_id = str(data.get("default_ai_provider_id") or providers[0].provider_id)
        return AppSettings(
            active_shop=str(data.get("active_shop") or "YUHOOBO"),
            cdp_endpoint=str(data.get("cdp_endpoint") or "http://127.0.0.1:9222"),
            refresh_interval_seconds=int(data.get("refresh_interval_seconds") or 5),
            purchase_export_dir=str(data.get("purchase_export_dir") or "E:/1PythonProject/SendGoods/outputs"),
            local_image_auto_start_comfyui=bool(data.get("local_image_auto_start_comfyui", True)),
            local_image_keep_comfyui=bool(data.get("local_image_keep_comfyui", True)),
            local_image_test_mode=bool(data.get("local_image_test_mode", True)),
            ai_edit_api_key=providers[0].api_key,
            ai_edit_api_base=providers[0].api_base,
            ai_edit_model=providers[0].model,
            ai_edit_size=providers[0].size,
            default_ai_provider_id=default_provider_id,
            ai_providers=providers,
            ai_edit_prompt=str(data.get("ai_edit_prompt") or DEFAULT_AI_EDIT_PROMPT),
            ai_edit_split_collage=bool(data.get("ai_edit_split_collage", False)),
            ai_edit_split_count=max(1, int(data.get("ai_edit_split_count") or 10)),
            ai_edit_total_return_count=max(1, int(data.get("ai_edit_total_return_count") or 10)),
            ai_edit_reference_dir=str(data.get("ai_edit_reference_dir") or ""),
            posai_gallery_root=str(data.get("posai_gallery_root") or "E:/1PythonProject/PosAiImg/图库"),
            posai_mockup_root=str(data.get("posai_mockup_root") or "E:/1PythonProject/PosAiImg/批量贴图结果"),
            posai_xlsx_root=str(data.get("posai_xlsx_root") or "E:/1PythonProject/PosAiImg/衣物对应的xlsx"),
            posai_model_root=str(data.get("posai_model_root") or "E:/1PythonProject/PosAiImg/模特图-干净"),
            putaway_project_dir=str(data.get("putaway_project_dir") or "E:/1PythonProject/PutawayAiRobot"),
            putaway_data_dir=str(data.get("putaway_data_dir") or "E:/1PythonProject/PutawayAiRobot/data"),
            putaway_log_dir=str(data.get("putaway_log_dir") or "E:/1PythonProject/PutawayAiRobot/log"),
            applygoods_project_dir=str(data.get("applygoods_project_dir") or "E:/1PythonProject/ApplyGoods"),
            program_data_dir=str(data.get("program_data_dir") or ""),
            bo_product_title=str(data.get("bo_product_title") or "BO固定产品标题"),
            szw_product_title=str(data.get("szw_product_title") or "SZW固定产品标题"),
            publish_prefix=str(data.get("publish_prefix") or "BO"),
            publish_task_name=str(data.get("publish_task_name") or "默认产品发布任务"),
            publish_start_number=max(0, int(data.get("publish_start_number") or 0)),
            publish_generation_mode=str(data.get("publish_generation_mode") or "本地生图"),
            publish_local_count=max(1, int(data.get("publish_local_count") or 10)),
            publish_ai_count=max(1, int(data.get("publish_ai_count") or 2)),
            publish_handoff_mode=str(data.get("publish_handoff_mode") or "同步并唤起"),
            publish_handoff_delay_seconds=max(0, int(data.get("publish_handoff_delay_seconds") or 0)),
            publish_pause_before_putaway=bool(data.get("publish_pause_before_putaway", True)),
            publish_test_mode=bool(data.get("publish_test_mode", True)),
            publish_local_steps=max(8, int(data.get("publish_local_steps") or 28)),
            publish_local_seed=max(1, int(data.get("publish_local_seed") or 2026061702)),
            publish_auto_start_comfyui=bool(data.get("publish_auto_start_comfyui", True)),
            publish_keep_comfyui=bool(data.get("publish_keep_comfyui", True)),
            publish_ai_prompt=str(data.get("publish_ai_prompt") or DEFAULT_AI_EDIT_PROMPT),
            publish_ai_reference_images=[str(path) for path in (data.get("publish_ai_reference_images") or [])],
            startup_width=int(data.get("startup_width") or 1180),
            startup_height=int(data.get("startup_height") or 760),
            accounts=accounts,
        )

    def save(self, settings: AppSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        providers = _normalize_providers(list(settings.ai_providers or []))
        default_provider_id = settings.default_ai_provider_id or providers[0].provider_id
        if default_provider_id not in {provider.provider_id for provider in providers}:
            default_provider_id = providers[0].provider_id

        data = {
            "active_shop": settings.active_shop,
            "cdp_endpoint": settings.cdp_endpoint,
            "refresh_interval_seconds": int(settings.refresh_interval_seconds or 5),
            "purchase_export_dir": settings.purchase_export_dir or "E:/1PythonProject/SendGoods/outputs",
            "local_image_auto_start_comfyui": bool(settings.local_image_auto_start_comfyui),
            "local_image_keep_comfyui": bool(settings.local_image_keep_comfyui),
            "local_image_test_mode": bool(settings.local_image_test_mode),
            "ai_edit_api_key_dpapi": encrypt_secret(settings.ai_edit_api_key),
            "ai_edit_api_base": settings.ai_edit_api_base or "https://api.openai.com/v1",
            "ai_edit_model": settings.ai_edit_model or "gpt-image-2",
            "ai_edit_size": settings.ai_edit_size or "1024x1024",
            "default_ai_provider_id": default_provider_id,
            "ai_providers": [
                {
                    "provider_id": provider.provider_id,
                    "name": provider.name,
                    "api_key_dpapi": encrypt_secret(provider.api_key),
                    "api_base": provider.api_base or "https://api.openai.com/v1",
                    "model": provider.model or "gpt-image-2",
                    "size": provider.size or "1024x1024",
                }
                for provider in providers
            ],
            "ai_edit_prompt": settings.ai_edit_prompt or DEFAULT_AI_EDIT_PROMPT,
            "ai_edit_split_collage": bool(settings.ai_edit_split_collage),
            "ai_edit_split_count": max(1, int(settings.ai_edit_split_count or 10)),
            "ai_edit_total_return_count": max(1, int(settings.ai_edit_total_return_count or 10)),
            "ai_edit_reference_dir": settings.ai_edit_reference_dir or "",
            "posai_gallery_root": settings.posai_gallery_root or "E:/1PythonProject/PosAiImg/图库",
            "posai_mockup_root": settings.posai_mockup_root or "E:/1PythonProject/PosAiImg/批量贴图结果",
            "posai_xlsx_root": settings.posai_xlsx_root or "E:/1PythonProject/PosAiImg/衣物对应的xlsx",
            "posai_model_root": settings.posai_model_root or "E:/1PythonProject/PosAiImg/模特图-干净",
            "putaway_project_dir": settings.putaway_project_dir or "E:/1PythonProject/PutawayAiRobot",
            "putaway_data_dir": settings.putaway_data_dir or "E:/1PythonProject/PutawayAiRobot/data",
            "putaway_log_dir": settings.putaway_log_dir or "E:/1PythonProject/PutawayAiRobot/log",
            "applygoods_project_dir": settings.applygoods_project_dir or "E:/1PythonProject/ApplyGoods",
            "program_data_dir": settings.program_data_dir or "",
            "bo_product_title": settings.bo_product_title or "BO固定产品标题",
            "szw_product_title": settings.szw_product_title or "SZW固定产品标题",
            "publish_prefix": settings.publish_prefix or "BO",
            "publish_task_name": settings.publish_task_name or "默认产品发布任务",
            "publish_start_number": max(0, int(settings.publish_start_number or 0)),
            "publish_generation_mode": settings.publish_generation_mode or "本地生图",
            "publish_local_count": max(1, int(settings.publish_local_count or 10)),
            "publish_ai_count": max(1, int(settings.publish_ai_count or 2)),
            "publish_handoff_mode": settings.publish_handoff_mode or "同步并唤起",
            "publish_handoff_delay_seconds": max(0, int(settings.publish_handoff_delay_seconds or 0)),
            "publish_pause_before_putaway": bool(settings.publish_pause_before_putaway),
            "publish_test_mode": bool(settings.publish_test_mode),
            "publish_local_steps": max(8, int(settings.publish_local_steps or 28)),
            "publish_local_seed": max(1, int(settings.publish_local_seed or 2026061702)),
            "publish_auto_start_comfyui": bool(settings.publish_auto_start_comfyui),
            "publish_keep_comfyui": bool(settings.publish_keep_comfyui),
            "publish_ai_prompt": settings.publish_ai_prompt or DEFAULT_AI_EDIT_PROMPT,
            "publish_ai_reference_images": list(settings.publish_ai_reference_images or []),
            "startup_width": int(settings.startup_width or 1180),
            "startup_height": int(settings.startup_height or 760),
            "accounts": {},
        }
        for key, account in settings.accounts.items():
            data["accounts"][key] = {
                "shop_name": account.shop_name,
                "phone": account.phone,
                "password_dpapi": encrypt_secret(account.password),
            }
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
